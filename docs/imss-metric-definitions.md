# IMSS affiliated job counts

For this project, use **`ta`** in `imss.monthly_cells` when counting IMSS
affiliated jobs (puestos de trabajo afiliados), also described by IMSS as
insured jobs or insured persons associated with a job. The unit is an
affiliated job as defined by IMSS; do not label the result as a count of
distinct individuals.

Do not substitute **`asegurados`** for `ta`: the official guide defines
`asegurados` as total insured persons, a broader measure. The separate
`no_trabajadores` field refers to insured persons without an associated job.
Retain these original field names and choose a different measure only when the
research question explicitly calls for its corresponding population.

The source is the IMSS [Guía del usuario datos abiertos, asegurados](https://datos.imss.gob.mx/sites/default/files/Guia_usuario_datos_abiertos_asegurados.pdf)
and [Glosario de datos abiertos, asegurados](https://datos.imss.gob.mx/sites/default/files/glosario_datos_abiertos_asegurados_.pdf).
Use the definitions applicable to each source version and document any change.

The view contains aggregate cells and one selected source version per month.
When summing `ta`, specify the reference month, population and dimensions, and
ensure the selected cells do not overlap. Do not add monthly snapshots to
report a count of unique jobs or people over a longer period. Numeric blanks
and `NA` are represented as SQL `NULL` in the view; document missingness and do
not silently interpret it as zero. Historical source layouts without `ptpd`
retain it as `NULL`, so absence of `ptpd` does not mean absence of platform
work. These aggregate records do not support individual IMSS–ENOE linkage.

## Provisional platform series (issue #59)

The user supplied a transcription of the IMSS dictionary on 2026-11-09:
`ptpd`: “Identificador de trabajador de plataforma digital 1: Es trabajador de
plataforma 0: No es trabajador de plataforma”. The transcription identifies
`ta` as “Puestos de trabajo afiliados al IMSS (empleos asegurados o asegurados
asociados a un empleo)”. The user reported temporary site unavailability.
No original dictionary file, exact URL, publication version, applicability date
or official-file hash was supplied or independently verified. This evidence is
user-supplied, not a retrieved official source. Contract
`user-transcription-2026-11-09-v1` permits provisional implementation of
`SUM(ta)` for `ptpd = 1`; official-source publication remains pending recovery
and verification of the applicable dictionary. Do not infer unique persons,
threshold qualification, insurance branches or reporting-cutoff rules.

```bash
uv run --locked python -m platform_work_reform.imss_platform_series
```

The command uses a read-only repeatable-read snapshot of selected reconciled
months, retaining reference date, run, source ID/hash/name and layout. It emits
aggregate JSON only. It checks row counts against load metadata and independently
aggregates overall and raw-code totals, reconciling counts, observed sums and
missing metric counts. A historical reconciliation record is required; this
command does not re-read or rehash the original source files.

Codes `1` and `0` are exact; NULL, blank and `NA` are separate raw missing
states combined into a reported missing-classification bucket. Other codes fail
without emitting a report. Negative, fractional and nonfinite `ta` values fail.
A category with any missing `ta` has a NULL total, with missing-row counts
reported; observed partial sums are never labeled complete totals. An empty
category in a platform layout has zero jobs. Legacy layouts require NULL `ptpd`
and return NULL platform/nonplatform totals with status `unavailable`, even if
no platform-coded row exists. Months absent from the selection are omitted,
not filled. Classification missingness in a platform layout remains visible;
its platform bucket is the count of explicitly identified jobs only.

Each output carries the provisional source status and contract. No official
publication or ENOE comparison is performed. Recover the official dictionary,
record unchanged bytes/hash and period applicability, and reconcile coverage
before changing that status. Never add monthly stocks to estimate unique people.

### Local validation (2026-11-09)

The read-only command reconciled all 44 selected months and 199,395,921 rows.
Thirty-nine legacy months returned unavailable platform/nonplatform totals.
The five platform-layout months (May–September 2026) contained only codes 0/1,
with no missing `ta` or missing classification. For each month the platform
and nonplatform job totals exactly matched overall `ta`; no invalid count or
code was encountered. The aggregate report, including each selected source
hash and run, is retained outside Git at `artifacts/imss-platform-series.json`.
This is operational reconciliation under the provisional transcription contract,
not independent verification of the official dictionary or source dimensions.

`just check` passed 110 unit tests and shared hooks. `just db-test` passed 32
isolated PostgreSQL integration tests, with one optional original-source test
skipped. The initial integration attempt found PostgreSQL stopped; after
`just db-up`, the full integration suite passed. Tests cover legacy missingness,
platform/nonplatform/missing partitions, missing metrics, provenance, invalid
codes/counts and reconciliation failures. The actual selected-month audit was
executed separately from synthetic tests.
