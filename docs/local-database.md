# Local PostgreSQL service

The service is PostgreSQL 17, pinned by image digest, in one project-specific
Compose service. The default port is 55432 on 127.0.0.1. Originals on external disks
are never mounted into the database container. Source ingestion will use COPY
FROM STDIN through the client.

Copy `.env.example` to `.env`, set a private nonempty password, then run:

```bash
just db-config
just db-up
just db-status
```

Existing installations should update `PWR_POSTGRES_PORT` in their private `.env`
and run `just db-up` to apply the new port to the existing persistent volume.

Use only PWR_POSTGRES_* variables; unrelated DATABASE_URL or PG* values are not
project configuration. Do not print `docker compose config` without `--quiet`:
the expanded configuration contains the password. SQL identifiers and the project
database prefix are validated before service startup.

`just db-down` removes the container and network but preserves the named volume.
Do not run `docker compose down -v` or volume pruning against project data.
The volume is not a backup. Initialization credentials only apply to an empty
volume: changing .env does not change an existing database password or rename it.

## Optional storage on a larger filesystem

The default `PWR_POSTGRES_VOLUME=pgdata` continues to use the original named
volume. To place a new volume on a larger local filesystem, create an empty
directory, set `PWR_POSTGRES_VOLUME=pgdata_home` and set the absolute directory
path in `PWR_POSTGRES_DATA_DIR`. The local Docker volume driver bind-mounts that
directory. Ensure Docker can access the path and that the filesystem has space.

Existing databases must be copied consistently before switching. Create and verify
a backup, stop PostgreSQL cleanly, and copy the entire stopped data directory to
a new empty destination preserving owners and permissions. Preserve the original
named volume. After switching configuration, verify the PostgreSQL system ID,
migration revision, selected periods and aggregate checks. Never initialize a new
empty directory and mistake it for the old database. The original volume remains
available for rollback until independently verified and backed up.

Docker's `pgdata_home` is a named volume with fixed driver options after creation;
changing the directory setting does not migrate an existing named volume. Inspect
the volume mountpoint before a later relocation. Do not prune or remove volumes as
part of normal maintenance.

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
