# Reviewed ENOE multi-quarter person preparation

Issue #55 extends the existing national activity preparation to reviewed 2025
Q2/Q3/Q4 and 2026 Q2. Migration 0007 adds `enoe.person_quarter_v1` and
`enoe.prepared_person_v1`; the original pilot views retain their definitions.
These are reproducible database views, not exported microdata or a selected
analytical release. Consumers must select exactly one explicit `run_id` per
period; several successful runs are never implicitly combined.

## Provenance and joins

The foundation requires a successful run, reviewed reference period and layout,
archive hash in metadata, and exact ordered SDEM header signature and column
count. The four release contracts are frozen inside migration 0007. Updating the
Python ingestion allowlist does not silently change this preparation version.
These checks establish metadata compatibility, not independent revalidation of
all staged bytes. Use the [source/staging matrix](enoe-multiquarter-ingestion.md)
for independent source reconciliation before consuming a prepared run.

One SDEM record produces one person row. COE1 and COE2 are optional left joins
on the complete original source person key and run ID. Staging uniqueness
prevents join multiplication. NULL questionnaire row numbers mean absence of a
matched questionnaire, not zero answers or an inferred explanation. Source
keys retain `ent` for 2025 Q2 and `cve_ent` for subsequent reviewed releases.
Run IDs, source IDs, period, layout, source hash and original row numbers remain
available. Raw logical byte arrays remain in the foundation and staging;
ambiguous free text is not decoded or included in aggregate output.

## National activity contract

The prepared view exposes original `eda`, `r_def`, `c_res`, `fac_tri`, `clase1`
and `clase2` codes, trimmed using PostgreSQL bytea escape representation. It
classifies each row as `eligible`, `outside_universe` or `invalid` under the
[national pilot universe](enoe-national-pilot-indicators.md). Eligibility uses
the release-specific completed-interview code (`00` in 2025 Q4, `0` elsewhere),
residence 1 or 3, ages 15–98, positive integer quarterly weight and consistent
activity pairs (1/1, 1/2, 2/3, 2/4). Code 98 is the documented unspecified adult
age category; 99 is outside this universe. Codes are not stripped of leading
zeros to force equivalence. `quarterly_weight` is NULL outside eligibility;
missing and invalid values are not assigned zero. The view retains invalid rows
for inspection; aggregate reconciliation fails on them.

Only the existing national activity contract is extended. The fields and
universe do not validate platform work, earnings, informality, social-security
coverage or other questionnaire domains. Those require separate reviewed tasks.

## Aggregate reconciliation

After `just db-migrate`, run once for each explicit successful reviewed run:

```bash
uv run --locked python -m platform_work_reform.enoe_preparation --run-id <uuid>
```

The command reads under a read-only repeatable-read snapshot and prints only
aggregates, provenance and missing-questionnaire categories. It independently
recalculates eligibility and weighted totals with the Python activity audit,
checks every SQL preparation status and weight, and requires reviewed SDEM and
matched COE counts and all four national point totals. Unknown, empty, invalid
or unreconciled runs fail. Rates are displayed with the existing one-decimal
half-up convention; only the four national totals are reference gates for the
added periods. The [ingestion note](enoe-multiquarter-ingestion.md) identifies
the reviewed official references. Precision remains explicitly unvalidated
(issue #42): no SE, CV or confidence interval is emitted.

Integration tests use synthetic records with public source headers. They check
four-period coexistence, age codes 98/99, missingness, invalid weights/activity,
period-specific interview codes, run-scoped optional questionnaire joins and
rejection of unsupported provenance/headers. They do not constitute empirical
survey validation. Actual local operational evidence is recorded separately.

## Local operational evidence (2026-11-06)

Migration 0007 was applied to the existing local database. All four explicit
runs listed in the [ingestion evidence](enoe-multiquarter-ingestion.md) passed
the preparation audit: every prepared status and weight agreed with the Python
activity audit, all four national reference totals matched, and SDEM and both
matched questionnaire counts agreed with the reviewed release contracts.

| Quarter | SDEM records | Eligible | Outside universe | Matched COE1 / COE2 each |
|---|---:|---:|---:|---:|
| 2025 Q2 | 423,744 | 324,613 | 99,131 | 346,404 |
| 2025 Q3 | 422,306 | 325,108 | 97,198 | 346,524 |
| 2025 Q4 | 419,038 | 323,367 | 95,671 | 344,166 |
| 2026 Q2 | 417,128 | 324,265 | 92,863 | 344,709 |

No invalid prepared records were encountered. The complete aggregate reports
and missing-questionnaire categories remain in ignored
`artifacts/enoe-preparation-reconciliation.json`. These checks do not validate
survey variance or additional analytical variables. `just check` passed 103
unit tests and shared hooks; `just db-test` passed 31 isolated integration tests
with one optional original-source test skipped. The real-run checks above were
executed separately and are not inferred from synthetic fixtures.
