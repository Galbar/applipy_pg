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
from .migration import PgMigration, find_migrations
from applipy_pg import PgModule
from typing import cast


class PgMigrationsModule(Module):
    _config: Config

    def __init__(self, config: Config) -> None:
        self._config = cast(Config, config['pg.migrations'])

    def configure(self, bind: BindFunction, register: RegisterFunction) -> None:
        connection_name = self._config.get("connection")
        if connection_name is not None and type(connection_name) is not str:
            raise TypeError("Config value `pg.migrations.connection` must be a string or None")
        if connection_name:
            bind(with_names(Repository, {"pool": connection_name}))
        else:
            bind(Repository)

        register(MigrationsHandle)
        self._bind_migrations_from_config(bind)

    @classmethod
    def depends_on(cls) -> tuple[type[Module], ...]:
        return LoggingModule, PgModule

    def _bind_migrations_from_config(self, bind: BindFunction) -> None:
        migrations_module_names = self._config.get('modules', [])
        if type(migrations_module_names) is not list:
            raise TypeError("Config value `pg.migrations.modules` must be a list of strings or None")
        migrations = [
            migration
            for migrations_module_name in migrations_module_names
            for migration in find_migrations(migrations_module_name)
        ]
        for migration in migrations:
            bind(PgMigration, migration)
