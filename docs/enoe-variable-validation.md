# ENOE occupation and social-security variable validation

Issue #61; validation contract `enoe-variable-audit-v1`. The intended use is
national descriptive preparation of occupation/activity and medical-access
screens, one eligible occupied person per explicitly selected run. It does not
identify confirmed platform workers or establish an IMSS comparison population.
Reviewed periods are 2025 Q2/Q3/Q4 and 2026 Q2. No later quarter is inferred
available. Original files and generated reports remain outside Git.

## Reproducible checks and provenance

```bash
uv run --locked python -m platform_work_reform.enoe_variable_audit \
  artifacts/enoe-quarter-manifest.json > artifacts/enoe-variable-audit.json
```

The private manifest format and explicit reviewed local run IDs are documented
in [multi-quarter ingestion](enoe-multiquarter-ingestion.md). Each archive must
match its existing reviewed SHA-256 before and after the audit. The command
reruns the national preparation reconciliation and validates successful run,
period, layout and source-hash compatibility. It independently fingerprints the
selected logical fields, exact source keys and original row order in SDEM, COE1
and COE2 against staging in a read-only repeatable-read snapshot. Counts must
match the reviewed releases, and exact ordered headers must pass existing
contracts. The preparatory reconciliation runs in its own preceding read-only
snapshot; source agreement and national totals are checked again in the variable
audit. No source, staged record, database view or release selection is modified.

The fingerprint is SHA-256 over one compact ASCII JSON array per original row,
`[row_number, source_key_array, selected_value_array]`, followed by a newline.
`selected_value_array` uses module `BASE` then `FIELDS['SDEM']` for SDEM and
`FIELDS[table]` for questionnaires. Source whitespace is preserved in hashes.
Only selected code fields are decoded strictly as ASCII; source free text is
never decoded or emitted. Fingerprints do not verify unselected fields.

Each field's original bundled catalogue member, SHA-256 and number of keys
are retained in the report. The verified archive hash pins those bytes.
Catalogue keys are read literally, preserving leading zeros. The known 2025 Q2
`c_ocu11c` three-column serialization is accepted only through an explicit
parser branch. Its split code-1 description is joined for internal reading;
original bytes/hash remain unchanged. No catalogue is rewritten. Other ragged
rows and duplicate keys fail closed.

## Scope and states

The audit checks SDEM `c_ocu11c`, `rama`, `scian`, `pos_ocu`, `seg_soc`,
`medica5c`, `imssissste`, `emp_ppal`, `t_tra`; COE1 `p3`, `p4a` and the
supporting routing field `p4`; and COE2 `p6d`, `p7`.

The existing [15-plus universe](enoe-multiquarter-preparation.md) is retained,
including eligible age code 98, exclusion of 99, release-specific completed
interview code, residence rules and positive `fac_tri`. Within it, only occupied
people (`clase1=1`, `clase2=1`) enter field diagnostics. Source-key joins are
exact and questionnaire absence remains distinct from an empty answer. The
national source totals and questionnaire coverage must match preparation.

Every field partitions occupied rows into:

- `missing_questionnaire`: no matching COE record; never a substantive no.
- `blank_routing_unresolved`: matched record but empty after whitespace trim;
  the reason is not assigned from blankness alone.
- `coded_not_applicable`: released SDEM code `0`; never assumed equivalent to blank.
- `unspecified`: the field-specific released unknown/unspecified code.
- `insufficient_detail`: a valid `p4a` catalogue description explicitly stating
  insufficient specification below the general `9999` code. Such a code must
  not silently pass a detailed activity screen.
- `invalid_code`: nonblank code absent from that release's catalogue.
- `substantive_code`: other valid catalogue codes; validity does not establish
  platform work, applicability or detailed identification.

Rows and `fac_tri` totals are reported for each state. Each partition must sum
exactly to the occupied denominator. Observed valid-code counts are also kept;
invalid values themselves are not exposed. Code whitespace is trimmed for
classification but leading zeros are never removed. Hashes retain the original
logical values. The report diagnoses invalid codes rather than silently fixing
or excluding them; a downstream selection must explicitly reject unresolved
invalid states. Weight totals are descriptive, not confidence intervals.

Cross-tabs of `p6d`/`imssissste`, `p6d`/`seg_soc`, `p7`/`t_tra` and `p4` with
`p6d`/`p7` report rows and weighted totals. Non-substantive states remain explicit.
The report also compares medical-access cross-tabs against the reviewed 2023
reference rules described below, reporting compared, unresolved and mismatched
row counts and mismatched weights. A blank `p6d` can enter this reference check
as unspecified only when its observed correspondence with `p4=4` is exact.
Agreement is limited to those rules and fields, not a reconstruction of every
released precode. No automatic repair or interchangeability claim follows. All output excludes person identifiers, free text and design
stratum/UPM identifiers.

