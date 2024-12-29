from typing import Any


class PgConnection:
    def __init__(
        self,
        *,
        name: str | None = None,
        user: str,
        host: str,
        dbname: str,
        password: str | None,
        port: str | int | None,
        aliases: list[str] = [],
        config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.user = user
        self.host = host
        self.dbname = dbname
        self.password = password
        self.port = port
        self.aliases = aliases
        self.config = config or {}

    def get_dsn(self) -> str:
        dsn = f"dbname={self.dbname} user={self.user} host={self.host}"
        if self.password:
            dsn += f" password={self.password}"
        if self.port:
            dsn += f" port={self.port}"
        return dsn
