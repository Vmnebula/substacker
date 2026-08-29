"""Emissions estimation, and the honesty guarantees around it.

The point of these tests is less that the arithmetic is right — it is a multiplication —
than that the module cannot be made to invent a number. An unmeasured model must come
back as an explicit unknown, unknowns must never fold into a total as zero, and a total
must never travel without the coverage figure that qualifies it.
"""

from decimal import Decimal

import pytest

from carbon import (
    EMISSIONS_FACTORS,
    CarbonCoverage,
    EmissionsBasis,
    EmissionsEstimate,
    EmissionsFactor,
    EmissionsProvenance,
    estimate_emissions,
    factor_coverage_report,
    get_emissions_factor,
    normalize_model_name,
    summarise,
    unknown_estimate,
)

# Models with no published emissions figure from their vendor. Anthropic publishes
# nothing model-specific; OpenAI publishes nothing per-model either.
UNPUBLISHED_MODELS = [
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-3-5-haiku-20241022",
    "gpt-5",
    "gpt-4o",
    "o3-mini",
]


# --------------------------------------------------------------------------------------
# Name normalisation
# --------------------------------------------------------------------------------------


def test_exact_model_name_matches():
    assert normalize_model_name("gemini-2.5-flash") == "gemini-2.5-flash"


def test_normalisation_is_case_and_whitespace_insensitive():
    assert normalize_model_name("  Gemini-2.5-Flash  ") == "gemini-2.5-flash"


def test_date_stamped_variant_falls_back_to_base_model():
    assert normalize_model_name("gemini-2.5-flash-2026-01-15") == "gemini-2.5-flash"


def test_longer_key_wins_over_shorter_prefix():
    """`gemini-2.5-flash-lite` must not collapse onto `gemini-2.5-flash`."""
    assert normalize_model_name("gemini-2.5-flash-lite") == "gemini-2.5-flash-lite"


@pytest.mark.parametrize("model", UNPUBLISHED_MODELS)
def test_unpublished_models_do_not_normalise(model):
    assert normalize_model_name(model) is None


@pytest.mark.parametrize("value", ["", None])
def test_empty_model_name_is_not_an_error(value):
    assert normalize_model_name(value) is None


# --------------------------------------------------------------------------------------
# The unknown state — the core guarantee
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("model", UNPUBLISHED_MODELS)
def test_unpublished_model_returns_unknown_not_zero(model):
    estimate = estimate_emissions(model, input_tokens=1000, output_tokens=1000)

    assert estimate.provenance is EmissionsProvenance.UNKNOWN
    assert estimate.gco2e is None, "an unmeasured model must not produce a number"
    assert estimate.gco2e != Decimal("0"), "zero would understate, not abstain"
    assert estimate.is_known is False
    assert estimate.reason, "an unknown estimate must say why"


def test_unknown_estimate_cannot_carry_a_value():
    with pytest.raises(ValueError):
        EmissionsEstimate(
            model="claude-opus-5",
            gco2e=Decimal("1.0"),
            provenance=EmissionsProvenance.UNKNOWN,
            basis=EmissionsBasis.NOT_APPLICABLE,
            reason="no published figure",
        )


def test_unknown_estimate_must_give_a_reason():
    with pytest.raises(ValueError):
        EmissionsEstimate(
            model="claude-opus-5",
            gco2e=None,
            provenance=EmissionsProvenance.UNKNOWN,
            basis=EmissionsBasis.NOT_APPLICABLE,
        )


def test_known_estimate_must_carry_a_value():
    with pytest.raises(ValueError):
        EmissionsEstimate(
            model="gemini-2.5-flash",
            gco2e=None,
            provenance=EmissionsProvenance.MEASURED,
            basis=EmissionsBasis.PER_REQUEST,
        )


def test_factor_table_cannot_hold_an_unknown_provenance():
    """An unmeasured model is absent from the table, never present holding zero."""
    with pytest.raises(ValueError):
        EmissionsFactor(
            gco2e=Decimal("0"),
            basis=EmissionsBasis.PER_REQUEST,
            provenance=EmissionsProvenance.UNKNOWN,
            provider="Anthropic",
            source="https://example.invalid",
            published="2026-01-01",
            scope="inference",
        )


def test_factor_cannot_be_negative():
    with pytest.raises(ValueError):
        EmissionsFactor(
            gco2e=Decimal("-1"),
            basis=EmissionsBasis.PER_REQUEST,
            provenance=EmissionsProvenance.MEASURED,
            provider="Google",
            source="https://example.invalid",
            published="2026-01-01",
            scope="inference",
        )


# --------------------------------------------------------------------------------------
# Estimation
# --------------------------------------------------------------------------------------


def test_published_model_produces_a_known_estimate():
    estimate = estimate_emissions("gemini-2.5-flash", output_tokens=500)

    assert estimate.is_known
    assert estimate.gco2e is not None
    assert estimate.gco2e > 0
    assert estimate.provenance in (
        EmissionsProvenance.MEASURED,
        EmissionsProvenance.DERIVED,
    )
    assert estimate.source, "a known estimate must cite where the figure came from"
    assert estimate.published, "a known estimate must be dated"


def test_every_estimate_reports_its_basis():
    """Providers publish in different units; the caller is told which one applies."""
    estimate = estimate_emissions("gemini-2.5-flash", output_tokens=100)
    assert estimate.basis in (
        EmissionsBasis.PER_REQUEST,
        EmissionsBasis.PER_1K_OUTPUT_TOKENS,
    )


def test_per_request_factor_scales_with_request_count():
    one = estimate_emissions("gemini-2.5-flash", output_tokens=100, requests=1)
    ten = estimate_emissions("gemini-2.5-flash", output_tokens=100, requests=10)

    if one.basis is EmissionsBasis.PER_REQUEST:
        assert ten.gco2e == one.gco2e * 10


