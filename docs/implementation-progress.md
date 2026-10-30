# Implementation progress

| Stage | Evidence | Status |
|---|---|---|
| P01 | PR #6; just setup, just check and GitHub ci passed | Merged |
| P02 | PR #7; just check, just governance-check and branch-guard verification passed | Merged |
| P03 | PR #8; 11 unit tests; local connection and container-recreation persistence passed | Merged |
| P04 | PR #9; 11 unit and 4 isolated PostgreSQL tests; local migration passed | Merged |
| P05 | PR #10; backup restored and verified independently | Merged |
| P06 | PR #12; 45 local source files inventoried | Merged |
| P07 | PR #14; strict encoding inspection and normalization | Merged |
| P08 | PR #18; source layout contracts | Merged |
| P09 | PR #20; transactional staging and pilot | Merged |
| P10 | PR #22; reconciled monthly selection and analysis view | Merged |
| P11 | PR #26; resumable batch with storage guard | Merged |
| P12–P13 | 44 months staged, independently reconciled and selected; one exception | Partial |
| P14 | PR #31; reviewed ENOE 2025 Q3 source and join contract | Pilot merged |
| P15 | PR #33; transactional ENOE pilot loader and isolated real-data test | Pilot merged |
| P16 | Prepared 2025 Q3 person-quarter pilot and national point-estimate reconciliation; no survey-design precision | In progress |

Main protection was enabled before the first PR was merged. The ci check was
observed and made mandatory before merging PR #6.

PostgreSQL listens on loopback port 55432. On 2026-10-30 the active database
contained revision 0004 and the five ENOE pilot tables with the audited counts.
The private .env, persistent volume, and backup artifacts are excluded from Git.
A recovery validation database named
platform_work_reform_restore_initial_validation was restored successfully and
retained for inspection; it is not the active project database.

As of 2026-10-28, the selected IMSS view contains 44 monthly datasets and
199,395,921 aggregate rows from January 2023 through September 2026, excluding
January 2025. Each selected month has a passing source reconciliation and dataset
version record. Thirty-nine selected months use the legacy layout without `ptpd`;
five use the layout with `ptpd`. The local January 2025 file ends with an
incomplete row and remains unselected pending investigation in issue #27.

The active PostgreSQL volume is bound to the project data directory on /home;
the original root-filesystem volume was preserved. The 2026-10-29 backup was
independently stored and restored on 2026-10-30; see `backup-and-restore.md` for
the verified scope and remaining limitations. Shared
deployment and least-privilege analyst accounts remain P19. ENOE analytical
preparation and causal analysis remain subsequent work.
