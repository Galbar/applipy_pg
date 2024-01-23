from applipy import (
    BindFunction,
    Config,
    Module,
    RegisterFunction,
)

from .connection import Connection
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
            db_config.update(global_config)
            db_config.update(conn.get("config", {}))
            connection = Connection(**conn, config=db_config)
            pool = PgPool(connection)
            bind(PgPool, pool, name=connection.name)
            bind(ApplipyPgPoolHandle, pool)

        register(PgAppHandle)
