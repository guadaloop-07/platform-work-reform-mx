# ENOE 2025 Q3 observed design-support audit

This read-only diagnostic advances issue #42; it does not complete survey-design
precision validation. It measures support in the observed SDEM records, not in
the full sampling frame. No singleton correction or variance estimator is chosen.

```bash
uv run --locked python -m platform_work_reform.enoe_design_support --run-id <run-uuid>
```

The command requires one explicit successful reviewed `enoe-2025q3-v1` load,
checks the recorded archive hash, period and complete ordered SDEM header, and
reads under a repeatable-read read-only snapshot. Metadata validation does not
independently re-hash staged bytes. An unknown, unsupported or empty run fails.
Only aggregate counts, support histograms and provenance are emitted; person
records, stratum codes and UPM identifiers are not printed.

## Definitions

Design keys use the original CSV names `cve_ent`, `est_d_tri` and `upm`,
preserving their code strings. Strata are nested by entity, and UPMs by stratum.
Multiple persons sharing the same nested UPM contribute once to its support.
Blank, non-ASCII, nonnumeric or zero design keys are counted separately outside
completed residents and rejected among completed residents, including children.
This is a structural key check, not validation against every official code list.

The audit compares all observed records; completed resident interviews
(`r_def=0`, `c_res` 1 or 3) at all ages; the reviewed 15-plus pilot universe;
and its PEA domain. Age, activity and eligible quarterly-weight validation reuse
the [national pilot rules](enoe-national-pilot-indicators.md), including treatment
of age codes 98 and 99. Source values are not imputed. Weighted totals are
reconciliation diagnostics only.

For the two age/activity domains, the report also retains every stratum in the
completed-resident parent population. It counts strata with zero, one, or at
least two UPMs contributing domain records, and parent UPMs with no domain
records. A parent UPM without domain members is not evidence that the UPM was
absent from the sample. This parent is a diagnostic comparison, not an approved
variance frame or a reconstruction of missing/nonresponding households.

## Reviewed local audit

The reviewed source SHA-256 is
`7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566`.
The command was run on 2026-11-04 for pilot run
`fe197954-1c2d-4880-8bf5-16b2fa432905`.

| Observed population | Records | Entity/stratum combinations | Nested UPMs | Single-UPM strata |
|---|---:|---:|---:|---:|
| All SDEM | 422,306 | 744 | 21,203 | 23 |
| Completed residents, all ages | 411,562 | 744 | 21,203 | 23 |
| Reviewed 15-plus universe | 325,108 | 744 | 21,203 | 23 |
| PEA | 196,643 | 744 | 21,131 | 23 |

No invalid design keys were observed. All completed-resident strata contain
15-plus and PEA records. However, 72 parent UPMs have no PEA records. The 23
single-UPM strata are already present before age and activity restrictions;
these restrictions alone do not explain them. This does not establish that
they are certainty strata or justify assigning zero variance. National weighted
totals reproduce the existing pilot reference values.

## Remaining precision gates

[INEGI metadata](https://www.inegi.org.mx/rnm/index.php/catalog/1121) describes
ultimate-cluster and Taylor methods, but the operational implementation still
requires period-specific methodological support and independent validation.
Issue #42 must determine the applicable design population, treatment of
nonresponse, official handling of the observed singleton strata, variance
formulas, degrees of freedom and confidence level. Validate against the
[published precision workbook](https://www.inegi.org.mx/rnm/index.php/catalog/1121/download/36732)
or a trusted independent implementation with documented assumptions. Do not
publish standard errors, CVs or confidence intervals based on this audit alone.
