from applipy import (
    BindFunction,
    Config,
    Module,
    RegisterFunction,
)

from .connection import PgConnection
from .handle import PgAppHandle
from .pool_handle import (
    ApplipyPgPoolHandle,
    PgPool,
)


class PgModule(Module):
    def __init__(self, config: Config) -> None:
        self.config = config

    def configure(self, bind: BindFunction, register: RegisterFunction) -> None:
        global_config = self.config.get("pg.global_config", {})
        for conn in self.config.get("pg.connections", []):
            db_config = {}
            db_config.update(dict(global_config))
            db_config.update(dict(conn.get("config", {})))
            connection = PgConnection(
                name=conn.get('name'),
                user=conn['user'],
                host=conn['host'],
                dbname=conn['dbname'],
                password=conn.get('password'),
                port=conn.get('port'),
                aliases=conn.get('aliases', []),
                config=db_config,
            )
            pool = PgPool(connection)
            bind(ApplipyPgPoolHandle, pool)
            bind(PgPool, pool, name=connection.name)
            for alias in connection.aliases:
                bind(PgPool, pool, name=alias)

        register(PgAppHandle)
