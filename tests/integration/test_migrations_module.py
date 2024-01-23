import asyncio
from typing import Any, Callable, Iterator

import pytest
from applipy import Application, Config
from applipy_inject.inject import with_names

from applipy_pg import ClassNameMigration, Migration, PgPool, PgMigrationsModule
from applipy_pg.connections.connection import Connection


@pytest.fixture
def migrations_conn_name(database_test1: dict[str, str]) -> str:
    return database_test1["name"]


@pytest.fixture
def migrations_conn(database_test1: dict[str, Any]) -> Iterator[PgPool]:
    pool = PgPool(Connection(**database_test1))
    yield pool
    pool.pool().close()


@pytest.fixture
def output_conn_name(database_test2: dict[str, str]) -> str:
    return database_test2["name"]


@pytest.fixture
def output_conn(database_test2: dict[str, Any]) -> Iterator[PgPool]:
    pool = PgPool(Connection(**database_test2))
    yield pool
    pool.pool().close()


@pytest.fixture
def config(
    database_test1: dict[str, Any],
    database_test2: dict[str, Any],
    migrations_conn_name: str,
) -> Config:
    return Config(
        {
            "pg.connections": [database_test1, database_test2],
            "pg.migrations.connection": migrations_conn_name,
            "logging.level": "DEBUG",
        }
    )


@pytest.fixture
def applipy_app_builder(config: Config) -> Callable[[], Application]:
    return lambda: Application(config).install(PgMigrationsModule)


class _TestMigration1(Migration):
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool

    async def migrate(self) -> None:
        async with self._pool.cursor() as cur:
            await cur.execute(
                "CREATE TABLE test_migration (id SERIAL, subject TEXT, version TEXT);"
            )
            await cur.execute(
                "INSERT INTO test_migration (subject, version) VALUES (%(subject)s, %(version)s);",
                {"subject": self.subject(), "version": self.version()},
            )

    def subject(self) -> str:
        return "test_migration"

    def version(self) -> str:
        return "1"


class _TestMigration2(Migration):
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool

    async def migrate(self) -> None:
        async with self._pool.cursor() as cur:
            await cur.execute(
                "INSERT INTO test_migration (subject, version) VALUES (%(subject)s, %(version)s);",
                {"subject": self.subject(), "version": self.version()},
            )

    def subject(self) -> str:
        return "test_migration"

    def version(self) -> str:
        return "2"


class SomeSubject_20240101(ClassNameMigration):
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool

    async def migrate(self) -> None:
        async with self._pool.cursor() as cur:
            await cur.execute(
                "CREATE TABLE test_some_subject (id SERIAL, subject TEXT, version TEXT);"
            )
            await cur.execute(
                "INSERT INTO test_some_subject (subject, version) VALUES (%(subject)s, %(version)s);",
                {"subject": self.subject(), "version": self.version()},
            )


class SomeSubject_20240201(ClassNameMigration):
    def __init__(self, pool: PgPool) -> None:
        self._pool = pool

    async def migrate(self) -> None:
        async with self._pool.cursor() as cur:
            await cur.execute(
                "INSERT INTO test_some_subject (subject, version) VALUES (%(subject)s, %(version)s);",
                {"subject": self.subject(), "version": self.version()},
            )


