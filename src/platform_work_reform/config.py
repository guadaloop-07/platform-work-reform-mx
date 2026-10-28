"""Project-specific database configuration; never inherit another project's URL."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    user: str
    password: str = field(repr=False)
    database: str = "platform_work_reform"
    host: str = "127.0.0.1"
    port: int = 5436

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> "Settings":
        if values is None:
            values = {**dotenv_values(".env"), **os.environ}
        user = values.get("PWR_POSTGRES_USER", "platform_owner")
        database = values.get("PWR_POSTGRES_DB", "platform_work_reform")
        password = values.get("PWR_POSTGRES_PASSWORD", "")
        host = values.get("PWR_POSTGRES_HOST", "127.0.0.1")
        for label, name in (("user", user), ("database", database)):
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name or ""):
                raise ValueError(f"Invalid PostgreSQL {label}; use a lowercase SQL identifier")
        if not database.startswith("platform_work_reform"):
            raise ValueError("Database must use the platform_work_reform project prefix")
        if not password or not password.strip():
            raise ValueError("Set PWR_POSTGRES_PASSWORD to a nonempty local secret")
        if host != "127.0.0.1":
            raise ValueError("The initial local service requires PWR_POSTGRES_HOST=127.0.0.1")
        try:
            port = int(values.get("PWR_POSTGRES_PORT", "5436"))
        except (TypeError, ValueError) as exc:
            raise ValueError("PWR_POSTGRES_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("PWR_POSTGRES_PORT must be between 1 and 65535")
        return cls(user=user, password=password, database=database, host=host, port=port)

    def connection_parameters(self, database: str | None = None) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "dbname": self.database if database is None else database,
            "connect_timeout": 5,
        }
