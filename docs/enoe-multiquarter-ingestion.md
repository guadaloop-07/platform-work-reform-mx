# Reviewed ENOE multi-quarter ingestion and design-support comparison

Issue #53 extends source-faithful ingestion to 2025 Q2, 2025 Q4 and 2026 Q2.
The 2025 Q3 pilot is retained. Unresolved precision issue #42 does not block
loading, source reconciliation or observed-design diagnostics. No national or
domain variance is declared validated by this extension.

The [precision methodology note](enoe-precision-methodology.md) retains the
confidence-interval finding and original link to INEGI, *Cómo se hace la ENOE.
Métodos y procedimientos*,
[section 3.9, PDF pages 64–65](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/889463909743.pdf#page=64):
the interval uses a normal critical value, and the variance formula is undefined
for a stratum with one UPM. Reproducing national weighted totals does not resolve
that issue or authorize a singleton correction.

## Release contracts and source differences

The machine-readable allowlist is `src/platform_work_reform/enoe_releases.json`.
For each added period it records the official archive URI, reviewed archive and
CSV/dictionary hashes, exact ordered header signatures, counts, original join
keys, entity field, completed-interview code, review date and independent
national point-estimate reference. Any new hash or period requires review.
Original archives remain outside Git under `data/enoe/official/<year>q<quarter>/`.

Official archive links:

- [2025 Q2](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2025/conjunto_de_datos_enoe_2025_2t_csv.zip)
- [2025 Q4](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2025/conjunto_de_datos_enoe_2025_4t_csv.zip)
- [2026 Q2](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2026/conjunto_de_datos_enoe_2026_2t_csv.zip)

The [INEGI 2025 structure](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf)
identifies the entity-name transition: `ent` through 2025 Q2 and `cve_ent`
from Q3. Join keys use the actual original name for each release. The audit
maps the selected entity value to a common diagnostic slot; staging never
renames columns or changes field values.

The inspected 2025 Q4 CSV uses `r_def="00"` for completed interviews, while the
other reviewed CSV releases use `"0"`. That source-specific code is an explicit
eligibility rule, not an automatic removal of leading zeros. The fingerprint
retains the original logical code, including `"00"`. Blank and coded missing
values remain unchanged in staging. The diagnostic universe is completed
interviews, `c_res` 1 or 3, and `eda` 15–98 (98 is an unspecified adult-age
code, not a literal age); use positive quarterly `fac_tri` and valid activity
codes. The [pilot universe note](enoe-national-pilot-indicators.md) supplies
these precoded-variable rules. This does not authorize the same universe for
all questionnaire variables.

Bundled dictionaries identify the reviewed age, quarterly weight, activity and
design variables. The two free-text fields `cs_p21_des` and `cs_p23_des` contain
non-ASCII bytes in the new releases, as in the pilot. A Latin-1 parse remains a
reversible byte mapping, not an encoding determination or decoded-text release.
The initial inspection checked row widths, key uniqueness and all five source
parent/child relationships before registering the contracts.

## Loading and validation

The loader accepts explicit `--year` and `--quarter` arguments. Defaults retain
the original Q3 pilot behavior. For example:

```bash
uv run --locked python -m platform_work_reform.enoe_staging \
  data/enoe/official/2025q2/enoe-2025q2-official.zip --year 2025 --quarter 2
```

Each release is loaded in one transaction, including all five raw tables,
metadata and source keys. Hashes, bundled dictionaries, headers, row counts,
key uniqueness and child-to-parent matches must pass. The source is re-hashed
before completion. A repeated completed release is idempotent. There is no new
migration: the existing staging schema is run-scoped. Existing prepared/pilot
views remain restricted to 2025 Q3; new periods are not silently added to them.

The real-data rehearsal exposed a quadratic nested-loop plan in the orphan
checks for new, uncommitted run IDs without useful planner statistics. Those
three attempts were canceled and rolled back. The loader and reconciliation
now disable nested loops locally inside their transactions; an `EXPLAIN` check
confirmed a hash anti-join. Every relationship check remains mandatory. No
global database planner setting or survey value is changed.

A source-only audit can run before loading:

```bash
uv run --locked python -m platform_work_reform.enoe_source_support \
  data/enoe/official/2025q4/enoe-2025q4-official.zip --year 2025 --quarter 4
```

For added periods the source audit must reproduce all four independent national
reference totals (population 15-plus, PEA, occupied and unemployed); a mismatch
fails rather than changing weights or accepting an empty universe. References:

- [2025 Q2, bulletin 433/25, table 1](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/enoe/enoe2025_08.pdf#page=3)
- [2025 Q4, bulletin published February 2026, table 1](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2026/enoe/enoe2026_02.pdf#page=3)
- [2026 Q2, bulletin 503/26, table 1](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2026/enoe/enoe2026_08.pdf#page=3)

## Cross-quarter matrix

Create a private JSON list with one explicit reviewed archive and successful
run per quarter. Do not commit the manifest or generated diagnostics:

```json
[
  {"year": 2025, "quarter": 2, "archive": "data/enoe/official/2025q2/enoe-2025q2-official.zip", "run_id": "<uuid>"}
]
```

Then run:

```bash
uv run --locked python -m platform_work_reform.enoe_quarter_matrix \
  artifacts/enoe-quarter-manifest.json > artifacts/enoe-quarter-matrix.json
```

The matrix verifies source/staged selected-field fingerprints and group counts,
actual staged row counts and each parent/child join, and independent national
point totals. It reports VIV/HOG/SDEM support, completed-resident and age/activity
domains, missing design keys and pairwise overlap counts of singleton
`(entity, est_d_tri)` codes. It never emits person records or the stratum/UPM
identifiers. Duplicate quarters or mismatches fail closed.

Shared codes do not establish unchanged strata, geographic populations or
cross-quarter person identity. Zero-domain UPMs are retained in support
diagnostics; none is automatically dropped or assigned a variance correction.
The comparison is evidence of recurrence, not validation of sampling precision.

2026 Q2 provides only a partial initial overlap with selected local IMSS releases
containing `ptpd`: May–June are available, April lacks that field. This stage
does not equate that partial window to a complete quarterly platform count or
perform the P18 population comparison.

## Local operational evidence (2026-11-04)

All three added releases completed in the active local PostgreSQL database.
Identical repeat loads returned the same counts without adding runs. The
four-quarter matrix passed: exact source/staged selected-field fingerprints,
all five actual staged table counts, all five child/parent relationships with
zero unmatched children, and all four independent national point totals per
quarter. The original Q3 run was retained and reverified.

| Quarter | VIV rows | HOG rows | SDEM rows | COE1 rows | COE2 rows |
|---|---:|---:|---:|---:|---:|
| 2025 Q2 | 150,442 | 151,468 | 423,744 | 346,404 | 346,404 |
| 2025 Q3 | 150,405 | 151,354 | 422,306 | 346,524 | 346,524 |
| 2025 Q4 | 150,356 | 151,333 | 419,038 | 344,166 | 344,166 |
| 2026 Q2 | 150,350 | 151,316 | 417,128 | 344,709 | 344,709 |

Successful local runs (operational references, not portable database IDs):

- 2025 Q2: `3509f056-b7a4-4d5b-9222-3895e526d51f`.
- 2025 Q3: `fe197954-1c2d-4880-8bf5-16b2fa432905`.
- 2025 Q4: `dd4d7739-0dea-4b58-94da-99b7f5a1475d`.
- 2026 Q2: `a15921d9-f298-4550-bf4d-5691992e8779`.

Observed support uses original `(entity, est_d_tri)` and nested `upm`, before
filtering to an analytical domain:

| Quarter | SDEM strata | SDEM nested UPMs | SDEM singleton strata | VIV/HOG singleton strata | Parent UPMs absent from SDEM |
|---|---:|---:|---:|---:|---:|
| 2025 Q2 | 743 | 21,192 | 7 | 5 | 59 |
| 2025 Q3 | 744 | 21,203 | 23 | 24 | 49 |
| 2025 Q4 | 724 | 21,194 | 11 | 11 | 45 |
| 2026 Q2 | 722 | 21,216 | 13 | 13 | 44 |

No invalid design keys were observed in these SDEM groups. In Q2, two SDEM
singleton strata have additional UPMs in VIV/HOG; the other five remain
singletons in those parent tables. None of the SDEM singletons in the other
three quarters gains additional parent UPMs. The Q3 parents contain one stratum
absent from SDEM, explaining their higher singleton count.

Only the Q4/2026 Q2 pair shares one singleton entity/stratum code; the other
five pairs share none. This establishes recurrence of the support problem,
not stable membership of affected strata. Excluding Q3 alone would not remove
the need for a justified variance policy. Continue source-faithful preparation
while keeping issue #42 and national precision explicitly unresolved.

Validation: `just check` passed 103 unit tests and all shared hooks;
`just db-test` passed 28 isolated integration tests (one optional real-source
test skipped). The separate real-data operations above validate the actual
added releases, rather than treating synthetic fixtures as empirical evidence.
The private manifest and full aggregate matrix remain in ignored `artifacts/`.
