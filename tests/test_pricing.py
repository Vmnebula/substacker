"""Pricing, model normalisation, and provider detection.

Cost figures are the product's whole purpose, so these tests pin the arithmetic and
the name matching rather than just asserting that a lookup returns something.
"""

from decimal import Decimal

import pytest

from cost_analyzer import CostAnalyzer, ModelPricing, OpenAIWasteAnalyzer, Provider


@pytest.fixture
def analyzer():
    return CostAnalyzer()


# (reported name, expected pricing key, expected provider, expected input price per 1K)
NORMALISATION_CASES = [
    # Current OpenAI
    ("gpt-5", "gpt-5", Provider.OPENAI, "0.00125"),
    ("gpt-5-mini", "gpt-5-mini", Provider.OPENAI, "0.00025"),
    ("gpt-5-nano", "gpt-5-nano", Provider.OPENAI, "0.00005"),
    ("gpt-5.6-sol", "gpt-5.6-sol", Provider.OPENAI, "0.005"),
    ("gpt-4.1", "gpt-4.1", Provider.OPENAI, "0.002"),
    ("gpt-4o", "gpt-4o", Provider.OPENAI, "0.0025"),
    ("gpt-4o-mini", "gpt-4o-mini", Provider.OPENAI, "0.00015"),
    # Reasoning series carries no "gpt" prefix
    ("o3", "o3", Provider.OPENAI, "0.002"),
    ("o3-mini", "o3-mini", Provider.OPENAI, "0.0011"),
    ("o4-mini", "o4-mini", Provider.OPENAI, "0.0011"),
    ("o1-pro", "o1-pro", Provider.OPENAI, "0.150"),
    # Current Anthropic
    ("claude-opus-5", "claude-opus-5", Provider.ANTHROPIC, "0.005"),
    ("claude-sonnet-5", "claude-sonnet-5", Provider.ANTHROPIC, "0.003"),
    ("claude-haiku-4-5", "claude-haiku-4-5", Provider.ANTHROPIC, "0.001"),
    ("claude-fable-5", "claude-fable-5", Provider.ANTHROPIC, "0.010"),
    ("claude-opus-4-8", "claude-opus-4-8", Provider.ANTHROPIC, "0.005"),
    # Current Gemini
    ("gemini-3.7-flash", "gemini-3.7-flash", Provider.GOOGLE, "0.00075"),
    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite", Provider.GOOGLE, "0.0003"),
    ("gemini-2.5-pro", "gemini-2.5-pro", Provider.GOOGLE, "0.00125"),
    # Azure
    ("azure-gpt-4o", "azure-gpt-4o", Provider.AZURE, "0.0025"),
    ("azure-gpt-35-turbo", "azure-gpt-35-turbo", Provider.AZURE, "0.0005"),
    # Retired models still price for historical exports
    ("gpt-4", "gpt-4", Provider.OPENAI, "0.030"),
    ("gpt-3.5-turbo", "gpt-3.5-turbo", Provider.OPENAI, "0.0005"),
    ("claude-3-opus", "claude-3-opus", Provider.ANTHROPIC, "0.015"),
    ("gemini-1.5-flash", "gemini-1.5-flash", Provider.GOOGLE, "0.000075"),
]


@pytest.mark.parametrize("reported,expected_key,provider,input_price", NORMALISATION_CASES)
def test_model_resolves_to_correct_price(analyzer, reported, expected_key, provider, input_price):
    assert analyzer._normalize_model_name(reported) == expected_key

    pricing, is_known = analyzer._get_model_pricing(reported)
    assert is_known, f"{reported} should be a known model"
    assert pricing.input_price == Decimal(input_price)
    assert analyzer._detect_provider(reported) == provider


@pytest.mark.parametrize(
    "reported,expected_key",
    [
        ("GPT-4o", "gpt-4o"),
        ("  gpt-4o  ", "gpt-4o"),
        ("gpt-4o-2024-08-06", "gpt-4o"),
        ("gpt-4-0613", "gpt-4"),
        ("claude-3-opus-20240229", "claude-3-opus-20240229"),
        ("gemini-2.5-pro-latest", "gemini-2.5-pro"),
        ("gpt-4-turbo-preview", "gpt-4-turbo-preview"),
    ],
)
def test_case_whitespace_and_version_suffixes(analyzer, reported, expected_key):
    assert analyzer._normalize_model_name(reported) == expected_key


def test_gpt_4o_is_not_confused_with_gpt_4(analyzer):
    """Regression: substring matching billed gpt-4o at the gpt-4 rate, 12x too high.

    The two models must resolve independently and price differently.
    """
    assert analyzer._normalize_model_name("gpt-4o") == "gpt-4o"
    assert analyzer._normalize_model_name("gpt-4") == "gpt-4"

    gpt4o, _ = analyzer._get_model_pricing("gpt-4o")
    gpt4, _ = analyzer._get_model_pricing("gpt-4")
    assert gpt4o.input_price < gpt4.input_price
    assert gpt4o.input_price == Decimal("0.0025")


