# Repository instructions

Write repository files, comments, commits, issues, and PRs in English. Preserve
original survey variable names and exact source titles.

## Code discovery

Prefer codebase-memory-mcp over grep/glob for code discovery. Index this repository
when needed, then use search_graph, trace_path, get_code_snippet, or query_graph.
Use text search for documentation, configuration, literals, or insufficient graph
results. Never commit the local graph cache.

## Git workflow

1. Inspect instructions and the working tree; preserve unrelated changes.
2. Open or identify the scoped issue before editing project files.
3. Create an issue-linked branch from current main.
4. Implement only that issue and run just check plus relevant integration checks.
5. Commit with a conventional English title, push the branch, and open a PR with
   Closes #<issue> and actual validation evidence.
6. Squash merge only within the user's authorized scope, with required checks
   passing and review threads resolved. Never use an administrator override.

Never push directly to main, skip hooks, weaken protection, or bypass failing
checks. Follow the single-maintainer review policy in CONTRIBUTING.md.

## Implementation and data

Use Python 3.12 and uv; commit dependency updates with uv.lock. Prefer focused
modules and explicit contracts so each roadmap stage can be implemented alone.
Use meaningful tests for behavior changes; do not add placeholder tests.

Keep original source files, microdata, credentials, backups, and generated outputs
outside Git. Preserve original bytes and record source versions and hashes. Treat
encoding detection as evidence, not certainty; never silently replace characters.
Document universes, missing-value rules, weights, and source definitions. Do not
infer municipal representativeness or individual IMSS–ENOE linkage from identifiers.

The approved initial scope is P01–P05 in docs/implementation-plan.md. Subsequent
data ingestion and analytical stages require their own scoped tasks.
