from contextlib import contextmanager
from typing import (
    Any,
    Iterator,
)
from uuid import uuid4

import pytest
from testcontainers.postgres import PostgresContainer


@contextmanager
def create_db() -> Iterator[dict[str, Any]]:
    user = str(uuid4())
    password = str(uuid4())
    dbname = str(uuid4())
    port = 5432
    with PostgresContainer(
        user=user, password=password, dbname=dbname, port=port
    ) as container:
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