@pytest.mark.asyncio
class TestPgMigrationsModule:
    async def test_no_migrations(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn: PgPool,
    ) -> None:
        await asyncio.to_thread(applipy_app_builder().run)

        with pytest.raises(Exception, match='relation "test_migration" does not exist'):
            async with output_conn.cursor() as cur:
                await cur.execute("SELECT version, subject FROM test_migration;")

    async def test_single_migration_single_subject(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn_name: str,
        output_conn: PgPool,
        migrations_conn: PgPool,
    ) -> None:
        applipy_app = applipy_app_builder()
        applipy_app.injector.bind(
            Migration, with_names(_TestMigration1, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app.run)

        async with migrations_conn.cursor() as cur:
            await cur.execute(
                "SELECT subject, version FROM applipy_pg_migrations_repository ORDER BY version ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 1
        assert result[0] == ("test_migration", "1")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_migration ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 1
        assert result[0] == ("1", "test_migration")

    async def test_two_migrations_single_subject_single_app_run(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn_name: str,
        output_conn: PgPool,
        migrations_conn: PgPool,
    ) -> None:
        applipy_app = applipy_app_builder()
        applipy_app.injector.bind(
            Migration, with_names(_TestMigration1, {"pool": output_conn_name})
        )
        applipy_app.injector.bind(
            Migration, with_names(_TestMigration2, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app.run)

        async with migrations_conn.cursor() as cur:
            await cur.execute(
                "SELECT subject, version FROM applipy_pg_migrations_repository ORDER BY version ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 1
        assert result[0] == ("test_migration", "2")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_migration ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("1", "test_migration")
        assert result[1] == ("2", "test_migration")

    async def test_two_migrations_single_subject_two_app_runs(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn_name: str,
        output_conn: PgPool,
        migrations_conn: PgPool,
    ) -> None:
        applipy_app_first = applipy_app_builder()
        applipy_app_first.injector.bind(
            Migration, with_names(_TestMigration1, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app_first.run)
        applipy_app_second = applipy_app_builder()
        applipy_app_second.injector.bind(
            Migration, with_names(_TestMigration2, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app_second.run)

        async with migrations_conn.cursor() as cur:
            await cur.execute(
                "SELECT subject, version FROM applipy_pg_migrations_repository ORDER BY version ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("test_migration", "1")
        assert result[1] == ("test_migration", "2")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_migration ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("1", "test_migration")
        assert result[1] == ("2", "test_migration")

    async def test_multiple_migrations_two_subjects_single_app_run(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn_name: str,
        output_conn: PgPool,
        migrations_conn: PgPool,
    ) -> None:
        applipy_app = applipy_app_builder()
        applipy_app.injector.bind(
            Migration, with_names(_TestMigration1, {"pool": output_conn_name})
        )
        applipy_app.injector.bind(
            Migration, with_names(_TestMigration2, {"pool": output_conn_name})
        )
        applipy_app.injector.bind(
            Migration, with_names(SomeSubject_20240101, {"pool": output_conn_name})
        )
        applipy_app.injector.bind(
            Migration, with_names(SomeSubject_20240201, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app.run)

        async with migrations_conn.cursor() as cur:
            await cur.execute(
                "SELECT subject, version FROM applipy_pg_migrations_repository ORDER BY subject ASC, version ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("SomeSubject", "20240201")
        assert result[1] == ("test_migration", "2")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_migration ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("1", "test_migration")
        assert result[1] == ("2", "test_migration")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_some_subject ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("20240101", "SomeSubject")
        assert result[1] == ("20240201", "SomeSubject")

    async def test_multiple_migrations_two_subjects_two_app_runs(
        self,
        applipy_app_builder: Callable[[], Application],
        output_conn_name: str,
        output_conn: PgPool,
        migrations_conn: PgPool,
    ) -> None:
        applipy_app_first = applipy_app_builder()
        applipy_app_first.injector.bind(
            Migration, with_names(_TestMigration1, {"pool": output_conn_name})
        )
        applipy_app_first.injector.bind(
            Migration, with_names(SomeSubject_20240101, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app_first.run)
        applipy_app_second = applipy_app_builder()
        applipy_app_second.injector.bind(
            Migration, with_names(_TestMigration2, {"pool": output_conn_name})
        )
        applipy_app_second.injector.bind(
            Migration, with_names(SomeSubject_20240201, {"pool": output_conn_name})
        )
        await asyncio.to_thread(applipy_app_second.run)

        async with migrations_conn.cursor() as cur:
            await cur.execute(
                "SELECT subject, version FROM applipy_pg_migrations_repository ORDER BY subject ASC, version ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 4
        assert result[0] == ("SomeSubject", "20240101")
        assert result[1] == ("SomeSubject", "20240201")
        assert result[2] == ("test_migration", "1")
        assert result[3] == ("test_migration", "2")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_migration ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("1", "test_migration")
        assert result[1] == ("2", "test_migration")

        async with output_conn.cursor() as cur:
            await cur.execute(
                "SELECT version, subject FROM test_some_subject ORDER BY id ASC;"
            )
            result = await cur.fetchall()

        assert len(result) == 2
        assert result[0] == ("20240101", "SomeSubject")
        assert result[1] == ("20240201", "SomeSubject")
