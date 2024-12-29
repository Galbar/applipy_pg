from typing import Any
from unittest.mock import Mock

import pytest
from applipy import Config
from applipy_inject.inject import Injector

from applipy_pg import PgModule
from applipy_pg.connections.handle import PgAppHandle
from applipy_pg.connections.pool_handle import PgPool


@pytest.mark.asyncio
class TestPgModule:
    async def test_configure_and_connect_single_anonimous_db(
        self, database_anon: dict[str, Any]
    ) -> None:
        config = Config(
            {
                "pg.connections": [database_anon],
            }
        )
        sut = PgModule(config)
        injector = Injector()
        register = Mock()
        sut.configure(injector.bind, register)
        actual_pools = injector.get_all(PgPool, None)
        assert len(actual_pools) == 1

        pool = actual_pools[0]
        async with pool.cursor() as cur:
            await cur.execute("SELECT 1")
            result = await cur.fetchone()
        assert result == (1,)

        register.assert_called_once_with(PgAppHandle)
        injector.bind(PgAppHandle)
        app_handle = injector.get(PgAppHandle)
        await app_handle.on_shutdown()
        assert (await pool.pool()).closed

    async def test_configure_and_connect_multiple_dbs(
        self,
        database_anon: dict[str, Any],
        database_test1: dict[str, Any],
        database_test2: dict[str, Any],
    ) -> None:
        config = Config(
            {
                "pg.connections": [
                    database_anon,
                    database_test1,
                    database_test2,
                ],
            }
        )
        sut = PgModule(config)
        injector = Injector()
        register = Mock()
        sut.configure(injector.bind, register)
        actual_anon_pools = injector.get_all(PgPool, None)
        actual_test1_pools = injector.get_all(PgPool, "test1")
        actual_test2_pools = injector.get_all(PgPool, "test2")
        assert len(actual_anon_pools) == 1
        assert len(actual_test1_pools) == 1
        assert len(actual_test2_pools) == 1

        results = []
        for pool in actual_anon_pools + actual_test1_pools + actual_test2_pools:
            async with pool.cursor() as cur:
                await cur.execute("SELECT 1")
                results.append(await cur.fetchone())
        assert len(results) == 3
        assert all(result == (1,) for result in results)

        register.assert_called_once_with(PgAppHandle)
        injector.bind(PgAppHandle)
        app_handle = injector.get(PgAppHandle)
        await app_handle.on_shutdown()
        for pool in actual_anon_pools + actual_test1_pools + actual_test2_pools:
            assert (await pool.pool()).closed

    async def test_configure_pool_with_extra_config(
        self, database_anon: dict[str, Any]
    ) -> None:
        database_anon["config"] = {
            "minsize": 10,
            "maxsize": 13,
            "timeout": 43.0,
        }
        config = Config(
            {
                "pg.connections": [database_anon],
            }
        )
        sut = PgModule(config)
        injector = Injector()
        register = Mock()
        sut.configure(injector.bind, register)
        actual_pools = injector.get_all(PgPool, None)
        assert len(actual_pools) == 1

        pool = actual_pools[0]
        aiopg_pool = await pool.pool()
        assert aiopg_pool.minsize == 10
        aiopg_pool.maxsize == 13
        aiopg_pool.timeout == 43.0

    async def test_configure_pool_with_global_config(
        self, database_anon: dict[str, Any]
    ) -> None:
        database_anon["config"] = {
            "minsize": 1,
        }
        config = Config(
            {
                "pg.global_config": {
                    "minsize": 10,
                    "maxsize": 13,
                    "timeout": 43.0,
                },
                "pg.connections": [database_anon],
            }
        )
        sut = PgModule(config)
        injector = Injector()
        register = Mock()
        sut.configure(injector.bind, register)
        actual_pools = injector.get_all(PgPool, None)
        assert len(actual_pools) == 1

        pool = actual_pools[0]
        aiopg_pool = await pool.pool()
        assert aiopg_pool.minsize == 1
        aiopg_pool.maxsize == 13
        aiopg_pool.timeout == 43.0

    async def test_connection_alias(self) -> None:
        config = Config(
            {
                "pg.connections": [{
                    "user": "some_user",
                    "password": "1234",
                    "host": "192.168.5.1",
                    "port": 1234,
                    "dbname": "test1231241",
                    "name": "db1",
                    "aliases": ["db2", "db3"],
                }],
            }
        )
        sut = PgModule(config)
        injector = Injector()
        register = Mock()
        sut.configure(injector.bind, register)
        assert injector.get(PgPool, "db1") is injector.get(PgPool, "db2")
        assert injector.get(PgPool, "db1") is injector.get(PgPool, "db3")
