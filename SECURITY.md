# Security Policy

## Reporting a vulnerability

Please don't report security problems in a public issue, pull request or
discussion. Use
[**Report a vulnerability**](https://github.com/sadayamuthu/ocbc/security/advisories/new)
on the repository's Security tab instead. Only the maintainer can see the
report.

Include what you can of:

- the output of `ocbc --version`, your Python version and your OS
- how OCBC was used: `ocbc fetch`, `ocbc generate` (with any overridden
  source URLs), the published catalog URL, or the GitHub Actions workflows
- steps to reproduce, ideally a command or a small script
- what happened and what you expected

You'll get a reply when the report has been read, and again when a fix is
ready. A fix to the package ships as a patch release on PyPI; a fix to the
published catalog ships in the next catalog release. The advisory names you
unless you'd rather it didn't.

## Supported versions

OCBC is pre-1.0. Fixes land in the latest PyPI release and the latest
published catalog only; please upgrade before reporting.

## What counts

OCBC downloads data over the network and publishes a catalog that other
tools use to decide which security controls apply. `ocbc fetch` downloads
the catalog from `https://openastra.org/ocbc/catalog/v0.1/latest.json`.
`ocbc generate` downloads nine OSCAL JSON files from
`raw.githubusercontent.com`, or from any URLs passed on the command line.
Both parse the JSON and write one output file. The
[`main-release.yml`](.github/workflows/main-release.yml) workflow
regenerates the catalog daily and pushes it to the `baseline-artifacts`
branch and to openastra.org with a deploy token. Anything that breaks one of
these promises is a security issue:

- **Downloads only read data.** A response from a source URL, or from the
  catalog URL, that makes OCBC run code, write anywhere other than the
  `--out` path, or reach a host other than the one requested is in scope.
- **The published catalog is what NIST and FedRAMP published.** A way to
  change the catalog at openastra.org, the `baseline-artifacts` branch or a
  GitHub release so that it no longer matches what the generator produces
  from the official sources is in scope. So is a way to change the schema
  published at openastra.org.
- **The workflows keep their secrets.** Script injection or a path that
  leaks the deploy token or the PyPI publishing identity, or lets someone
  other than the maintainer publish a package or a catalog, is in scope.
- **The package on PyPI is built from this repository.** A way to publish an
  `ocbc` release that doesn't come from a tag here is in scope.

`ocbc fetch` doesn't check a checksum or signature; it trusts HTTPS and the
host. Its integrity rests on the publishing pipeline above.

A wrong value in the catalog, such as a control flagged in the wrong
baseline, is a bug, not a vulnerability, unless someone changed it on
purpose. Report it in a normal issue; see
[CONTRIBUTING.md](CONTRIBUTING.md).
