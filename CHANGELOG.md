# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- Resolved fourteen advisories reported against pinned dependencies. `jinja2` was
  pinned at 3.1.2, which carries two sandbox escapes, a sandbox breakout via malicious
  filenames, and HTML attribute injection through the `xmlattr` filter; the floor is
  now 3.1.6. `python-multipart` was pinned at 0.0.6, which carries an arbitrary file
  write plus several denial-of-service and parameter-smuggling issues; the floor is
  now 0.0.32.
- Requirements moved from exact `==` pins to minimum bounds. The exact pins are why
  these went unpatched: a pinned dependency never receives a security update until
  someone edits the file.

### Changed

- `templates.TemplateResponse(name, context)` migrated to the current
  `TemplateResponse(request, name, context)` signature across all ten call sites.
  Starlette removed the legacy argument order, and on the upgraded stack every
  server-rendered page raised `TypeError: unhashable type: 'dict'` at request time.
- `requirements-dev.txt` added for test and lint tooling.

### Added

- HTTP-level tests covering every server-rendered page, the authenticated routes, the
  multipart upload path, and the OpenAPI schema. The template regression above passed
  the entire unit suite and imported cleanly, so only a real request could catch it.

## [0.1.0] - 2026-08-18

First tagged release. Establishes a baseline for the existing codebase.

### Added

- A pricing test suite covering model normalisation, provider detection, cost
  arithmetic against known token counts, and a guard that every model in the shipped
  sample data has a price. The suite went from 4 tests to 48.
- `docs/README.md` explaining where pricing lives and how to add a provider.
- `.editorconfig`.
- Continuous integration running lint and the test suite on Python 3.10 through 3.13,
  plus a check that the application starts with the default configuration.
- CodeQL scanning and Dependabot updates for pip and GitHub Actions.
- Security policy, code of conduct, issue templates, and a pull request template.
- Ruff configuration and a project `pyproject.toml`.

### Changed

- Pricing data refreshed against provider pricing pages on 2026-08-18. The table
  previously stopped at GPT-4, Claude 3, and Gemini 1.5, and had no entry at all for
  `gpt-4o` or any reasoning model. It now covers the GPT-5, Claude 5, and Gemini 3
  families, the `o`-series, and current Azure deployments, and retains retired models
  so historical exports still price correctly. The docstring records the verification
  date and links each provider's pricing page.
- `analyzer_v2.py` renamed to `cost_analyzer.py` and `OpenAIWasteAnalyzer` renamed to
  `CostAnalyzer`, since the class covers four providers and does more than waste
  analysis. `OpenAIWasteAnalyzer` remains as an alias.
- Sample data and the downloadable CSV template now use current model names, so a new
  user's first analysis produces real costs rather than zeros.
- `DATABASE_TYPE` now selects the storage backend as documented. The application
  previously required Supabase regardless of the setting, so a fresh clone could not
  start. When the variable is unset the backend is inferred: Supabase if its
  credentials are present, SQLite otherwise. That keeps existing deployments that never
  set the variable on Supabase, while a fresh clone still runs with no configuration.
- The Python SDK reports usage from a background worker instead of blocking the calling
  thread, and logs failures through the `logging` module rather than printing them.
- The SDK is packaged with `pyproject.toml` and now installs a working, importable
  module. The previous `setup.py` produced an empty distribution.
- Documentation rewritten to describe the API that actually exists.

### Removed

- `analyzer.py`, 574 lines of unreachable code. Nothing imported it, it declared a
  second class also named `OpenAIWasteAnalyzer`, it kept a duplicate pricing table in
  floats rather than `Decimal`, and it silently priced unknown models as
  `gpt-3.5-turbo` instead of flagging them.
- `docs/architecture/NETWORK_DIAGRAM.txt`, a record of debugging an SMTP problem that
  named the hosting provider, region, and firewall behaviour of the production
  deployment. It documented an incident, not the architecture.
- `docs/architecture/ARCHITECTURE_SKETCHES.txt`, ASCII diagrams headed "for Google
  Fellowship Application" and superseded by the diagram in the README.
- Unreferenced scratch files from `sample_data/` (`test.csv`, `test1.csv`, `test2.csv`,
  `test3.csv`, and a `sample_usage.csv` containing an unrelated stationery order).
- `docs/assets/demo.gif` and its history. The 12 MB file accounted for almost all of
  the repository size and was downloaded on every clone. It is now attached to the
  release and referenced from the README by URL.

### Fixed

- `gpt-4o` was billed at the `gpt-4` rate, twelve times its real input price. Model
  matching compared substrings against a hardcoded list, so `gpt-4o` matched `gpt-4`
  and was reported as a recognised model. Matching is now derived from the pricing
  table and tries the longest key first. A regression test pins both prices.
- Reasoning models (`o1`, `o3`, `o4-mini`) were attributed to no provider at all,
  because provider detection only looked for a `gpt` prefix.
- Two route handlers shared the name `realtime_dashboard`, making the first
  unreachable by name. The page handler is now `realtime_dashboard_page`.
- Removed dead assignments and unused imports across the analyzer and application
  modules; replaced bare `except:` clauses in the SDK.
- Replaced deprecated `datetime.utcnow()` with a timezone-aware equivalent.

[Unreleased]: https://github.com/Vmnebula/substacker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Vmnebula/substacker/releases/tag/v0.1.0
