# Documentation

Project documentation lives here. The [README](../README.md) is the entry point and
covers installation, configuration, and the HTTP API.

| Path | Contents |
| --- | --- |
| [`architecture/USER_FLOW.md`](architecture/USER_FLOW.md) | Product walkthrough of the dashboard flows. Written 2025-11-01 and not revised since, so treat it as intent rather than a description of current behaviour. |
| `assets/` | Diagrams referenced from the documentation. |

## Where pricing comes from

Model prices live in `cost_analyzer.py`, in `CostAnalyzer._initialize_pricing`. The
docstring there records the date the table was verified and links to each provider's
pricing page. When you update a price, update that date too and add a test in
`tests/test_pricing.py` asserting the resulting cost for a known token count.

Prices are stored per 1,000 tokens as `Decimal`, while providers publish per 1,000,000.
Divide by 1,000 when transcribing.

## Adding a provider

1. Add an entry to the `Provider` enum in `cost_analyzer.py`.
2. Add the models and prices to `_initialize_pricing`.
3. Extend `_detect_provider` so the provider's naming convention is recognised.
4. Add cases to `NORMALISATION_CASES` in `tests/test_pricing.py`.

Model matching is derived from the pricing table itself and tries the longest key
first, so a specific model always wins over a shorter prefix. Do not reintroduce
substring matching against a hardcoded list of names.
