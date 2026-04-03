# Releasing

This project uses two different workflows for ordinary development and releases.

## Ordinary Pull Requests

Normal pull requests do not need to update `pyproject.toml` or `CHANGELOG.md`.

Examples:

- documentation-only changes
- CI or tooling changes
- code changes that are not being released yet

## Release Pull Requests

Use a dedicated branch named `release/X.Y.Z` when you want to prepare a PyPI
release.

That release PR must:

- bump `[project].version` in `pyproject.toml` to `X.Y.Z`
- update the top entry in `CHANGELOG.md` to `X.Y.Z`

The CI workflow checks this metadata only for `release/*` pull requests.

## Publishing

After the release PR is merged to `main`:

1. Create a GitHub Release with tag `X.Y.Z`.
2. The publish workflow validates:
   - the tag format is `X.Y.Z`
   - the tag matches `pyproject.toml`
   - the top changelog version matches `pyproject.toml`
   - the tagged commit is reachable from `main`
3. If the checks pass, GitHub publishes the package to PyPI through Trusted
   Publishing.
