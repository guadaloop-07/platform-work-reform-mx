# Local PostgreSQL service

The service is PostgreSQL 17, pinned by image digest, in one project-specific
Compose service. The default port is 5436 on 127.0.0.1. Originals on external disks
are never mounted into the database container. Source ingestion will use COPY
FROM STDIN through the client.

Copy `.env.example` to `.env`, set a private nonempty password, then run:

```bash
just db-config
just db-up
just db-status
```

Use only PWR_POSTGRES_* variables; unrelated DATABASE_URL or PG* values are not
project configuration. Do not print `docker compose config` without `--quiet`:
the expanded configuration contains the password. SQL identifiers and the project
database prefix are validated before service startup.

`just db-down` removes the container and network but preserves the named volume.
Do not run `docker compose down -v` or volume pruning against project data.
The volume is not a backup. Initialization credentials only apply to an empty
volume: changing .env does not change an existing database password or rename it.

Shared deployment, individual analyst accounts, and non-loopback access belong to
P19. This local owner account is for infrastructure development only.

## Migrations and tests

Run `just db-migrate` from the source checkout. Alembic bootstraps its `meta`
namespace and records revision 0001 in `meta.alembic_version`. Repeated upgrades
are harmless. Migrations are reviewed source files; do not edit applied revisions
or downgrade a database containing research data. Offline SQL generation and
installed-wheel migration execution are not supported by this initial interface.

Revision 0001 creates provenance metadata and empty source namespaces, not survey
tables or results. Hash identity is unique per source. Dataset provenance must
refer to a run for the same source file. Terminal run states require a finish
timestamp. Publication selection and recovery orchestration arrive in P10–P11.

Run `just db-test` with the local service running. Tests create randomly named
`platform_work_reform_test_*` databases and remove only those databases afterward;
they do not clear or recreate the configured project database. CI runs the same
tests against a disposable PostgreSQL service. Failed data transactions must be
rolled back before a separate audit transaction records the failure.

See [verified backup and restore](backup-and-restore.md) for recovery commands.
