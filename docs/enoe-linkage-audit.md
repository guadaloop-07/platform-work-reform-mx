# ENOE 2025 Q2–Q3 individual-linkage feasibility audit

Issue #65. Current contract `enoe-linkage-audit-v2`. This is an aggregate sample-feasibility
audit with an optional sample-transition extension, not a validated population release. It creates no microdata export,
national transition estimate, national formalization rate, individual IMSS linkage,
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

## Original v1 local operational findings (2026-11-19)

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

## Optional sample employment transitions

The user-authorized v2 extension uses `--transitions` to tabulate released
principal-employment states within the consistency-supported, both-eligible
pairs. It does not require continued occupation or continued employment.
`emp_ppal=1` is informal principal employment, 2 formal, 0 not applicable and
blank unresolved. For nonoccupied eligible people, `clase2=2` is unemployment;
3/4 are inactivity, not informal work. Occupied codes are checked against both
original source catalogues and unknowns never become formal/informal statuses.

```bash
uv run --locked python -m platform_work_reform.enoe_linkage \
  artifacts/enoe-quarter-manifest.json --transitions \
  --output-dir artifacts/enoe-sample-transitions
```

The matrix has six states per endpoint, including explicit unknown/not-applicable
formality. Its sum equals the supported linked sample for every baseline screen.
The informal→formal percentage divides the corresponding sample count by **all
linked people informal at baseline**, including those unemployed, inactive or
with unknown formality at follow-up. The reverse rate has its own formal-baseline
denominator. These rates must not be subtracted as an estimate of net national
formalization. Both endpoints refer to principal employment and do not establish
continuity of employer/job, a platform relationship or a reform effect.

`transitions.csv` exports all 36 cells per screen, including zeros.
`transitions.md` summarizes the two directional flows. `linkage.json` adds
sample matrices, baseline-state retention by linkage status and a full-birth-date
sensitivity requiring three comparable components. The latter has its own
baseline denominators; it is not a random subsample by assumption. Existing v1
outputs remain separate; default execution without the flag does not read new
employment fields or estimate transitions.

### Precision and expansion are separate questions

Records do not possess statistical significance. Significance concerns a stated
hypothesis/contrast; precision concerns uncertainty of an estimator; expansion
weights concern the target population and selection/response probabilities.
A p-value or sample count alone cannot authorize a weight or prove adequate
precision. A high retention rate also does not remove nonresponse selection.

INEGI's [ENOE 2025 metadata](https://www.inegi.org.mx/rnm/index.php/catalog/1121)
describes quarterly weight adjustments and ultimate-cluster precision estimates.
Its [tabulated precision documentation](https://www.inegi.org.mx/contenidos/programas/enoe/14ymas/doc/enoe_tabulados.pdf)
explains why rare characteristics and finer breakdowns need cell-specific errors
and CVs. These sources do not validate a longitudinal weight for our selected
linked sample. No universal minimum sample-size rule is applied here.

The extension reports the number of baseline nested UPMs and entity/strata with
observed events in each cell, maximum events in one UPM and missing-design counts.
These are unweighted support diagnostics, not design degrees of freedom, effective
sample sizes, SEs, CVs or confidence intervals. A stratum with a single event UPM
is not necessarily a singleton sampling stratum: zero-event UPMs still belong in
variance estimation. No zero-domain design units are declared disposable.

Before nationally expanding transitions, establish a suitable longitudinal target
and weights accounting for rotation, follow-up eligibility, unsupported telephone
records, linkage/response selection and calibration, and validate the variance
estimator. Neither summing baseline/follow-up `fac_tri` over survivors nor applying
a universal 1/0.8 correction is treated as validated. Issue #42's variance
population and singleton questions remain open, with additional longitudinal
requirements. This restriction does not imply weights can never be developed;
it means this extension does not yet supply a justified population estimator.

### V2 sample-transition findings (2026-11-19)

The real two-quarter execution with `--transitions` reverified original hashes,
headers, national preparation reconciliation and occupation catalogues and
additionally verified original `emp_ppal` catalogue membership. Supported linkage
counts match the original audit. Every six-by-six matrix sums to the corresponding
linked sample, and baseline-state retention partitions sum to the full baseline
sample. Full-birth counts never exceed their corresponding all-supported cells.

| Baseline screen | Linked informal in Q2 | Informal→formal | Sample % | Linked formal in Q2 | Formal→informal | Sample % |
|---|---:|---:|---:|---:|---:|---:|
| All eligible | 65,173 | 7,931 | 12.17 | 61,300 | 7,685 | 12.54 |
| Passenger | 2,018 | 348 | 17.24 | 860 | 264 | 30.70 |
| Delivery | 768 | 82 | 10.68 | 291 | 85 | 29.21 |
| Narrow passenger | 1,958 | 334 | 17.06 | 670 | 237 | 35.37 |
| Broad including freight | 3,678 | 625 | 16.99 | 3,008 | 589 | 19.58 |

These are individual-state changes within consistency-supported sample pairs,
not expanded national people or reform effects. Screens are fixed at baseline
and include nonplatform work. Changes may accompany a different job or occupation.
The two directional percentages have different denominators. Their difference
is not a net formalization rate. Full-date-only sensitivity gives 308/1,839
(16.75%) passenger informal→formal cases and 71/710 (10.00%) delivery cases,
versus 17.24% and 10.68% with all supported links. This supports a bounded identity
sensitivity check, not general robustness to attrition, classification or design.

Among linked informal baseline members, 152 passenger and 102 delivery cases move
to unemployment or inactivity. They remain in the reported informal-baseline
denominators. Do not condition on continued occupation or employment to recover a
more favorable transition proportion.

The passenger informal→formal cell has 348 observations across 335 nested baseline
UPMs and 181 entity/strata; the delivery cell has 82 across 81 UPMs and 65 strata.
The largest event count in one UPM is two for each cell; no baseline design key
is missing. This indicates the observed events are not concentrated in one or
two UPMs, but does not establish precision or a significant reform effect.
Zero-event UPMs and the full variance population remain necessary for inference.

Six additional synthetic tests check nonemployment/unknown denominators, reverse
flows, full-date sensitivity, nested design support, unweighted arithmetic,
nonapplicable codes, full-cell exports and linkage integration without an
occupation-survival condition (33 tests across linkage and transition modules).
`just check` passed 143 unit tests; `just db-test` passed 32 isolated integration
tests, with one optional original-source check skipped. No new dependencies,
migration, source mutation or population weights were introduced. The aggregate
outputs are ignored under `artifacts/enoe-sample-transitions/`.
