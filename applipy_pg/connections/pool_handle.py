from types import TracebackType
from typing import (
    Any,
    Optional,
    Protocol,
    Type,
)

import aiopg
from aiopg import (
    Cursor,
    Pool,
)
from aiopg.pool import _PoolCursorContextManager

from .connection import PgConnection


class ApplipyPgPoolHandle(Protocol):
    async def pool(self) -> Pool:
        ...


class _ApplipyPgPoolContextManager:
    def __init__(
        self,
        pool_handle: ApplipyPgPoolHandle,
        name: Optional[str] = None,
        cursor_factory: Any = None,
        scrollable: Optional[bool] = None,
        withhold: bool = False,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        self._pool_handle = pool_handle
        self._name = name
        self._cursor_factory = cursor_factory
        self._scrollable = scrollable
        self._withhold = withhold
        self._timeout = timeout
        self._cursor_ctx_manager: _PoolCursorContextManager | None = None

    async def __aenter__(self) -> Cursor:
        pool = await self._pool_handle.pool()
        self._cursor_ctx_manager = await pool.cursor(
            self._name,
            self._cursor_factory,
            self._scrollable,
            self._withhold,
            timeout=self._timeout,
        )
        return self._cursor_ctx_manager.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._cursor_ctx_manager is None:
            return
        self._cursor_ctx_manager.__exit__(exc_type, exc, tb)


class PgPool:
    """
    Thin wrapper around a aiopg.Pool that facilitates dependency injection by applipy.

    It can be used as follows to get a cursor and start querying the database:

        pool: PgPool
        async with pool.cursor() as cur:
            # here cur is a aiopg.Cursor
            ...

    For more advanced usage, the underlying aiopg.Pool can be retrieved doing:

        aiopg_pool = await pool.pool()
    """

    def __init__(self, connection: PgConnection) -> None:
        self._connection = connection
        self._pool: Pool | None = None

    async def pool(self) -> Pool:
        if self._pool is None:
            self._pool = await aiopg.create_pool(
                self._connection.get_dsn(), **self._connection.config
            )

        return self._pool

    def cursor(
        self,
        name: Optional[str] = None,
        cursor_factory: Any = None,
        scrollable: Optional[bool] = None,
        withhold: bool = False,
        *,
        timeout: Optional[float] = None,
    ) -> _ApplipyPgPoolContextManager:
        return _ApplipyPgPoolContextManager(
            self, name, cursor_factory, scrollable, withhold, timeout=timeout
        )
