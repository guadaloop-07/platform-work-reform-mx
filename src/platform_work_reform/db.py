"""Local database validation and status commands."""

import argparse

import psycopg

from platform_work_reform.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "status"])
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    if args.command == "validate":
        print("Local PostgreSQL configuration is valid.")
        return
    try:
        with psycopg.connect(**settings.connection_parameters()) as connection:
            database, version = connection.execute(
                "SELECT current_database(), current_setting('server_version')"
            ).fetchone()
    except psycopg.Error:
        parser.exit(1, "Database connection failed; check the service and local configuration.\n")
    print(f"Connected to {database}; PostgreSQL {version}.")


if __name__ == "__main__":
    main()
