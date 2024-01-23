import asyncio

from applipy import AppHandle

from .pool_handle import ApplipyPgPoolHandle


class PgAppHandle(AppHandle):
    def __init__(self, pool_handles: list[ApplipyPgPoolHandle]) -> None:
        self.pool_handles = pool_handles

    async def on_shutdown(self) -> None:
        coros = []
        for pool_handle in self.pool_handles:
            pool = await pool_handle.pool()
            pool.close()
            coros.append(pool.wait_closed())

        await asyncio.gather(*coros)
