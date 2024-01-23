from typing import Any

from applipy import Config


class Connection:
    def __init__(
        self,
        *,
        name: str | None = None,
        user: str,
        host: str,
        dbname: str,
        password: str | None,
        port: str | int | None,
        **kwargs: dict[str, Any],
    ) -> None:
        self.name = name
        self.user = user
        self.host = host
        self.dbname = dbname
        self.password = password
        self.port = port
        self.config = Config(kwargs).get("config") or {}

    def get_dsn(self) -> str:
        dsn = f"dbname={self.dbname} user={self.user} host={self.host}"
        if self.password:
            dsn += f" password={self.password}"
        if self.port:
            dsn += f" port={self.port}"
        return dsn
