# Contributing

Run `just setup` on every clone to install locked dependencies and Git hooks.
Run `just check` before committing or opening a PR. Hooks are local: Git does not
distribute installed hooks. The remote required `ci` check is authoritative.

## Issue and pull request workflow

Open an issue with objective, dependencies, inputs/outputs, acceptance criteria,
validation commands, and explicit exclusions. Branch from updated main, using
`feat/<issue>-<description>`, `fix/...`, or `chore/...`. Use conventional English
commit titles. Push only the feature branch and open a PR containing
`Closes #<issue>` and the checks actually run. Resolve review conversations before
squash merging. Do not bypass hooks, required checks, or protection.

GitHub permits squash merging only and deletes merged branches automatically.
Main requires a PR, the up-to-date `ci` check from GitHub Actions, linear history,
resolved conversations, and administrator enforcement. Force pushes and deletion
are disabled. No bypass identities are configured.

While there is one maintainer, zero external approvals are required: a maintainer
cannot supply an independent approval for their own PR. PRs and CI remain required.
When an independent reviewer becomes available, change the documented policy and
remote configuration together to require one approval. Do not enable a requirement
that can only be satisfied by bypassing it.

Run `just governance-check` to check remote settings. This read-only command needs
an authenticated `gh` client with permission to read branch protection. CI does
not receive administration credentials to inspect or modify governance.

## Validation

The commit-only branch guard prevents local commits on main. Shared hooks run at
the manual stage in both `just check` and GitHub Actions, including on main.
Pre-push hooks run the fast shared checks. Database integration checks are added
with the database behavior and run in an isolated PostgreSQL database.

Do not commit source data, credentials, notebook outputs, or backups. Small
synthetic fixtures belong in tests; they must not be presented as empirical data.
