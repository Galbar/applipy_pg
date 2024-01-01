from contextlib import contextmanager
from typing import (
    Any,
    Iterator,
)
from unittest.mock import Mock
from uuid import uuid4

import pytest
from applipy import Config
from applipy_inject.inject import Injector
from testcontainers.postgres import PostgresContainer

from applipy_pg.handle import PgAppHandle
from applipy_pg.module import PgModule
from applipy_pg.pool_handle import PgPool


@contextmanager
def create_db() -> Iterator[dict[str, Any]]:
    user = str(uuid4())
    password = str(uuid4())
    dbname = str(uuid4())
    port = 5432
    with PostgresContainer(user=user, password=password, dbname=dbname, port=port) as container:
        yield {
            "user": user,
            "password": password,
            "host": container.get_container_host_ip(),
            "port": container.get_exposed_port(port),
            "dbname": dbname,
        }


@pytest.fixture
def database_anon() -> Iterator[dict[str, Any]]:
    with create_db() as db:
        yield db


@pytest.fixture
def database_test1() -> Iterator[dict[str, Any]]:
    with create_db() as db:
        db["name"] = "test1"
        yield db


@pytest.fixture
def database_test2() -> Iterator[dict[str, Any]]:
    with create_db() as db:
        db["name"] = "test2"
        yield db


@pytest.mark.asyncio
class TestPgModule:
    async def test_configure_and_connect_single_anonimous_db(
        self, database_anon: dict[str, Any]
    ) -> None:
        config = Config(
            {
                "pg.databases": [database_anon],
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
                "pg.databases": [
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
                "pg.databases": [database_anon],
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
                "pg.databases": [database_anon],
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
