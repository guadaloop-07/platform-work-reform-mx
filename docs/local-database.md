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