def test_unknown_model_is_flagged_and_costs_nothing(analyzer):
    """An unrecognised model must be reported, never silently priced as something else."""
    pricing, is_known = analyzer._get_model_pricing("some-model-that-does-not-exist")
    assert is_known is False
    assert pricing.input_price == Decimal("0")
    assert pricing.output_price == Decimal("0")


@pytest.mark.parametrize(
    "model,prompt_tokens,completion_tokens,expected",
    [
        # 1M input + 1M output at $5/$25 per 1M
        ("claude-opus-5", 1_000_000, 1_000_000, "30"),
        # 1M input + 1M output at $1.25/$10 per 1M
        ("gpt-5", 1_000_000, 1_000_000, "11.25"),
        # 1K input + 1K output at $2.50/$10 per 1M
        ("gpt-4o", 1_000, 1_000, "0.0125"),
        ("claude-opus-5", 0, 0, "0"),
    ],
)
def test_cost_arithmetic(analyzer, model, prompt_tokens, completion_tokens, expected):
    pricing, _ = analyzer._get_model_pricing(model)
    cost = analyzer._calculate_row_cost(prompt_tokens, completion_tokens, pricing)
    assert cost == Decimal(expected)


def test_costs_use_decimal_not_float(analyzer):
    """Aggregating float costs drifts; the pricing path must stay in Decimal."""
    pricing, _ = analyzer._get_model_pricing("gpt-4o")
    assert isinstance(pricing.input_price, Decimal)

    cost = analyzer._calculate_row_cost(1000, 1000, pricing)
    assert isinstance(cost, Decimal)

    total = sum((analyzer._calculate_row_cost(333, 333, pricing) for _ in range(3)), Decimal(0))
    assert isinstance(total, Decimal)


def test_every_price_is_positive_and_output_not_cheaper_than_input(analyzer):
    """Sanity sweep over the whole table: no provider charges less for output."""
    for name, pricing in analyzer.pricing.items():
        assert pricing.input_price > 0, f"{name} has a non-positive input price"
        assert pricing.output_price > 0, f"{name} has a non-positive output price"
        assert pricing.output_price >= pricing.input_price, (
            f"{name} prices output below input, which no provider currently does"
        )


def test_negative_pricing_is_rejected():
    with pytest.raises(ValueError):
        ModelPricing(Decimal("-1"), Decimal("1"), Provider.OPENAI)


def test_legacy_class_name_still_importable():
    """OpenAIWasteAnalyzer is kept as an alias so existing imports keep working."""
    assert OpenAIWasteAnalyzer is CostAnalyzer


@pytest.mark.parametrize("csv_name", ["template.csv", "example_with_teams.csv"])
def test_shipped_sample_data_is_fully_priced(analyzer, csv_name):
    """Sample files are the first thing a new user runs, so they must not contain a
    model the pricing table does not know. This is the guard against the sample data
    quietly going stale as providers retire models.
    """
    import csv
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "sample_data" / csv_name
    with path.open(newline="") as handle:
        models = {row["model"].strip() for row in csv.DictReader(handle)}

    assert models, f"{csv_name} contained no rows"

    unpriced = [m for m in sorted(models) if not analyzer._get_model_pricing(m)[1]]
    assert not unpriced, f"{csv_name} references models with no price: {unpriced}"


class TestDatabaseBackendSelection:
    """The backend must not silently change under an existing deployment.

    Before DATABASE_TYPE was wired up, the application always used Supabase. A
    deployment that never set the variable must therefore keep using Supabase, while a
    fresh clone with no configuration at all must get SQLite.
    """

    @staticmethod
    def _select(monkeypatch, **env):
        import importlib

        import app

        for key in ("DATABASE_TYPE", "SUPABASE_URL", "SUPABASE_KEY"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(app)._select_database_type()

    def test_defaults_to_sqlite_with_no_configuration(self, monkeypatch):
        assert self._select(monkeypatch) == "sqlite"

    def test_infers_supabase_when_credentials_are_present(self, monkeypatch):
        got = self._select(
            monkeypatch, SUPABASE_URL="https://x.supabase.co", SUPABASE_KEY="k"
        )
        assert got == "supabase"

    def test_explicit_setting_always_wins(self, monkeypatch):
        got = self._select(
            monkeypatch,
            DATABASE_TYPE="sqlite",
            SUPABASE_URL="https://x.supabase.co",
            SUPABASE_KEY="k",
        )
        assert got == "sqlite"

    def test_partial_supabase_credentials_do_not_trigger_inference(self, monkeypatch):
        assert self._select(monkeypatch, SUPABASE_URL="https://x.supabase.co") == "sqlite"
