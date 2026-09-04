# Changelog

All notable changes are documented here.

## 0.1.2 - 2026-09-05

- Publish the package on PyPI for one-command installation.
- Add a verified three-change demo and repository social preview.

## 0.1.1 - 2026-09-04

- Add `--live` reports for long-running interactive agent sessions.
- Mark reports as `running` or `completed` and write them atomically.
- Exclude live report files from their own filesystem diff.
- Document `codex exec` for one report per task.

## 0.1.0 - 2026-09-04

- Initial local command wrapper with before/after filesystem snapshots.
- Detect tracked, untracked, ignored, mode, and symlink-target changes.
- Add Markdown and JSON reports, exclusions, diagnostics, and `--fail-on-change`.
