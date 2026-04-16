# Release Workflow (MDI policy)

## Version source

- Python packages: `pyproject.toml` (`[project].version`)
- Non-package repos: `VERSION`

## Commands

```bash
make release-check
make release-bump-patch
# or make release-bump-minor / make release-bump-major
```

After merge to `main`:

```bash
make release-tag
# then push tags explicitly
# git push origin main --tags
```

## Release branch policy

- Keep release preparation local until the candidate is ready for public review.
- If a public-facing review branch is needed, use a temporary branch named
  `release-vX.Y.Z-review`.
- Merge to `main` before creating and pushing tag `vX.Y.Z`.

## Changelog policy

- Keep `## [Unreleased]` at top.
- Add release section `## [X.Y.Z] - YYYY-MM-DD` for each release.
- Maintain concise entries grouped under Added/Changed/Fixed.

## Release-check expectations

- `make release-check` is an authoritative pre-release readiness check.
- It requires a git repository with an `origin` remote.
- It checks the current version tag directly against `origin` before
  evaluating whether that version is already published.
- It should pass when the current version is untagged, or when the current
  commit is already the tagged release commit for that version.
- It should fail when the current version tag already exists on a different
  commit; in that case, bump the version before preparing the next release.
