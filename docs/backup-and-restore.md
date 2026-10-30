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

## Historical recovery verification

On 2026-10-30, the independent copy of `20261029T213030Z-f12f51ee.dump` on the
project's external IIEG volume was restored into the new database
`platform_work_reform_restore_20261030_enoe`. The archive SHA-256 was
`5c95fdb7cf159d29c2c7feeba3b6bcdd0b9bcb984b8b99c6a68dc06ca728bc7a` and the
manifest SHA-256 was
`ad68201bccdb281fcc87619cd9a8a457206c386303b642599da794c8f4aaf969`;
both matched the local copies. The restore tool verified the archive checksum,
revision 0004 and the four metadata fingerprints against the manifest.

The restored database had 44 selected IMSS months, January 2023 through
September 2026, with January 2025 absent. Its September 2026 staging rows
numbered 4,708,094. The ENOE VIV, HOG, SDEM, COE1 and COE2 tables had 150,405,
151,354, 422,306, 346,524 and 346,524 rows respectively. The restoration was
retained for inspection and used roughly 64 GiB of additional space. The
active database is separate and has later migrations; the backup precedes
those migrations and does not verify recovery of original source archives,
credentials, every IMSS month or all individual values. Apply later migrations
after recovery when appropriate. Do not delete the retained database without
an explicit retention decision.
