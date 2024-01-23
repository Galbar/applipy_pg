import datetime
from logging import Logger

from applipy_pg import PgPool


_REPOSITORY_TABLE_NAME = "applipy_pg_migrations_repository"


class Clock:
    def utc_now_as_timestamp(self) -> str:
        return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


class Repository:
    def __init__(self, pool: PgPool, logger: Logger, clock: Clock | None) -> None:
        self._pool = pool
        self._logger = logger.getChild(f"{self.__module__}.{self.__class__.__name__}")
        self._clock = clock or Clock()
        self._has_ensured_table_exists = False

    async def get_latest_version(self, subject: str) -> str | None:
        await self._ensure_table_exists()
        async with self._pool.cursor() as cur:
            await cur.execute(
                f"""
SELECT subject, version, utc_timestamp
FROM {_REPOSITORY_TABLE_NAME}
WHERE subject = %(subject)s;
""",
                {"subject": subject},
            )
            latest_version_row = await cur.fetchone()
            self._logger.debug(
                "Got latest version for %s: %s", subject, latest_version_row
            )
            if latest_version_row is None:
                return None
            version: str = latest_version_row[1]
            return version

    async def set_latest_version(self, subject: str, version: str) -> None:
        await self._ensure_table_exists()
        async with self._pool.cursor() as cur:
            await cur.execute(
                f"""
INSERT INTO {_REPOSITORY_TABLE_NAME}
(subject, version, utc_timestamp)
VALUES (%(subject)s, %(version)s, %(utc_timestamp)s);
""",
                {
                    "subject": subject,
                    "version": version,
                    "utc_timestamp": self._clock.utc_now_as_timestamp(),
                },
            )

    async def _ensure_table_exists(self) -> None:
        if self._has_ensured_table_exists:
            return

        async with self._pool.cursor() as cur:
            await cur.execute(
                f"""
CREATE TABLE IF NOT EXISTS {_REPOSITORY_TABLE_NAME} (
    subject text not null,
    version text not null,
    utc_timestamp text not null,
    CONSTRAINT subject_version PRIMARY KEY(subject, version)
);
"""
            )
        self._has_ensured_table_exists = True
