set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

default:
    @just --list

setup:
    uv sync --locked
    uv run --locked pre-commit install --install-hooks

check:
    uv lock --check
    uv run --locked pre-commit run --all-files --hook-stage manual
    uv run --locked pytest -m 'not integration'

test:
    uv run --locked pytest -m 'not integration'

db-config:
    uv run --locked python -m platform_work_reform.db validate
    docker compose config --quiet

db-up: db-config
    docker compose up -d --wait

db-down:
    docker compose down

db-status:
    uv run --locked python -m platform_work_reform.db status

db-migrate:
    uv run --locked python -m platform_work_reform.migrate

db-test:
    PWR_RUN_DB_TESTS=1 uv run --locked pytest -m integration

db-backup:
    uv run --locked python -m platform_work_reform.backup backup

db-restore archive target:
    uv run --locked python -m platform_work_reform.backup restore --archive "$1" --target "$2"

governance-check:
    uv run --locked python scripts/check_governance.py
