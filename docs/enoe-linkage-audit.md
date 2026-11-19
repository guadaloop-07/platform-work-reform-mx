# ENOE 2025 Q2–Q3 individual-linkage feasibility audit

Issue #65. Contract `enoe-linkage-audit-v1`. This is an aggregate sample-feasibility
audit, not a longitudinal analytical release. It creates no microdata export,
national transition estimate, formalization rate, individual IMSS linkage,
platform label or causal effect. It is independent of open PRs #62 and #64.

## Evidence and scope

INEGI, *Encuesta Nacional de Ocupación y Empleo (ENOE). Seguimiento e
identificación de viviendas en ENOE, ETOE y ENOE (Nueva edición)*, March 10,
2021, [pages 1–2](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/seguimiento_enoe-etoe-enoen.pdf),
lists entity/CON/V_SEL for dwellings and adds N_HOG/H_MUD/N_REN for people.
It describes advancing N_ENT for the traditional sample and distinguishes
telephone tracking. This is historical methodological guidance, not proof that
every 2021 telephone-specific rule applies in 2025.

INEGI's [2025 metadata](https://www.inegi.org.mx/rnm/index.php/catalog/1121)
describes five quarterly visits and 20% sample replacement, and separately
reports face-to-face and telephone components. The
[2025 structure](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf)
identifies ENT through Q2 and CVE_ENT starting Q3 and defines demographic fields.
Actual original Q2/Q3 bundled SDEM dictionaries and catalogues were inspected:
`tipo=1` is ENOE, `tipo=2` ENOE-CATI, `n_ent=1..5` interview order, and `c_res=3`
new resident. The executable maps only the documented entity-name change into
an internal diagnostic slot; original columns and bytes remain unchanged.
Archive and selected SDEM dictionary hashes accompany execution results.

## Candidate linkage and quarantine rules

Within-quarter joins use the full original table key including TIPO/MES_CAL/CD_A;
header, row width, uniqueness and all selected ASCII codes are checked. COE1
occupation/activity catalogue membership is verified for eligible occupied people.
Original source national activity/count totals must reconcile with one explicit
prepared database run per period, and archive hashes must match before and after.
No new ingestion or database mutation is performed.

Cross-quarter candidate key: `(entity, con, v_sel, n_hog, h_mud, n_ren)`, restricted
to `tipo=1`. Calendar month and period are not required to stay equal. Birth date
and sex are validation evidence, not fuzzy identifiers used to create new links.
`h_mud` is never dropped to recover a failed match. All occurrences of a repeated
reduced key are quarantined; the command does not pick a first/last record.

This first audit deliberately excludes `tipo=2`; its raw and baseline-screen
exclusions remain visible. No claim that these records are errors or untrackable
is made. Investigating current telephone linkage and mode changes is separate
work. The analysis does not describe retention for the entire ENOE sample.

A candidate is supported by the diagnostic when:

- Both reduced keys are unique, with complete key fields and TIPO=1.
- Baseline interview is 1–4 and follow-up interview is exactly one higher.
- UPM and CD_A are present and unchanged. Context differences are quarantined;
  they are not silently recoded or assumed to establish a different person.
- Sex is known and consistent. Age increases by zero or one; special age 97 is
  treated as capped (96→97 and 97→97 allowed), while 98/99 or missing ages are
  unresolved rather than literal ages.
- Comparable birth-day/month/year components do not conflict and complete
  calendar dates are valid. Missing/unspecified components are not equal-date
  evidence; the number of comparable components is reported separately.
- An existing baseline resident is not labeled a new resident (`c_res=3`) at
  follow-up. Such candidates are conflicts requiring investigation.

Demographic consistency does not prove identity. A supported pair with only
sex/age/context agreement is distinguished by its comparable-birth-component
count from one with all three date components available. Unknowns are not
imputed. Missing demographic information on departed residents can make a key
candidate unresolved even though the row remains in SDEM.

