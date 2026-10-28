# IMSS staging load

Apply migrations with `just db-migrate`, then load one inventoried file:

```bash
uv run --locked python -m platform_work_reform.imss_staging \
  '/path/to/asg-2026-09-30.csv' --manifest artifacts/imss-inventory-2023-2026.json \
  --encoding cp1252
```

The command verifies the source against its inventory SHA-256 before and after
streaming COPY. It validates the exact header, strict decoding and row width.
Rows, staging metadata and success status commit together. On failure, data rows
roll back and a separate transaction records the failed run. Repeating the same
source and period returns the existing row count without inserting duplicates.

`staging.imss_row.raw_fields` preserves the thirty source positions as text. The
fifth position is SQL NULL when the legacy source lacks `ptpd`; source blanks and
`NA` remain distinct strings. Staging is not a published or typed analytical table.
Never sum all versions without selecting one per period.

For the local September 2026 pilot, the original and staging agree on 4,708,094
rows and the sums of all 17 metrics. Data bytes after the header were entirely
ASCII, so CP1252 and ISO-8859-1 produce identical text for this file. The staged
table occupied about 1,477 MiB. Other months need their own encoding validation,
reconciliation, and resource checks before use.
