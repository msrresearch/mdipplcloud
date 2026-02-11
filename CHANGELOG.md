# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added
- Added mdivicom plugin contract v0.1 metadata shape (`meta` + `entry.callable`) in `mdipplcloud.plugin:get_plugin`.
- Added plugin output sidecar `resultbundle.json` with minimal v0.1 envelope fields for cross-plugin handoff.
- Added `dry_run`/`work_dir` coverage and contract-shape assertions in plugin tests.

### Changed
- Changed plugin execution entry to `run(dataset_dir, out_dir, config, *, work_dir=None, dry_run=False)` with compatibility fallback for `plugin_out_dir`.
- Changed plugin provenance/result payloads to include plugin-scoped output paths and config hash.
- Changed README to include mdivicom plugin usage (`plugins list/info/run`) and contract-facing output notes.

### Fixed
- Updated task workflow tracking (`planning/tasks.*`) to reflect completed README alignment and active contract-alignment work.
- Constrained setuptools package discovery to `mdipplcloud*` and normalized versioning to `0.2.0` so editable installs work in cross-repo smoke tests.
