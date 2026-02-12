# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

- No entries yet.

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

### Fixed
- Constrained setuptools package discovery to `mdipplcloud*` so editable installs work in cross-repo smoke tests.
- Allowed release checks to warn (not fail) when `AGENTS.md` is absent on release branches.

## [0.1.0] - 2025-04-10

### Added
- Initial public package for interacting with Pupil Labs Cloud API v2.
- Core download/list helpers for workspace/project/recording resources.
- Early README usage examples and pyproject-based packaging baseline.

### Changed
- Iterative README improvements and packaging migration from `setup.py` to `pyproject.toml`.

### Fixed
- Early reliability and structure refinements prior to plugin-contract hardening.
