# P17 IMSS–ENOE measurement contract, version 1

Issue #57; evidence reviewed 2026-11-06. This contract supports the
[P18 feasibility study](imss-enoe-comparability.md), with the
[policy calendar](p17-policy-calendar.md) and
[source register](p17-source-register.md). It defines available concepts and
remaining gates; it does not implement or estimate candidate populations.

## Units and IMSS field gate

Use `ta` in `imss.monthly_cells` as affiliated jobs, under the existing
[metric contract](imss-metric-definitions.md). Do not substitute `asegurados`
or interpret a sum as distinct persons. Preserve the selected monthly source
version, hash, reference date, missingness and layout. ENOE's analytical unit is
one eligible person per explicit quarterly run, not an employer registration or
platform account. Multiple jobs and platforms prevent an assumed one-to-one
conversion; no multiplicity correction is approved.

`ptpd` is available in selected May–September 2026 files. Issue #59 authorizes
a provisional `ptpd = 1` selection using the user-supplied dictionary
transcription, with `0` meaning nonplatform. The [metric contract](imss-metric-definitions.md#provisional-platform-series-issue-59)
records provenance and executable missingness rules. This supersedes the earlier
code-selection hold for provisional implementation only. Official dictionary
version/hash and period applicability remain unverified; threshold qualification,
insurance coverage and reporting-cutoff semantics remain unresolved. Missing
historical `ptpd` remains NULL, never a nonplatform code or zero platform jobs.

The [IMSS rules](p17-source-register.md#s02-imss-rules) explain registration and
monthly adjustment obligations. They do not define the open-data column.
Comparisons with institutionally published unique-person counts require a
separate unit and coverage reconciliation even after the codebook is obtained.

## ENOE source scope and universe

The audit inspected original SDEM, COE1 and COE2 dictionary members and the
selected fields' catalogues in all four reviewed archives (2025 Q2/Q3/Q4 and
2026 Q2), and confirmed presence in their actual CSV headers. It read no person
records and generated no empirical estimates. Archive and member hashes are
recorded in [S09](p17-source-register.md#s09-reviewed-enoe-archives).
The 2025 structure PDF supports the field interpretation; the actual bundled
2026 Q2 dictionaries are the period-specific evidence for that release. A guessed
2026 structure URL returned non-PDF content and is not evidence of equivalence.

The proposed analytical base is the existing prepared national 15-plus universe,
restricted to occupied people (`clase1=1`, `clase2=1`), using positive `fac_tri`
once per eligible person. Preserve its release-specific interview code, residence
and age rules, including ages 98/99, as specified in
[multi-quarter preparation](enoe-multiquarter-preparation.md). The COE instrument
itself covers age 12-plus; do not confuse its full survey universe with this
15-plus analytical restriction. Each field additionally requires applicability
and response checks. Existing preparation validates national activity only;
the additional fields below are not exposed as validated prepared-view columns.
Issue #61 adds a separate [source/staging and catalogue audit](enoe-variable-validation.md)
for descriptive use, with explicit missingness and unresolved routing. It does
not implement candidate populations or remove the identification gates.

## Variable and code matrix

Codes below are descriptive contract evidence, not executable classification
rules. Original lowercase names refer to the actual CSVs. SDEM catalogues use
`0` for not applicable in the listed categorical fields; a blank or missing
questionnaire is a separate state. Unknown and unspecified responses never
become a substantive no, zero income or nonplatform status.

| Source field | Available meaning and codes | Applicability, missingness and comparison limit |
|---|---|---|
| COE1 `p3` | Four-character occupation catalogue (SINCO); question 3 concerns the principal job. | Occupied base with COE1 and valid occupation. Retain leading zeros and exact catalogue; no occupation list or platform label is selected here. |
| SDEM `c_ocu11c` | Broad occupation groups; `7` transport operators, `11` unspecified. | Occupied base; `0` not applicable. Too broad to isolate app drivers or delivery workers. Q2 catalogue has a serialization anomaly described below. |
| COE1 `p4a` | Four-character economic-activity catalogue for the business/institution in the principal job. | Require COE1 and a valid release catalogue key; `9999` is insufficiently specified. Not a direct match to IMSS economic-risk categories. |
| SDEM `rama`, `scian` | Coarse activity groups. `rama=4` services, `7` unspecified; `scian=8` transport/mail/storage, `21` unspecified. | Occupied base; `0` not applicable. `scian` is a 1–21 grouping, not a full industry code. Neither isolates platforms. |
| SDEM `pos_ocu` | `1` subordinate paid workers; `2` employers; `3` own account; `4` unpaid; `5` unspecified. | Occupied base; `0` not applicable. Survey position does not independently establish the legal platform relationship. |
| COE2 `p6d` | Medical care through this job: `1` IMSS; `2` naval/military/Pemex; `3` ISSSTE; `4` state ISSSTE; `5` another institution; `6` no care; `9` unknown. | Principal-job question, reached through the employment questionnaire. Require COE2; separate blank/not reached from `6` and `9`. It reports access, not administrative registration, insurance-branch completeness or prior coverage. |
| SDEM `seg_soc` | Health-institution access: `1` access, `2` no access, `3` unspecified. | Occupied precoded domain; `0` not applicable. Do not equate access with all five IMSS insurance branches or infer coverage through a particular platform. |
| SDEM `medica5c` | `1` no benefits; `2` health access only; `3` health plus other benefits; `4` other benefits without health access; `5` unspecified. | Occupied precoded domain; `0` not applicable. Distinct from both `seg_soc` and IMSS registration. |
| SDEM `imssissste` | `1` IMSS; `2` ISSSTE; `3` other; `4` no care; `5` unspecified. | Occupied precoded domain; `0` not applicable. The #61 audit confirms agreement with the documented grouping of `p6d=2..4` under code 2; this includes naval/military/Pemex, not only the literal ISSSTE response. Retain job-specific `p6d` for institution detail; not a unique-person match to IMSS. |
| SDEM `emp_ppal` | `1` informal principal employment; `2` formal principal employment. | `0` not applicable; blank/unrecognized separate. Describes the principal job's derived classification, not previous informality or informal-sector status. Use the released classification; reconstructing it requires separate methodology validation. |
| SDEM `t_tra`; COE2 `p7` | `t_tra`: `1` one job, `2` two jobs. `p7`: secondary-activity responses `1–6`, `7` no other job, `9` unknown. | `t_tra=0` not applicable; require COE2 for `p7`. These do not measure number of apps, accounts or employer registrations. Primary-job-only candidates can miss secondary platform activity. |
| SDEM `ingocup` | Monthly labor-income field; dictionary range `1–999998`. | Income is outside the present executable contract: separately verify questionnaire period conversion, zero-income treatment, missing/special codes, job coverage and deflation. Do not apply legal platform net-income factors or the statutory threshold to this field. |

The catalogue meanings above are supported by the original period-specific
members, not by translating variable names. Relevant structural references are
[S07](p17-source-register.md#s07-enoe-structure), PDF pages 20–21 and 26–27,
and basic COE2 page 84. The questionnaire
[S08](p17-source-register.md#s08-basic-questionnaire), PDF page 8, shows `p6d`
after earnings paths, including a direct path for unpaid work. Thus a missing
income answer does not itself establish no health access. The downloaded
instrument bears `COE 2021`; its routing is supporting evidence, while the
reviewed release dictionaries establish the actual field names and response
codes for each period. Issue #61 subsequently retrieved the 2025 RNM-linked COE BÁSICO 2023
seventh version and checked the selected routes; see [S12](p17-source-register.md#s12-enoe-variable-validation-supplements-2026-11-09).
2026 Q2 instrument-version confirmation and complete path validation remain
required before implementing general questionnaire-routing rules. Preserve the downloaded
instrument vintage rather than inventing a separate 2026 version.

## Catalogue findings and unresolved transformations

For the selected fields, the reviewed catalogue bytes are identical across the
four archives except SDEM `c_ocu11c`. Its 2025 Q2 CSV has a third empty header
column and an unquoted comma splitting the code-1 description across columns.
Later catalogues have two columns and a quoted description. This is a source
serialization difference, not evidence of a changed occupation population.
Do not silently repair the catalogue or treat dictionary ranges as proof of
valid observations. A future parser/crosswalk task must explicitly preserve and
handle the anomaly. Some COE dictionary descriptions also contain visible
spelling/character anomalies; originals are unchanged and no text repair is
approved here. Catalogue byte equality does not validate person-level values,
routing, reconstruction algorithms or population estimates.

Before implementation, freeze narrow/broad candidate rules on substantive
questionnaire and occupation/activity evidence independent of IMSS fit. Keep
unknown occupation/activity, unknown health access, absent COE and secondary-job
limitations separate in an exclusion flow. No direct platform relationship
indicator was established in the reviewed field subset; this is not an
exhaustive claim that every ENOE item or later instrument lacks such a question.

## Compatibility and timing decision

| Dimension | Decision for the first comparison |
|---|---|
| Unit | IMSS jobs versus ENOE people: conceptual comparison only until multiplicity and coverage assumptions are explicit. |
| Coverage | Legal registration, monthly qualification and survey medical access are separate. Provisional `ptpd` coding is transcribed; official applicability and coverage remain unresolved. |
| Geography | Begin with national feasibility. Do not equate IMSS employer-registration geography with ENOE residence; validate any workplace/residence mapping before subnational comparisons. No municipal representativeness inference. |
| Occupation/activity | ENOE detail can define candidates after review; no IMSS occupation observation or direct industry-code equivalence is assumed. |
| Time | **No-go for a full-quarter platform comparison using the currently selected releases.** April 2026 lacks `ptpd`; May–June cannot be presented as all of Q2. |
| Precision | #42 remains a gate for reported survey uncertainty and small domains. No CI, CV or variance correction is authorized here. |

ENOE Q2 quarterly estimates pool interview-specific reference weeks and use
`fac_tri`. They are not June month-end stocks or a separately validated May–June
estimator. Do not subset by `mes_cal` and reuse quarterly weights as though that
produced a valid two-month estimate. Do not sum May and June stocks as unique
workers; a two-month stock mean, if later justified, must retain its two-month
label and cannot fill April.

The preferred next source task is to obtain the authoritative `ptpd` layout and
a complete, explicitly versioned common window: review an official April 2026
alternative with the field, or separately ingest/prepare a compatible later
ENOE quarter (e.g. Q3 against selected July–September IMSS). Availability and
comparability must be verified before choosing either route. A deliberately
partial sensitivity comparison would need its own estimand and temporal
justification; it is not approved by this document. These are project decisions
from the evidence and gaps above, not claims made by either producer.