## Population, retention and composition

Baseline populations use the reviewed completed-interview, residence 1/3,
age 15–98 and valid activity/positive quarterly weight preparation rules.
Age 98 is the unspecified-adult category. The national universe is reconciled,
but **no survey weights are used to expand linked records**.

Four baseline occupied screens are retained independently of outcomes:
passenger `p3=8342`; delivery `p3` in 8344/9321/9722/9723; narrow passenger
additionally `p4a=4850`; broad transport/delivery additionally includes freight
8341. All are occupational approximations including nonplatform work. Overlapping
screens must not be added. No follow-up occupation restriction selects links.

For every baseline screen the audit separates fifth-interview scheduled exits,
unsupported types/missing keys, reduced-key ambiguity, unmatched continuing rows,
conflicting/unresolved candidates, supported pairs outside the follow-up universe,
and supported pairs eligible in both periods. The continuing denominator counts
baseline TIPO=1 complete-key rows with interviews 1–4, including ambiguous rows.
Exclusions must be read alongside retention; the 80% rotation design is a dwelling
property, not a guaranteed individual linkage rate.

Unmatched continuing rows are classified using SDEM-observed household and
dwelling presence. Changed H_MUD is only a possible household-replacement flag.
These are not complete VIV/HOG frame counts or established individual-attrition
causes. Their denominators must not be treated as a response-rate estimate.

Unweighted baseline sex, age band, activity and position distributions are
reported for supported, scheduled-exit and other records, with an additional
strictly unmatched subset. Compare these before any longitudinal inference.
Follow-up availability includes COE1/COE2 presence, occupied status and baseline
screen persistence. Neither continued employment nor occupation is required for
a consistent person candidate; otherwise leavers would be selected out.

## Reproduction and outputs

```bash
uv run --locked python -m platform_work_reform.enoe_linkage \
  artifacts/enoe-quarter-manifest.json --output-dir artifacts/enoe-linkage-audit
```

The manifest selects explicit reviewed archive/run pairs for 2025 Q2 and Q3;
it can also contain the existing other reviewed quarters, which are not analyzed.
Duplicate periods/run IDs and absent required periods fail before source reads.
Output is written only after both sources reconcile. JSON contains source/run/hash
provenance, national reconciliation, interview progression, candidate diagnostics,
flow and composition counts. CSV and Markdown summarize the screen-specific
sample feasibility. Generated outputs remain ignored outside Git. Candidate keys,
UPMs, household identifiers, birth dates and person rows are never emitted.

`selected_sdem_sha256` hashes ordered compact sorted-key JSON rows of selected
original logical ASCII SDEM values before adding derived fields. It is a private
aggregate provenance fingerprint, not a source/staging equality proof. The existing
national preparation reconciliation is an independent population check, not an
independent fingerprint of every selected demographic staged field.

Before estimating national transitions, establish longitudinal weighting and
attrition treatment, target-domain precision and rotating-panel covariance.
Issue #42 remains unresolved. Household identity does not identify employer/job
continuity, and panel linkage alone does not identify platform work or causality.

## Local operational findings (2026-11-19)

Both original archives passed hash and national source/preparation reconciliation.
Each period's selected occupation catalogues and SDEM dictionary hashes are
recorded in the ignored JSON. Reduced TIPO=1 person keys were unique in both
periods: 386,103 Q2 and 385,232 Q3 rows, with zero ambiguous reduced keys.
The TIPO=2 source counts were 37,641 and 37,074 respectively; they remain outside
this first linkage contract, not silently classified as individual losses.

There were 283,159 raw candidate pairs across all SDEM ages/residence states.
Their interview transitions were 71,187 for 1→2; 70,674 for 2→3; 70,066 for 3→4;
and 71,232 for 4→5. These are all-SDEM candidate counts, not the eligible adult
or occupational-domain counts below. Flags may overlap and must not be added as
mutually exclusive rejected-pair totals.

