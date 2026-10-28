# Incremental implementation roadmap

One issue and normally one PR per stage. All work uses the workflow in
CONTRIBUTING.md. Infrastructure is independent of the job-quality-enoe project;
no external project database or credentials may be reused accidentally.

| Stage | Deliverable | Dependency |
|---|---|---|
| P01 | Locked Python tooling, hooks, CI and initial protection (#1) | None |
| P02 | Governance, templates and remote configuration verification (#2) | P01 |
| P03 | Local PostgreSQL service and validated configuration (#3) | P02 |
| P04 | Migrations and ingestion metadata (#4) | P03 |
| P05 | Verified independent backup and restore (#5) | P04 |
| P06 | Local source inventory and hashes | P04 |
| P07 | Strict encoding validation and incremental normalization | P06 |
| P08 | Versioned IMSS source contracts | P07 |
| P09 | Incremental IMSS staging load | P08 |
| P10 | Transactional versioned IMSS publication | P09 |
| P11 | Interrupted-run recovery and status | P10 |
| P12 | End-to-end IMSS pilot and resource measurement | P05, P11 |
| P13 | Agreed IMSS historical batches | P12 |
| P14 | ENOE source and join contracts | P12 |
| P15 | Official ENOE source ingestion | P14 |
| P16 | Validated person-quarter preparation | P15 |
| P17 | INPC, policy calendar and documented crosswalks | P12 |
| P18 | Platform-worker identification feasibility | P16, P17 |
| P19 | Shared instance and individually assigned roles | P05; may be advanced |
| P20 | Optional official-source downloader | P12 |

PostgreSQL is the canonical validated store. Original files remain unchanged on
external storage, with hashes and provenance recorded. Python validates encoding
and CSV contracts before COPY ingestion. Missing historical ptpd is not silently
zero-filled. Dataset releases select explicit versions, avoiding double counting.

Each issue must specify objective, dependencies, input/output contracts, expected
files, acceptance criteria, commands, and exclusions. Tests use small synthetic
fixtures; CI never downloads or uploads survey microdata. Real-data operational
reports contain only reviewed aggregates and provenance safe to publish.

No causal estimator is selected until P18 establishes a defensible population and
comparison design. IMSS cells are aggregates, not person-level linkage records.
