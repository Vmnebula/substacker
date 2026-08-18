# Contributing to Substacker

Thanks for your interest in improving Substacker. This document covers how to set up a
development environment, what the project is looking for, and how changes get reviewed.

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Requires Python 3.10 or newer.

```bash
git clone https://github.com/YOUR_USERNAME/substacker.git
cd substacker

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov ruff

cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
```

Run the application with `uvicorn app:app --reload`. The default `DATABASE_TYPE=sqlite`
requires no external services.

## Before opening a pull request

```bash
pytest          # must pass
ruff check .    # must be clean
```

Both run in CI across Python 3.10 through 3.13, along with a check that the application
starts with the default configuration. A pull request that fails either will not be merged.

## What to work on

Useful contributions, roughly in order of impact:

- **Provider adapters.** Pricing and usage parsing for Mistral, Cohere, Bedrock,
  DeepSeek, and Ollama. `analyzer_v2.py` holds the pricing tables and
  `analyzer_multi_provider.py` holds provider detection.
- **Pricing accuracy.** Provider prices change often. Corrections with a link to the
  provider's public pricing page are always welcome.
- **Test coverage.** The suite is thin. Tests for the cost engine, waste detection, and
  the API surface are high value.
- **SDK clients.** Node.js, Go, or Rust ports of `substacker_sdk`.
- **Export and reporting.** Scheduled reports, Slack summaries, PDF or CSV exports.

If you are planning a large change, open an issue first so the approach can be agreed
before you write the code.

## Pull request guidelines

- Keep each pull request focused on one change.
- Write a descriptive branch name, for example `feat/bedrock-pricing` or
  `fix/decimal-rounding`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit subjects:
  `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- Update the README or `.env.example` when you change behaviour or configuration.
- Add a test for any bug you fix.

## Changing cost calculations

Cost arithmetic uses `Decimal` throughout to avoid drift when totals are aggregated.
Do not introduce `float` into the pricing path. Any change to a pricing table needs a
test asserting the resulting cost for a known token count.

## Reporting bugs and vulnerabilities

Open a [bug report](https://github.com/Vmnebula/substacker/issues/new/choose) for
functional problems. For anything security related, use private reporting as described
in [SECURITY.md](SECURITY.md) instead of a public issue.

Never include real API keys, tokens, or customer data in an issue, pull request, or
test fixture.

## License

By contributing, you agree that your contributions are licensed under the MIT License.
