import aiopg
from applipy import (
    BindFunction,
    Config,
    Module,
    RegisterFunction,
)

from .handle import PgAppHandle
from .pool_handle import (
    PgPool,
    ApplipyPgPoolHandle,
)


def _build_dsn(
    dbname: str, user: str, host: str, password: str | None, port: str | None
) -> str:
    dsn = f"dbname={dbname} user={user} host={host}"
    if password:
        dsn += f" password={password}"
    if port:
        dsn += f" port={port}"
    return dsn


class PgModule(Module):
    def __init__(self, config: Config) -> None:
        self.config = config

    def configure(self, bind: BindFunction, register: RegisterFunction) -> None:
        global_config = self.config.get("pg.global_config", {})
        for db in self.config.get("pg.databases", []):
            name = db.get("name")
            user = db["user"]
            host = db["host"]
            dbname = db["dbname"]
            password = db.get("password")
            port = db.get("port")
            db_config = {}
            db_config.update(global_config)
            db_config.update(db.get("config", {}))
            dsn = _build_dsn(dbname, user, host, password, port)
            pool = PgPool(aiopg.create_pool(dsn, **db_config))
            bind(PgPool, pool, name=name)
            bind(ApplipyPgPoolHandle, pool)

        register(PgAppHandle)
