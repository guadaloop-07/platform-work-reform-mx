# ENOE 2025 Q3 prepared person-quarter pilot

Migration 0006 adds `enoe.prepared_person_2025q3_v1`, a read-only view based
on the source-faithful person-quarter view. It contains one row per SDEM
person per successful reviewed run, with run and source IDs, quarter, full
source key, source row numbers for SDEM and optional COE records, and the source
codes `eda`, `r_def`, `c_res`, `fac_tri`, `clase1`, and `clase2`. The view
checks the reviewed archive hash in metadata and the exact ordered SDEM header
signature; it does not re-hash staged rows. Original byte arrays remain in
staging. The displayed codes use PostgreSQL's bytea escape representation and
trim surrounding spaces; they are not a decoding of ambiguous free text.

`preparation_status` is `eligible`, `outside_universe`, or `invalid` for the
national 15-plus point-estimate universe described in
`enoe-national-pilot-indicators.md`. It checks completed interviews, residence,
age, weight and activity-code consistency. `quarterly_weight` is a positive
integer only for eligible rows; NULL elsewhere does not mean zero. Invalid
codes remain visible for review, not imputed or included in estimates. Weight
and activity codes outside the universe are retained without interpreting their
meaning. Age code 98 is eligible under the official precoded-variable universe;
99 is under 12, not a literal age.

Consumers must explicitly select a run and confirm the expected source,
counts and absence of invalid rows before using the view. Reconcile with
`enoe_pilot_indicators` and published INEGI results. This view is not an
authorization to export individual records or publish survey estimates. It
does not establish variance, representativeness at every geography, panel
identity, individual IMSS linkage or platform-worker status.
