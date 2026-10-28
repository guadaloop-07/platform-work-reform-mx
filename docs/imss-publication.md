# Reconciled IMSS monthly publication

Apply migrations, stage a source, then run:

```bash
uv run --locked python -m platform_work_reform.imss_publish \
  '/path/to/asg-2026-09-30.csv' --manifest artifacts/imss-inventory-2023-2026.json \
  --encoding cp1252
```

The source must match its recorded SHA-256 before and after the independent scan.
Publication requires the staging layout, encoding, row count, 17 metric sums,
and missing-value counts to match. Decimal values are compared exactly. The audit,
dataset version, and period selection commit in one transaction. A second source
version for an already selected month is rejected, not silently substituted.

`imss.monthly_cells` exposes only selected months. `ptpd` remains NULL if absent
from the original layout. Metric blanks and `NA` are mapped to SQL NULL in the view;
the exact source strings remain in staging. Changes to selected staging rows would
invalidate the audit; restrict direct database writes and restore from source if
that occurs. Database role separation is a later stage.
