# Resumable IMSS monthly batch

The batch checks the inventory has exactly one file per requested month and
verifies available space using `df` inside the actual PostgreSQL container. It
keeps at least 20 GiB free or ten times the source file size, whichever is larger.
This is a conservative guard, not a guaranteed bound on PostgreSQL's growth.

UTF-8 headers and BOM are recognized. For single-byte headers, the file is checked
for byte values 0x80–0x9f: if present, CP1252 and ISO-8859-1 may differ and the
batch stops for review. Full-file strict decoding, hash validation, staging and
independent metric reconciliation are performed by the existing commands.

```bash
uv run --locked python -m platform_work_reform.imss_batch \
  '/path/to/IMSS files' --manifest artifacts/imss-inventory-2023-2026.json \
  --start 2023-01-01 --end 2026-09-30 --progress artifacts/imss-batch.jsonl
```

The progress log is local, private and append-only. On an error the batch stops;
fix the cause and rerun the same command. Already selected months are verified by
hash and skipped; staged but unselected months are reconciled before selection.
No month is silently replaced when another version is already selected. Source
files remain untouched. Reconciliation is aggregate and does not establish causal
comparability or verify every dimension value.
