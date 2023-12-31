from contextlib import contextmanager
from time import (
    sleep,
    time,
)
from typing import (
    Any,
    Iterator,
)
from unittest.mock import Mock
from uuid import uuid4

import docker as _docker
import pytest
from applipy import Config
from applipy_inject.inject import Injector

from applipy_pg.handle import PgAppHandle
from applipy_pg.module import PgModule
from applipy_pg.pool_handle import PgPool


@pytest.fixture
def docker() -> _docker.APIClient:
    return _docker.from_env()


def wait_pg_container_ready(container: _docker.models.containers.Container) -> None:
    status_code = -1
    start = time()
    while status_code != 0:
        if time() - start >= 10:
            raise TimeoutError("Database took too long to be ready")
        status_code, _ = container.exec_run("pg_isready")
    sleep(1)


@contextmanager
def create_db(client: _docker.APIClient) -> Iterator[dict[str, Any]]:
    user = str(uuid4())
    password = str(uuid4())
    dbname = str(uuid4())
    container = client.containers.run(
        "postgres:latest",
        remove=True,
        detach=True,
        environment={
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": dbname,
        },
        ports={
            "5432/tcp": None,
        },
    )
    while not container.ports:
        container.reload()
    port = container.ports["5432/tcp"][0]["HostPort"]
    try:
        wait_pg_container_ready(container)
        yield {
            "user": user,
            "password": password,
            "host": "localhost",
            "port": port,
            "dbname": dbname,
        }
    finally:
        container.stop()


@pytest.fixture
def database_anon(docker: _docker.APIClient) -> Iterator[dict[str, Any]]:
    with create_db(docker) as db:
        yield db


@pytest.fixture
def database_test1(docker: _docker.APIClient) -> Iterator[dict[str, Any]]:
    with create_db(docker) as db:
        db["name"] = "test1"
        yield db


@pytest.fixture
def database_test2(docker: _docker.APIClient) -> Iterator[dict[str, Any]]:
    with create_db(docker) as db:
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