| Baseline population | All eligible baseline sample | TIPO=1 scheduled exits | TIPO=1 interviews 1–4 | Supported both eligible | Supported / continuing (%) |
|---|---:|---:|---:|---:|---:|
| All eligible ages 15+ | 324,613 | 58,493 | 237,421 | 215,462 | 90.75 |
| Passenger | 4,344 | 801 | 3,192 | 2,878 | 90.16 |
| Delivery | 1,633 | 311 | 1,187 | 1,059 | 89.22 |
| Narrow passenger | 3,962 | 735 | 2,916 | 2,628 | 90.12 |
| Broad including freight | 10,075 | 1,857 | 7,416 | 6,686 | 90.16 |

The headline baseline includes unsupported types; it is not the denominator of
the last column. Passenger TIPO=2/missing-key exclusions were 351 and delivery
135. Among passenger continuers, 3,000 had unique candidate counterparts: 2,878
were supported and eligible, 116 unresolved, one conflicted and five supported
but outside follow-up eligibility. Another 192 continuing rows had no unique
counterpart. For delivery, 1,118 had candidates, of which 1,059 were supported and
59 unresolved; 69 continuing rows were unmatched. The categories are sample
feasibility states, not formal/informal transitions.

All supported eligible passenger and delivery pairs had COE1 and COE2 at follow-up.
Of the 2,878 passenger pairs, 2,678 were occupied at follow-up and 2,164 met the
same passenger screen. Of the 1,059 delivery pairs, 938 were occupied and 541 met
the same delivery screen. Restricting follow-up to the same occupation would
therefore materially select the panel. These are availability diagnostics; they
do not establish employer continuity or genuine occupation changes rather than
classification changes.

For the supported passenger pairs, 2,604 had three comparable birth components,
223 one, and 51 two. For delivery, these counts were 967, 79 and 13. No supported
pair in these two screens relied on zero comparable birth components, but this
is an observed finding, not a universal property of the diagnostic contract.
A subsequent analysis can explicitly examine full-date-only sensitivity.

The supported samples make a next-stage longitudinal investigation feasible;
they do not establish adequate precision for every transition cell. Retention,
selection, current telephone linkage, longitudinal weights and #42 remain open.
Generated `linkage.md`, `linkage.csv` and full aggregate `linkage.json` remain at
`artifacts/enoe-linkage-audit/` outside Git. No candidate or person-level keys
were exported.

Validation: `just check` passed 137 unit tests; `just db-test` passed 32 isolated
integration tests, with one optional original-source check skipped. The 27 new
synthetic cases cover collisions, interview/reset patterns, household replacement,
sex/age/birth conflicts, unknown demographics, capped ages, new residents,
occupation change, follow-up noneligibility, denominator preservation, unsupported
types, empty exports and rejected manifests. Real-source execution is separate
from those fixtures. No new migration or production database write was introduced.

Composition diagnostics are descriptive sample comparisons. The female share is
3.23% among supported passenger pairs versus 5.21% among the 192 strictly unmatched
passenger continuers; corresponding age-15–29 shares are 13.69% and 14.58%.
For delivery, female shares are 9.54% versus 1.45%, and age-15–29 shares 42.78%
versus 50.72% among 69 strictly unmatched continuers. These small unmatched groups
and unvalidated uncertainty prohibit significance or representativeness claims.
They illustrate why the matched sample cannot automatically receive the original
quarterly weights without evaluating selection.

Household/dwelling unmatched-status labels refer specifically to the **unique
TIPO=1 SDEM index**, not the entire follow-up housing frame or telephone component.
In particular `unmatched_dwelling_not_in_sdem` means absent from that supported
index; it does not prove the dwelling was absent from all Q3 source tables.
All-SDEM interview/residence matrices and baseline-type counts use broader
universes than screen-specific eligible-adult retention and must not be mixed.
