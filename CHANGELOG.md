# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

No entries yet.

## [0.2.1] - 2026-04-16

### Added
- Added README scope note that the public v0.1 plugin id remains `mdipplcloud` and private pilot ids stay out of public docs until finalized.
- Added plugin test assertions for required metadata fields (`api_version`, `id`, `publisher`) and resultbundle producer/time-reference keys.
- Added helpers tests for config loading, cwd fallback, and recordings/projects URL builders.
- Added helper coverage that verifies wrapping quotes are stripped from config values for backward compatibility with older copied templates.

### Changed
- Clarified plugin contract notes in README to explicitly call out required `meta` fields used by `mdivicomtools` integration.
- Moved `upstream_tool` to top-level in `resultbundle.json` so contract resolvers/validators can read it consistently.
- Updated `config_template.ini` placeholders to use unquoted values so copied configs work in the standalone public path.
- Clarified `docs/RELEASE.md` so `release-check` is treated as an authoritative gate that checks tags directly against `origin`, and so the release flow follows `local/dev -> local/release-staging -> main`.

### Fixed
- Hardened `release-check` so it fails when the current version tag already exists on a different commit and so it no longer trusts only stale local tag refs.

## [0.2.0] - 2026-02-11

### Added
- Added mdivicom plugin contract v0.1 metadata shape (`meta` + `entry.callable`) in `mdipplcloud.plugin:get_plugin`.
- Added plugin output sidecar `resultbundle.json` with minimal v0.1 envelope fields for cross-plugin handoff.
- Added `dry_run`/`work_dir` coverage and contract-shape assertions in plugin tests.
- Added release tooling and workflow docs (`scripts/release/*`, `docs/RELEASE.md`).

### Changed
- Changed plugin execution entry to `run(dataset_dir, out_dir, config, *, work_dir=None, dry_run=False)` with compatibility fallback for `plugin_out_dir`.
- Changed plugin provenance/result payloads to include plugin-scoped output paths and config hash.
- Normalized package versioning to SemVer (`0.2.0`).
- Updated README installation guidance to reflect standalone/plugin-first usage and removed submodule-oriented wording.
- Corrected the plugin-run config example to use the `/v2` Pupil Cloud API base URL.

### Fixed
- Constrained setuptools package discovery to `mdipplcloud*` so editable installs work in cross-repo smoke tests.
- Allowed release checks to warn (not fail) when `AGENTS.md` is absent on release branches.
- Updated `pyproject.toml` license metadata to table form for broader PEP 621/toolchain compatibility.
- Switched project enrichment listing to shared `_request(...)` path for consistent timeout/retry behavior and removed unused locals in `download_enrichment`.
- Hardened `scripts/release/tag_release.sh` to require `main` aligned with `origin/main` before tagging.

## [0.1.0] - 2025-04-10

### Added
- Initial public package for interacting with Pupil Labs Cloud API v2.
- Core download/list helpers for workspace/project/recording resources.
- Early README usage examples and pyproject-based packaging baseline.

### Changed
- Iterative README improvements and packaging migration from `setup.py` to `pyproject.toml`.

### Fixed
- Early reliability and structure refinements prior to plugin-contract hardening.
