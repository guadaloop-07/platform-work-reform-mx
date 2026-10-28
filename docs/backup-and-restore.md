# Verified backup and restore

With the local service running and migrations applied, run:

```bash
just db-backup
just db-restore backups/<backup>.dump platform_work_reform_restore_trial
```

For an explicit output filename, use:

```bash
uv run --locked python -m platform_work_reform.backup backup --output backups/example.dump
```

The program uses pg_dump/pg_restore from the running PostgreSQL container, avoiding
host-client version mismatch. It does not pass passwords on command lines. CI
sets PWR_POSTGRES_CONTAINER to its isolated service container ID; normal local use
leaves that variable unset and uses the project Compose service.

## Consistency and publication

A repeatable-read, read-only transaction exports a snapshot. pg_dump uses that
same snapshot while the audit records the Alembic revision and ordered content
hashes/counts of the four provenance tables. Concurrent metadata changes cannot
silently make the dump and audit describe different states. Do not run DDL
migrations concurrently with backups.

Custom-format dumps contain the entire database. The accompanying `.dump.json`
records archive SHA-256, source database, UTC timestamp, revision and metadata
fingerprints; it does not contain credentials or raw metadata rows. Both files
are private (0600), and backup directories created by the program use 0700.
Output files are published without overwriting existing names. A backup is usable
only when both archive and manifest exist and their checksum matches. After a
process or machine crash, incomplete files without a valid pair are not backups.

Copy both files to separate storage. A backup left on the same disk as the volume
does not protect against disk loss. This is a database backup, not a backup of
original IMSS/ENOE files, global roles, or deployment secrets.

## Restore boundaries and verification

Restore accepts only a new `platform_work_reform_restore_*` database. It refuses
the configured database, the backup's original database, and every existing
target. It never uses pg_restore --clean or --create. The target is created
explicitly, then restored with --exit-on-error and --single-transaction.

The archive checksum is verified before database creation. After restoration,
the revision and all four provenance fingerprints must match. Integration tests
exercise populated provenance records, existing-target refusal, corruption,
dump failure, and a concurrent write excluded from the exported snapshot.
Source-table reconciliation will be extended with ingestion;
metadata fingerprints alone do not validate future analytical calculations.

If restore fails after creating the target, that new database remains for
inspection and will not be overwritten on retry. Choose a new target name.
Restoration does not switch the application's active database. This initial tool
supports trusted project backups in the same local PostgreSQL service; automated
schedules, role provisioning and point-in-time recovery are outside P05.
