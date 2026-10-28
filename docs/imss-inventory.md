# Local IMSS source inventory

The proposed initial research window starts in January 2023 and extends through
the latest available month. This allows multiple pre-reform seasonal comparisons;
it does not establish a pre-reform platform-worker cohort in IMSS.

Create a private manifest in the ignored artifacts directory:

```bash
uv run --locked python -m platform_work_reform.inventory \
  '/path/to/IMSS files' --start 2023-01-01 --end 2026-09-30 \
  --output artifacts/imss-inventory.json
```

Only month-end `asg-YYYY-MM-DD.csv` files and named variants such as
`asg-YYYY-MM-DD-revision.csv` are inventoried. SHA-256 is computed by streaming
each file once. Identical content and differing versions of a period are reported;
no version is selected automatically. The manifest includes the local source path,
so do not commit or publish it without review. Existing manifests are not replaced.
Hashes do not prove official origin. Files changing during hashing are rejected.

Header inspection of the supplied local collection found no `ptpd` in 2025 or
January–April 2026; it appears in May–September 2026. This is an observation of
the local file versions, not proof of the official historical schema or that no
platform workers existed. Verify official historical versions and alternatives
before claiming a complete platform-specific series. Encoding and CSV parsing are
separate P07–P08 tasks. This inventory does not load records into PostgreSQL.
