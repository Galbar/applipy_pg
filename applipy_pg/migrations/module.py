from applipy import (
    BindFunction,
    Config,
    LoggingModule,
    Module,
    RegisterFunction,
)
from applipy_inject.inject import with_names

from .handle import MigrationsHandle
from .repository import Repository
from applipy_pg import PgModule


class PgMigrationsModule(Module):
    def __init__(self, config: Config) -> None:
        self._config = config

    def configure(self, bind: BindFunction, register: RegisterFunction) -> None:
        connection_name = self._config.get("pg.migrations.connection")
        if connection_name is None or type(connection_name) is not str:
            raise TypeError("Config value `pg.migrations.connection` must be a string or None")
        bind(with_names(Repository, {"pool": connection_name}))
        register(MigrationsHandle)

    @classmethod
    def depends_on(cls) -> tuple[type[Module], ...]:
        return LoggingModule, PgModule
