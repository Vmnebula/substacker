# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-18

First tagged release. Establishes a baseline for the existing codebase.

### Added

- Continuous integration running lint and the test suite on Python 3.10 through 3.13,
  plus a check that the application starts with the default configuration.
- CodeQL scanning and Dependabot updates for pip and GitHub Actions.
- Security policy, code of conduct, issue templates, and a pull request template.
- Ruff configuration and a project `pyproject.toml`.

### Changed

- `DATABASE_TYPE` now selects the storage backend as documented. The application
  previously required Supabase regardless of the setting; `sqlite` is the default and
  needs no configuration.
- The Python SDK reports usage from a background worker instead of blocking the calling
  thread, and logs failures through the `logging` module rather than printing them.
- The SDK is packaged with `pyproject.toml` and now installs a working, importable
  module. The previous `setup.py` produced an empty distribution.
- Documentation rewritten to describe the API that actually exists.

### Removed

- `docs/assets/demo.gif` and its history. The 12 MB file accounted for almost all of
  the repository size and was downloaded on every clone. It is now attached to the
  release and referenced from the README by URL.

### Fixed

- Two route handlers shared the name `realtime_dashboard`, making the first
  unreachable by name. The page handler is now `realtime_dashboard_page`.
- Removed dead assignments and unused imports across the analyzer and application
  modules; replaced bare `except:` clauses in the SDK.
- Replaced deprecated `datetime.utcnow()` with a timezone-aware equivalent.

[Unreleased]: https://github.com/Vmnebula/substacker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Vmnebula/substacker/releases/tag/v0.1.0