## Instrument routing and interpretation

The unchanged **Encuesta Nacional de Ocupación y Empleo (ENOE). Cuestionario de
Ocupación y Empleo (Básico)** copy in source-register S08 bears COE 2021 and
SHA-256 `81ecf71165eef4b8bb78d2848bc0e199eaa279e5a8869ee4794d5aee37eb9153`.
PDF pages 5, 8, 9 and 10 (printed 6, 9, 10 and 11) were rendered and visually
reviewed for this task:

- `p4=4` identifies work abroad and routes directly to 6e, bypassing 6d.
- Unpaid-work responses at 6/6a explicitly route to 6d. Missing earnings cannot
  be used to assign no medical access or to exclude all unpaid workers.
- Workplace branches at 6g/6i can route foreign work to section 8, bypassing 7.
- At 7, code 7 means no other work and 9 unknown. They are distinct from blank.

A new review found that the [2025 Q2/Q3/Q4 RNM materials](https://www.inegi.org.mx/rnm/index.php/catalog/1121/related-materials)
link [c_bas_v7.pdf](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/c_bas_v7.pdf),
whose cover identifies COE BÁSICO 2023, seventh version. Its reviewed unchanged
copy has SHA-256 `7ee25f114a493cd4136bb086f7fa3a2f6db1fe7300dc5839ec2a7de9c3efa698`.
The same PDF pages were rendered and visually reviewed; the selected medical
and foreign-work routes above agree with the older copy. The RNM record's title
says basic while a description says expanded; the linked PDF itself is basic.
Use its actual cover/version and preserve that metadata inconsistency. This
improves the period-specific instrument evidence for 2025; a 2026 Q2 instrument
link/version and complete respondent-path validation remain unresolved. The
2025 public-consultation proposal is not substituted for a deployed instrument.

The same RNM record links **Encuesta Nacional de Ocupación y Empleo (ENOE).
Reconstrucción de variables** (2023),
[official PDF](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/recons_var_15ymas.pdf).
The unchanged reviewed copy has SHA-256
`747b41847a82af8e6f43fd7b9453ee211c58cbe28017377f411f7e15b98831bf`.
Section 3.3 (PDF page 20, printed 5) and section 10.17 (PDF page 124, printed
109) were rendered and visually reviewed. The reference rules specify:

- `seg_soc`: access for `p6d=1..5`, no access for 6, unspecified for 9 or `p4=4`.
- The group labeled ISSSTE in section 10.17 uses **`p6d=2..4`**, including the
  naval/military/Pemex answer, alongside IMSS for 1, other institutions for 5,
  no care for 6 and unspecified for 9 or `p4=4`.

Thus interpreting released `imssissste=2` as exclusively the literal ISSSTE
answer `p6d=3` would be wrong for this documented grouping. The source label is
preserved; the audit does not rename or repair the released variable. It checks
observed agreement with these two reference rules in all reviewed quarters;
2026 agreement does not independently establish the applicable instrument
version. Full `medica5c`, `emp_ppal`, position and multiple-work reconstruction
are not claimed. The source-register supplement retains the three new originals
and hashes outside Git. Current blanks retain `blank_routing_unresolved` in
field states even where these aggregate routing checks are consistent.

`p6d` concerns medical care through the principal job. It does not establish
administrative IMSS registration, all insurance branches or previous coverage.
`emp_ppal` remains the released principal-job informality classification; its
algorithm is not reconstructed. `t_tra` and `p7` do not count apps or accounts.

## Candidate-screen feasibility and proposals

The archive catalogues support the following **proposals for review**, fixed
from source descriptions rather than fitted to IMSS totals. They are not
implemented population estimates or bounds on platform-worker prevalence.

| Proposal | Occupation/activity screen | What prevents platform identification |
|---|---|---|
| Narrow passenger-transport screen | `p3=8342` and `p4a=4850`, among eligible occupied people with substantive codes. | 8342 includes bus, van, taxi and car passenger drivers; 4850 covers land passenger transport beyond apps. No app relationship is observed. |
| Broad transport/delivery occupation screen | `p3` in 8341, 8342, 8344, 9321, 9722, 9723. Retain `p4a` as a separate dimension rather than require transport-sector coding. | Includes nonplatform freight, passenger transport and delivery. Deliverers may be classified in restaurants or commerce; activity-only restrictions can exclude them. Secondary platform work remains outside principal-job occupation. |

Exact catalogue descriptions include 8341 **Conductores de camiones, camionetas
y automóviles de carga**, 8342 **Conductores de autobuses, camiones, camionetas,
taxis y automóviles de pasajeros**, 8344 **Conductores de motocicleta**, 9321
**Conductores de vehículos de transporte en bicicleta**, 9722 **Repartidores de
mensajería (a pie o en bicicleta) y mandaderos**, and 9723 **Repartidores de
mercancías (a pie o en bicicleta)**. Code 4850 is **Transporte terrestre de
pasajeros, excepto por ferrocarril**; 4920 is **Servicios de mensajería y
paquetería**. This confirms broad occupational overlap, not a unique platform
signature. These proposed screens cover different transport/delivery scopes;
the broad screen's excess is not an estimate of misclassification.

Keep position (`pos_ocu`), medical access (`p6d`), released informality
(`emp_ppal`) and multiple-work indicators as separate descriptors. Neither
own-account status nor lack of medical access proves a platform relationship.
Do not use health access to select candidates whose coverage will subsequently
be evaluated. Unknown occupation/activity, absent questionnaire and secondary-job
limitations need their own exclusion counts in a future candidate implementation.
Income, deflation, legal thresholds, causal inference and survey precision remain
outside this audit. A complete common IMSS/ENOE time window is still unavailable
under the current selected releases.

## Empirical results and remaining gates (2026-11-09)

All three selected-table fingerprints matched source and staging for all four
quarters. National preparation counts and reference totals reconciled. No
out-of-catalogue code, coded-not-applicable SDEM value or absent COE1/COE2 was
observed among eligible occupied people in these 14 fields. This statement is
restricted to the audited fields and universe; it is not a general assertion
that the survey contains no missing or invalid data.

| Quarter | Occupied sample rows | Occupied `fac_tri` total | `p3` unspecified | `p4a` unspecified / insufficient detail | `p6d` blank / unknown |
|---|---:|---:|---:|---:|---:|
| 2025 Q2 | 190,687 | 59,440,760 | 251 | 265 / 242 | 556 / 1,249 |
| 2025 Q3 | 190,938 | 59,533,449 | 255 | 280 / 206 | 555 / 1,197 |
| 2025 Q4 | 190,187 | 59,785,854 | 236 | 270 / 242 | 543 / 1,188 |
| 2026 Q2 | 189,353 | 60,040,094 | 170 | 258 / 155 | 522 / 1,001 |

The field-state counts are unweighted; the occupied total column is weighted.
Occupation unspecified rates range from 0.090% to 0.134% of occupied sample
rows. Activity unspecified plus insufficient detail ranges from 0.218% to
0.269%; these valid catalogue categories still cannot identify a detailed
activity. Medical-answer blankness ranges from 0.276% to 0.292%, and unknown
responses from 0.529% to 0.655%. These are descriptive sample rates, with no
sampling-error or trend-significance claim. The full report contains weighted
state counts; no new cross-quarter population transition is inferred.

All `p6d` blanks correspond exactly to `p4=4` in each audited quarter. The
reference `seg_soc` and `imssissste` mappings have zero mismatched or unresolved
rows across the occupied samples. In particular, `p6d=2` maps to
`imssissste=2` for 991, 982, 930 and 964 rows respectively, as the official
reconstruction rule specifies. A naive label-based recode to other institutions
would create artificial discrepancies. This is a high-confidence, material
interpretation risk; use job-specific `p6d` or the documented grouping.

`p7` blank counts are 556, 555, 543 and 522, but equal counts do not prove equal
missingness patterns. In 2025 Q4, 542 blank `p7` rows have `p4=4`, while one has
`p4=1`; one foreign-work row therefore has a nonblank `p7`. The aggregate
routing evidence does not establish the full path or a source error. This is a
localized unresolved applicability finding: preserve the values and review
6e/6g/6i before implementing secondary-work exclusions. Never replace these
blanks with the no-other-work code. On substantive `p7` answers, observed
`t_tra` agrees with one job for `p7=7` and two for `p7=1..6`; this is empirical
consistency only, not a complete reconstruction for unknown/skip cases.

The fields are usable for explicitly qualified national descriptive screens,
with unknown and insufficient-detail exclusions retained. They are insufficient
by themselves to identify platform relationships. Before any candidate release,
review the proposed screens, decide the treatment of foreign/secondary work,
confirm the remaining 2026 instrument evidence and maintain issue #42 as the
precision gate. No IMSS-fit criterion, causal estimate or platform prevalence
has been produced.

The complete report is ignored at `artifacts/enoe-variable-audit.json`. The
companion [notebook](../notebooks/enoe-variable-validation.ipynb) provides the
same audited command and aggregate inspection; it is committed without outputs.
Validation: `just check` passed 117 unit tests and shared hooks; `just db-test`
passed 33 isolated integration tests, with one optional original-source test
skipped. Notebook schema and code syntax were validated separately. Actual
four-quarter audits are separate from the synthetic test evidence.
