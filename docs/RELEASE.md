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

## Changelog policy

- Keep `## [Unreleased]` at top.
- Add release section `## [X.Y.Z] - YYYY-MM-DD` for each release.
- Maintain concise entries grouped under Added/Changed/Fixed.