def test_token_based_factor_scales_with_output_tokens():
    small = estimate_emissions("mistral-large-2", output_tokens=400)
    large = estimate_emissions("mistral-large-2", output_tokens=4000)

    if small.basis is EmissionsBasis.PER_1K_OUTPUT_TOKENS:
        assert large.gco2e > small.gco2e


def test_input_tokens_do_not_silently_change_the_result():
    """No published factor attributes emissions to prompt tokens separately."""
    without = estimate_emissions("gemini-2.5-flash", input_tokens=0, output_tokens=500)
    with_input = estimate_emissions("gemini-2.5-flash", input_tokens=50_000, output_tokens=500)

    assert without.gco2e == with_input.gco2e


def test_get_emissions_factor_returns_none_for_unpublished():
    assert get_emissions_factor("claude-opus-5") is None


def test_get_emissions_factor_returns_factor_for_published():
    factor = get_emissions_factor("gemini-2.5-flash")
    assert factor is not None
    # `source` is a prose citation naming the publication, its date and the figure taken
    # from it — richer than a bare URL, and the thing an auditor actually needs.
    assert len(factor.source) > 30
    assert factor.provider.lower() in factor.source.lower()


# --------------------------------------------------------------------------------------
# Coverage accounting
# --------------------------------------------------------------------------------------


def test_unknown_calls_reduce_coverage_rather_than_the_total():
    coverage = CarbonCoverage()
    coverage.add(estimate_emissions("gemini-2.5-flash", output_tokens=100))
    coverage.add(unknown_estimate("claude-opus-5"))

    assert coverage.total_requests == 2
    assert coverage.covered_requests == 1
    assert coverage.uncovered_requests == 1
    assert coverage.coverage_percent == 50.0
    assert coverage.is_complete is False
    assert "claude-opus-5" in coverage.unmeasured_models


def test_fully_covered_traffic_reports_complete():
    coverage = summarise(
        [
            ("gemini-2.5-flash", 100, 200),
            ("gemini-2.5-pro", 100, 200),
        ]
    )

    assert coverage.is_complete
    assert coverage.coverage_percent == 100.0
    assert coverage.uncovered_requests == 0
    assert coverage.total_gco2e > 0


def test_wholly_unmeasured_traffic_reports_no_total():
    coverage = summarise([(model, 100, 200) for model in UNPUBLISHED_MODELS])

    assert coverage.covered_requests == 0
    assert coverage.coverage_percent == 0.0
    assert coverage.to_dict()["total_gco2e"] is None, (
        "with nothing covered the total must be absent, not 0.0"
    )


def test_empty_coverage_does_not_divide_by_zero():
    coverage = CarbonCoverage()
    assert coverage.coverage_percent == 0.0
    assert coverage.is_complete is False
    assert coverage.caveat() == "No requests analysed."


def test_caveat_states_the_shortfall_direction():
    """A partial total understates. The caveat has to say so, not merely hedge."""
    coverage = summarise(
        [
            ("gemini-2.5-flash", 100, 200),
            ("claude-opus-5", 100, 200),
        ]
    )
    caveat = coverage.caveat()

    assert "1 of 2" in caveat
    assert "higher" in caveat, "the reader must learn which way the number is wrong"


def test_complete_caveat_still_names_the_exclusions():
    coverage = summarise([("gemini-2.5-flash", 100, 200)])
    caveat = coverage.caveat()

    assert "training" in caveat
    assert "embodied hardware" in caveat


def test_provenance_is_tallied_per_request():
    coverage = summarise(
        [
            ("gemini-2.5-flash", 10, 10),
            ("claude-opus-5", 10, 10),
            ("gpt-4o", 10, 10),
        ]
    )

    assert coverage.by_provenance[EmissionsProvenance.UNKNOWN.value] == 2
    known = (
        coverage.by_provenance[EmissionsProvenance.MEASURED.value]
        + coverage.by_provenance[EmissionsProvenance.DERIVED.value]
    )
    assert known == 1


def test_to_dict_is_json_safe_and_carries_the_caveat():
    coverage = summarise([("gemini-2.5-flash", 10, 10), ("claude-opus-5", 10, 10)])
    payload = coverage.to_dict()

    assert isinstance(payload["total_gco2e"], float)
    assert isinstance(payload["coverage_percent"], float)
    assert payload["caveat"]
    assert payload["methodology"] == "docs/CARBON-METHODOLOGY.md"
    assert payload["unmeasured_models"] == ["claude-opus-5"]


def test_nested_breakdowns_omit_the_methodology_path():
    coverage = summarise([("gemini-2.5-flash", 10, 10)])
    assert "methodology" not in coverage.to_dict(include_methodology=False)


# --------------------------------------------------------------------------------------
# The factor table itself
# --------------------------------------------------------------------------------------


def test_every_factor_is_cited_and_dated():
    for key, factor in EMISSIONS_FACTORS.items():
        assert len(factor.source) > 30, f"{key} has no substantive citation"
        assert factor.provider.lower() in factor.source.lower(), (
            f"{key} citation does not name the publisher"
        )
        assert factor.published, f"{key} is undated"
        assert factor.scope, f"{key} does not state what it covers"
        assert factor.provenance is not EmissionsProvenance.UNKNOWN


def test_no_anthropic_or_openai_factors_are_invented():
    """Neither vendor publishes model-specific figures. The table must not pretend."""
    for key, factor in EMISSIONS_FACTORS.items():
        assert factor.provider.lower() not in ("anthropic", "openai"), (
            f"{key} claims a published {factor.provider} figure that does not exist"
        )


def test_coverage_report_names_the_gap():
    report = factor_coverage_report()
    assert report, "the product should surface its own coverage gap"
