# ENOE person-quarter pilot foundation

After migration 0005, `enoe.person_quarter_pilot` exposes one row per SDEM
record in a successful 2025 Q3 `enoe-2025q3-v1` load. It joins COE1 and COE2
by the full source person key and run ID. Database uniqueness prevents a join
from multiplying people within a load. The view retains the load, source file,
period, source key and source row numbers for provenance. It exposes original
logical values as byte arrays; headers in `staging.enoe_table` describe their
positions. NULL questionnaire arrays and row numbers mean no corresponding
questionnaire row, not zero or an inferred reason for absence.

The view does not select one release if several are loaded. Consumers must
explicitly choose a `run_id` and verify its provenance before aggregating.
It does not interpret variables, establish eligibility, handle survey design or
weights, or provide analytical estimates. See `enoe-source-contract.md` for
period-specific universes and encoding limitations. Preserve the source archive.

For the reviewed pilot, verify 422,306 SDEM records, 346,524 matched COE1 and
COE2 records each, and 75,782 people without each questionnaire. These counts
are a reconciliation check, not validation of each field or survey estimate.
