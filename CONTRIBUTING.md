# Contributing to OCBC

Thanks for helping. OCBC is only useful if its catalog can be trusted, so
most of this guide is about keeping it accurate: every control in the output
must match what NIST and FedRAMP publish, and every change in behaviour comes
with a test that proves it.

- [Ways to help](#ways-to-help)
- [Reporting a wrong control mapping or enrichment](#reporting-a-wrong-control-mapping-or-enrichment)
- [Development setup](#development-setup)
- [Tests](#tests)
- [Code layout](#code-layout)
- [Schema versioning](#schema-versioning)
- [Pull requests](#pull-requests)
- [Security](#security)
- [License](#license)

## Ways to help

- **Report a wrong control mapping or enrichment.** This is the most useful
  contribution. See the next section.
- **Use the catalog** in your policy engine, dashboard or scanner and tell us
  what was missing or awkward, in an issue. Real-world use guides what to fix
  next.
- **Report a broken source URL.** The generator downloads OSCAL content from
  NIST and FedRAMP on every run. If an upstream file moves, `ocbc generate`
  fails until [`src/ocbc/urls.py`](src/ocbc/urls.py) is updated.
- **Pick up an open issue** on
  [GitHub](https://github.com/sadayamuthu/ocbc/issues).

For anything larger than a small fix, open an issue first so we can agree on
the approach before you write the code.

## Reporting a wrong control mapping or enrichment

A wrong mapping is, for example, a control flagged in a baseline it isn't
part of (or missing from one it is), a control linked to the wrong parent, a
missing or garbled `control_text`, or a `severity` or `non_negotiable` value
that doesn't follow the [rules in the README](README.md#severity-and-non-negotiable-rules).

Please include:

1. The `control_id`, for example `AC-2(1)`.
2. Where the catalog came from: the `generated_at_utc` and `project_version`
   fields of the file, and whether you used `ocbc fetch`, `ocbc generate` or
   the published URL.
3. The field that is wrong, its value, and the value you expected.
4. The source that shows the expected value: the NIST SP 800-53 Rev. 5
   catalog, the SP 800-53B baseline profile, or the FedRAMP baseline profile,
   with a link or the OSCAL ID.

If you ran `ocbc generate` with overridden URLs or
`--non_negotiable_min_baseline high`, say so, since both change the output.

## Development setup

You need **Python 3.11** or newer (CI tests 3.11, 3.12 and 3.13), `make` and
`git`. The generator needs network access to `raw.githubusercontent.com`;
the tests don't, because every download is mocked.

```sh
git clone https://github.com/sadayamuthu/ocbc.git
cd ocbc
python3 -m venv .venv && source .venv/bin/activate
make install-dev          # pip install -e ".[dev]" and pre-commit install
ocbc --version
```

Before pushing, run what CI runs. The `Develop CI` workflow
([`develop.yml`](.github/workflows/develop.yml)) runs `make install-dev` and
then `make check` on Python 3.11, 3.12 and 3.13 for every pull request to
`develop` or `main`:

```sh
make check                # make lint + make test-cov
```

which is:

```sh
python3 -m ruff check src/ tests/
python3 -m pytest tests/ -v --cov=ocbc --cov-report=term-missing --cov-report=html --cov-fail-under=100
```

CI doesn't check formatting, but the pre-commit hook does (`ruff --fix`,
`ruff-format` and `pytest`). Run `make format` to apply it by hand.

To generate a catalog locally:

```sh
ocbc generate --out baseline/ocbc_full_catalog_enriched.json
```

Don't commit regenerated files under `baseline/`. The
[`main-release.yml`](.github/workflows/main-release.yml) workflow regenerates
and publishes the catalog itself.

## Tests

The suite lives in [`tests/`](tests) and must keep **100% line coverage**;
`make test-cov` fails below that.

| File | What it covers |
|------|----------------|
| `tests/test_oscal_id.py` | OSCAL ID to control ID conversion (`ac-2.1` to `AC-2(1)`) |
| `tests/test_generate.py` | Catalog and profile parsing, baseline flags, severity and non-negotiable rules, the generator end to end with mocked downloads |
| `tests/test_fetch.py` | `ocbc fetch` with a mocked HTTP response |
| `tests/test_cli.py` | The `ocbc` command, its subcommands and `--version` |
| `tests/test_schema_validation.py` | `spec/schemas/ocbc-v0.1.json` accepts a valid catalog and rejects a missing field, a bad severity and an extra field |

Run one test while you work on it:

```sh
python3 -m pytest tests/test_generate.py -k severity -v
```

**Every behaviour change needs a test.** For a wrong mapping, add a test with
a small OSCAL fragment that fails before your change and passes after it.

## Code layout

| Path | What it does |
|------|--------------|
| `src/ocbc/cli.py` | CLI entry point: `ocbc fetch`, `ocbc generate`, `--version` |
| `src/ocbc/fetch.py` | Downloads the published catalog from openastra.org |
| `src/ocbc/generate.py` | Downloads the OSCAL sources, parses the catalog and profiles, adds baseline flags, severity and non-negotiable, writes the JSON |
| `src/ocbc/urls.py` | Default NIST and FedRAMP OSCAL source URLs |
| `src/ocbc/__init__.py` | `__version__`, read from the installed package metadata |
| `spec/VERSION` | Schema version |
| `spec/schemas/` | JSON Schema and YAML equivalent for the catalog output |
| `baseline/` | Generated catalog and timestamped historical copies |
| `.github/workflows/` | CI, the daily release, the schema release and PyPI publishing |

## Schema versioning

There are two versions, and they move independently:

- **The package version** is `version` in [`pyproject.toml`](pyproject.toml).
  It appears as `project_version` in the catalog and in `ocbc --version`.
  Pushing a `v*.*.*` tag publishes the package to PyPI
  ([`pypi-publish.yml`](.github/workflows/pypi-publish.yml)).
- **The schema version** is [`spec/VERSION`](spec/VERSION), in
  `MAJOR.MINOR.PATCH` form. `MAJOR.MINOR` is the URL path the catalog and
  schema are published under (`v0.1`). Bump it only when the structure of the
  catalog output changes.

Any change under `spec/` that reaches `main` triggers
[`schema-release.yml`](.github/workflows/schema-release.yml), which fails if
the tag `spec-v{VERSION}` already exists. So every change to the schema files
needs a new `spec/VERSION`:

- **Patch** (`0.1.0` to `0.1.1`): a fix to the schema files that doesn't
  change the output, such as a description. Same URL path.
- **Minor or major** (`0.1.x` to `0.2.0`): the output structure changes.
  Rename the files in `spec/schemas/` to `ocbc-v{MAJOR.MINOR}.json` and
  `.yaml` and update `SCHEMA_PATH` in `tests/test_schema_validation.py`.
  Keep only one version of each file in `spec/schemas/`, because the release
  workflow copies `ocbc-v*.json` to a single destination file. The catalog
  then publishes under the new path, and the old path stops being updated.

Change the generator, the schema and the README's Output Schema section in
the same pull request.

## Pull requests

- Keep each PR to one change; small PRs get reviewed faster.
- Open it against `develop` or `main`; both run `Develop CI`.
- Use the commit message style in the history: `type: summary`, for example
  `fix: push baseline-artifacts from detached HEAD explicitly`. Types in use:
  `feat`, `fix`, `docs`, `chore`.
- CI must pass on Python 3.11, 3.12 and 3.13.
- Update README.md when you change behaviour a user can see, such as a CLI
  flag, an output field or a rule.

## Security

Please don't report security problems in a public issue. Use
[**Report a vulnerability**](https://github.com/sadayamuthu/ocbc/security/advisories/new)
on the repository's Security tab instead. See [SECURITY.md](SECURITY.md) for
what to include and what's in scope.

## License

OCBC's code is licensed under the [MIT License](LICENSE). By contributing,
you agree that your contributions are licensed under the same license.

The control content in the catalog comes from NIST SP 800-53 Rev. 5 and
SP 800-53B, which are U.S. Government works in the public domain, and from
the FedRAMP baselines published by GSA.
