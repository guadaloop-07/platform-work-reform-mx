"""Apply project migrations from a source checkout."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from platform_work_reform.config import Settings


def upgrade(settings: Settings) -> None:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.attributes["settings"] = settings
    command.upgrade(config, "head")


def main() -> None:
    try:
        upgrade(Settings.from_env())
    except ValueError as exc:
        raise SystemExit(f"Configuration error: {exc}") from None
    print("Database migrations are up to date.")


if __name__ == "__main__":
    main()
