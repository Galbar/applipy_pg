[![pipeline status](https://gitlab.com/applipy/applipy_pg/badges/master/pipeline.svg)](https://gitlab.com/applipy/applipy_pg/-/pipelines?scope=branches&ref=master)
[![coverage report](https://gitlab.com/applipy/applipy_pg/badges/master/coverage.svg)](https://gitlab.com/applipy/applipy_pg/-/graphs/master/charts)
[![PyPI Status](https://img.shields.io/pypi/status/applipy_pg.svg)](https://pypi.org/project/applipy_pg/)
[![PyPI Version](https://img.shields.io/pypi/v/applipy_pg.svg)](https://pypi.org/project/applipy_pg/)
[![PyPI Python](https://img.shields.io/pypi/pyversions/applipy_pg.svg)](https://pypi.org/project/applipy_pg/)
[![PyPI License](https://img.shields.io/pypi/l/applipy_pg.svg)](https://pypi.org/project/applipy_pg/)
[![PyPI Format](https://img.shields.io/pypi/format/applipy_pg.svg)](https://pypi.org/project/applipy_pg/)

# Applipy PostgreSQL

An [applipy](https://gitlab.com/applipy/applipy) library for working with PostgreSQL.

It lets you declare connections in the configuration of your application that
get turned into postgres connection pools that can be accessed by declaring the
dependency in your classes.

The connection pools are created the first time they are used and closed on
application shutdown.

## Usage

You can define connections to databases in you application config file:

```yaml
# dev.yaml
app:
  name: demo
  modules:
  - applipy_pg.PgModule

pg:
  connections:
  # Defines an anonimous db connection pool
  - user: username
    host: mydb.local
    port: 5432
    dbname: demo
    password: $3cr37
  # Defines an db connection pool with name "db2"
  # which is also aliased to names "db3" and "db4"
  - name: db2
    user: username
    host: mydb.local
    port: 5432
    dbname: demo
    password: $3cr37
    aliases: [db3, db4]
```

The configuration definition above defines two database connection pools. These
can be accessed through applipy's dependency injection system:

```python
from applipy_pg import PgPool

class DoSomethingOnDb:
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool

    async def do_something(self) -> None:
        async with self.pool.cursor() as cur:
            # cur is a aiopg.Cursor
            await cur.execute('SELECT 1')
            await cur.fetchone()

from typing import Annotated
from applipy_inject import name

class DoSomethingOnDb2:
    def __init__(self, pool: Annotated[PgPool, name('db2')]) -> None:
        self._pool = pool

    async def do_something(self) -> None:
        async with self.pool.cursor() as cur:
            # cur is a aiopg.Cursor
            await cur.execute('SELECT 2')
            await cur.fetchone()
```

Aliased pools can also be accessed using their aliases:

```python
from typing import Annotated
from applipy_inject import name

class DoSomethingOnDb2:
    def __init__(
        self,
        pool2: Annotated[PgPool, name('db2')],
        pool4: Annotated[PgPool, name('db4')],
    ) -> None:
        assert pool2 is pool4
```

The `aiopg.Pool` instance can be accessed using the `PgPool.pool()` method.

Each connection pool can be further configured by setting a `config` attribute
with a dict containing the extra paramenters to be passed to
[`aiopg.create_pool()`](https://aiopg.readthedocs.io/en/stable/core.html#aiopg.create_pool):

```yaml
pg:
  connections:
  - user: username
    host: mydb.local
    port: 5432
    dbname: demo
    password: $3cr37
    config:
      minsize: 5
      timeout: 100.0
```

You can also define a global configuration that will serve as a base to all
database connections defined by setting `pg.global_config`.

```yaml
pg:
  global_config:
    minsize: 5
    timeout: 100.0
  connections:
  # ...
```

## Migrations

This library also includes a migrations functionality. How to use it:

First, define your migrations:

```python
class DemoMigrationSubject_20240101(PgClassNameMigration):
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool  # Import whatever resources you need

    async def migrate(self) -> None:
        # Do you migrations...
        async with self._pool.cursor() as cur:
            ...
```

If you want more control over how the version and subject of the migration is
defined, you can extend `PgMigration` and implement your own logic.

Then, create your migrations module:

```python
class MyMigrationsModule(Module):
    def configure(self, bind: BindFunction, register: RegisterFunction) -> None:
        bind(PgMigration, DemoMigrationSubject_20240101)

    @classmethod
    def depends_on(cls) -> tuple[type[Module], ...]:
        return PgMigrationsModule,
```

Finally, you can optionally set the name of the connection to use for the
migrations audit table. This table is used to know what migrations have been
run and which migrations should be ran:

```yaml
pg:
  connections:
  # Defines an db connection pool with name "db2"
  - name: db2
    # ...
  migrations:
    # sets the connection named "db2" as the connection to use for the
    # migrations audit table
    connection: db2
```

### Loading and Performing Migrations

To load your migrations in the application you can:

1. Bind them in an Applipy module to the type `PgMigration`, using the injector
2. Have them all be part of a Python module and set the config
   `pg.migrations.modules` to a list of strings containing the modules
   containing migration classes.

Then, just include the module `applipy_pg.PgMigrationsModule` somewhere in your
app, i.e. in the config file and your migrations will be run during the
`on_init` step of your application's lifecycle.
