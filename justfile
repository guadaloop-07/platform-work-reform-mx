set shell := ["bash", "-euo", "pipefail", "-c"]

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

governance-check:
    uv run --locked python scripts/check_governance.py
