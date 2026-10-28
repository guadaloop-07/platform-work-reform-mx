# platform-work-reform-mx
Reproducible analysis of Mexico’s 2025 digital platform labor reform, using IMSS
administrative records and ENOE survey data to study earnings, employment, and
social security coverage.

## Development

Install uv and just, then run:

```bash
just setup
just check
```

Python 3.12 and development dependencies are recorded in `.python-version` and
`uv.lock`. Run `just setup` for every clone to install local Git hooks. Manual
checks and CI share the same pre-commit configuration; the local branch guard
only runs when committing.

Use an issue-linked branch and a pull request for every change. Keep credentials,
source microdata, database volumes, backups, and generated outputs outside Git.
Infrastructure is being introduced incrementally; no empirical results exist yet.

See [contribution rules](CONTRIBUTING.md), the
[implementation roadmap](docs/implementation-plan.md), and
[implementation progress](docs/implementation-progress.md).

Follow the [local database guide](docs/local-database.md) to configure the isolated
PostgreSQL service. Never reuse another project's credentials or database.
