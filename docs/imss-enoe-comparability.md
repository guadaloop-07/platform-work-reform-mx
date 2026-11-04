# P18: IMSS–ENOE population comparability and identification feasibility

## Research objective

Assess whether independently defined ENOE populations potentially engaged in
platform work are comparable, in observable dimensions, with platform employment
registered in IMSS. Establish what the available sources can support about the
size, composition and social-security coverage of this population, and what
additional evidence is needed to study prior informality and formalization.

This is a measurement and feasibility stage. It does not identify individual
IMSS–ENOE matches, establish that new registrations were previously informal,
or attribute changes causally to the reform. Employer concentration is outside
this objective. P18 remains pending until the empirical assessment is reviewed.

## Methodological precedent

Colonna and Aldeco Leo (2025), *Outsourcing, Labor Regulations and Profit-Sharing:
Evidence from Mexico*, [Appendix B.1, printed pages 81–83](https://www.banxico.org.mx/publications-and-press/banco-de-mexico-working-papers/%7BA551AF0E-CE4A-B0D3-D9CD-C2197A36509E%7D.pdf),
compare independently constructed IMSS and EMIM samples using coverage
restrictions and group-level employment and wage diagnostics. This motivates
our harmonization strategy; their confidential employer–employee data and
establishment survey do not establish equivalent identification capabilities
for public IMSS aggregates and ENOE household records. Similar aggregate
profiles are evidence of compatibility, not proof of population identity.

## Current evidence and dependencies

- IMSS has 44 selected, reconciled months from January 2023 through September
  2026, excluding January 2025 (issue #27). Only May–September 2026 selected
  local releases contain `ptpd`. An absent field is not zero platform work.
- ENOE has one prepared 2025 Q3 pilot. National activity point estimates have
  been reconciled, but this does not validate platform classification,
  informality, earnings, social-security variables or survey precision.
- Issue #42 must establish supported survey-design variance and domain handling.
  Small population estimates require uncertainty diagnostics, not just weights.
- P17 must supply a versioned policy calendar, applicable definitions and
  documented classification and price crosswalks where needed.
- There is currently no prepared overlapping period between ENOE and selected
  IMSS releases containing `ptpd`. Verify official historical IMSS alternatives
  or prepare an available compatible ENOE quarter under a separate scoped task.

See [progress](implementation-progress.md), [IMSS inventory](imss-inventory.md),
[IMSS count definitions](imss-metric-definitions.md), and
[ENOE pilot reconciliation](enoe-national-pilot-indicators.md).

## Required comparison contract

Before computing comparisons, record the following for each source and release:

| Element | Required decision and evidence |
|---|---|
| Provenance | Source title, version, hash, selected dataset/run, reference period and applicable dictionary. |
| Population | Inclusion/exclusion rules, age, residence, employment status, platform indicator meaning and coverage category. |
| Observation unit | IMSS affiliated jobs (`ta`) versus ENOE persons and reported jobs; document multiple platforms, other employment and unobserved multiplicity. |
| Timing | Monthly stock versus quarterly survey reference; justify alignment and inspect within-quarter variation. Never sum monthly stocks as unique persons. |
| Geography | Establish what location each source measures; compare only compatible supported domains. No municipal representativeness inference. |
| Classification | Versioned occupation/activity crosswalk and questionnaire evidence. Occupation or industry alone does not establish platform work. |
| Coverage and informality | Distinguish registration, benefit coverage, access through the relevant job or another job, and the applicable ENOE informality definition. |
| Earnings | Distinguish reported labor income from IMSS registered salary; document jobs covered, reporting period, units, deflation and missing income. |
| Precision | ENOE design, weights, domain estimator, standard errors, CV, intervals and unsupported-cell rules. Administrative counts have different coverage errors. |

Each rule must identify exact original variables and codes, authoritative
period-specific documentation, missing/unknown handling and an auditable
implementation. Do not silently impute missing classifications or income as
zero. Report exclusions and unresolved observations separately. Any chosen
monthly-to-quarterly aggregation must state its estimand; a quarterly mean of
monthly stocks is not a quarterly count of unique workers.

## Candidate ENOE populations

Define substantively justified narrow and broad candidate populations before
examining their fit to IMSS. Inspect questionnaire responses, occupation,
activity, employment position and primary/secondary job coverage, as available.
Document false-inclusion and false-exclusion risks and code-version differences.
If the questionnaire cannot distinguish a platform relationship, label the
population as potentially platform-related, not identified platform workers.

Candidates are sensitivity scenarios, not formal lower/upper bounds unless
containment assumptions are independently justified. Do not choose a candidate
solely because its total, profile or correlation most closely matches IMSS.
Freeze rule versions before evaluating agreement; later revisions must record
new substantive evidence and retain prior results for comparison.

## Empirical outputs and interpretation

Produce a source-backed aggregate assessment containing:

1. A population flow table with weighted/unweighted ENOE counts, exclusions,
   missingness, source versions and supported uncertainty measures.
2. A compatibility matrix identifying which characteristics can actually be
   compared. Do not assume occupation is observed in IMSS or that geographic
   and earnings concepts coincide.
3. For supported common groups, totals, shares, absolute gaps and ratios;
   scatterplots against equality and correlations are complementary diagnostics.
   High correlation alone does not establish agreement in levels.
4. Sensitivity to candidate population, period alignment, multiplicity
   assumptions and missingness. Distinguish observed results from assumptions;
   do not invent multiplicity corrections without external evidence.
5. A decision record stating supported uses, unresolved differences, data-access
   needs and whether a descriptive paper or subsequent transition study is viable.

Assess precision and disclosure risk before publishing small cells. Incompatible
concepts must be reported as such rather than forced into a common statistic.
Do not set numerical agreement thresholds after observing results. Record any
pre-specified operational thresholds and their substantive justification in the
implementation issue; no universal correlation cutoff establishes comparability.

## Implementation sequence and completion gates

| Task | Deliverable | Gate |
|---|---|---|
| Complete P16 precision (#42) | Validated design estimator and domain handling | Independent precision validation passes. |
| Establish common-period feasibility | Versioned source availability and field audit | At least one defensible common period, or an explicit no-go finding. |
| Extend analytical contracts in P16/P17 | Reviewed variables, universes, policy definitions and crosswalks | Rules supported by period-specific sources; ambiguous concepts remain explicit. |
| Implement P18 candidates | Versioned transformations and meaningful synthetic behavior tests | Rules justified independently of IMSS fit; missingness retained. |
| Run P18 comparison pilot | Reproducible aggregate diagnostics and sensitivity assessment | Units, timing and domains supported; uncertainty validated. |
| Review P18 conclusion | Evidence-based feasibility decision | Limitations, unsupported claims and next tasks documented. |

Each implementation task requires its own scoped issue and PR, with inputs,
outputs, acceptance criteria and actual validation evidence. Documentation and
read-only source feasibility research can proceed before all numerical gates
pass. No estimates or platform labels are authorized by this contract alone.

A negative feasibility result is a valid P18 outcome: specify what cannot be
identified and which additional source would resolve it. Do not manufacture
comparability to satisfy a publication objective.

## Subsequent research boundary

Prior informality requires separate evidence. Repeated cross-sections can show
changes in population composition, not establish individual transitions. A
longitudinal ENOE extension requires separately validated cross-quarter identity,
attrition, weights, precision and job-specific status changes; even that does
not create an individual match to IMSS. Causal effects and estimator selection
require a subsequent scoped design supported by the P18 findings.
