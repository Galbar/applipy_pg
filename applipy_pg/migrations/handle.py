from logging import Logger

from applipy import AppHandle

from .migration import Migration
from .repository import Repository


class _DummyMigration(Migration):
    def __init__(self, subject: str, version: str) -> None:
        self._subject = subject
        self._version = version

    def subject(self) -> str:
        return self._subject

    def version(self) -> str:
        return self._version


def _get_migrations_by_subject(
    migrations: list[Migration],
) -> dict[str, list[Migration]]:
    migrations_by_subject: dict[str, list[Migration]] = {}
    for migration in migrations:
        subject = migration.subject()
        if subject not in migrations_by_subject:
            migrations_by_subject[subject] = []
        migrations_by_subject[subject].append(migration)
    return migrations_by_subject


class MigrationsHandle(AppHandle):
    def __init__(
        self, migrations: list[Migration], repository: Repository, logger: Logger
    ) -> None:
        self._migrations_by_subject = _get_migrations_by_subject(migrations)
        self._repository = repository
        self._logger = logger.getChild(f"{self.__module__}.{self.__class__.__name__}")

    async def on_init(self) -> None:
        for subject in self._migrations_by_subject:
            self._logger.debug("Starting migrations for %s", subject)
            migrations_to_execute = await self._get_migrations_to_execute(subject)
            if migrations_to_execute:
                await self._execute_migrations(migrations_to_execute)
            else:
                self._logger.debug("No migrations to execute for %s", subject)

    async def _get_migrations_to_execute(self, subject: str) -> list[Migration]:
        migrations = self._migrations_by_subject.get(subject, [])
        latest_version = await self._repository.get_latest_version(subject)
        self._logger.debug("Latest version for %s is %s", subject, latest_version)
        if latest_version is None:
            return migrations
        else:
            dummy_latest_migration = _DummyMigration(subject, latest_version)
            return [
                migration
                for migration in migrations
                if dummy_latest_migration < migration
            ]

    async def _execute_migrations(self, migrations: list[Migration]) -> None:
        if not migrations:
            return

        subject = migrations[0].subject()
        self._logger.info("Executing %i migrations for %s", len(migrations), subject)
        latest_success_version: str | None = None
        try:
            for migration in sorted(migrations):
                self._logger.debug(
                    "Executing migration for %s version %s",
                    subject,
                    migration.version(),
                )
                await migration.migrate()
                latest_success_version = migration.version()
        finally:
            if latest_success_version is not None:
                self._logger.info(
                    "Last migration executed for %s is version %s",
                    subject,
                    latest_success_version,
                )
                await self._repository.set_latest_version(
                    subject, latest_success_version
                )
