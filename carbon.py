"""Carbon ledger: grams of CO2e beside the euros, from the same telemetry.

Cost and carbon are the same measurement in two units. Substacker already records the
model, the provider and the token counts for every call, which is exactly the input an
emissions estimate needs. This module turns that record into gCO2e.

The hard part is not the arithmetic, it is the honesty. Published per-inference figures
exist for a handful of models and for nothing else. Where a figure exists this module
returns it with its provenance; where none exists it returns an explicit *unknown*, and
there is deliberately no way to get a number out of it instead. `EmissionsEstimate`
refuses to be constructed with a value and an ``UNKNOWN`` provenance, or with no value
and a ``MEASURED`` one, so "we don't know" can never decay into a silent zero on the way
to a dashboard. A zero would read as clean; the truth is that we cannot say.

Read `docs/CARBON-METHODOLOGY.md` before quoting any number this module produces. It
states the system boundary, what is excluded from it, and why. Estimates are marketing
claims the moment they reach a user, and from 27 September 2026 the EU Empowering
Consumers Directive applies to them.

Everything here is a pure function over stdlib types. No network, no I/O, no pandas.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

# Rounding for reported gCO2e. Four decimals of a gram is 0.1 mg, well below the
# precision any published factor supports, but it keeps per-call values from collapsing
# to zero before they are summed.
GRAM_PRECISION = Decimal("0.0001")


class EmissionsProvenance(Enum):
    """Where a number came from. Reported with every estimate, never inferred."""

    #: A figure the provider published from its own production measurement.
    MEASURED = "measured"
    #: Scaled arithmetically from a published life-cycle assessment.
    DERIVED = "derived"
    #: No published figure exists for this model. There is no number.
    UNKNOWN = "unknown"


class EmissionsBasis(Enum):
    """What the published figure is denominated in.

    Providers do not publish in a common unit. Google publishes per prompt, Mistral per
    response of a stated length. Converting one into the other requires assumptions
    neither provider supports, so the basis is carried through to the caller instead of
    being normalised away.
    """

    #: A whole request, regardless of its size. Does not scale with tokens.
    PER_REQUEST = "per_request"
    #: Per 1,000 output tokens. Input tokens are not separately attributed.
    PER_1K_OUTPUT_TOKENS = "per_1k_output_tokens"
    #: No basis, because there is no figure.
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class EmissionsFactor:
    """A published emissions figure for one model, with its citation attached.

    Every field is required. There is no default, and in particular no default of zero:
    an unmeasured model is represented by having no entry in the table at all, not by an
    entry holding zero.
    """

    gco2e: Decimal
    basis: EmissionsBasis
    provenance: EmissionsProvenance
    provider: str
    source: str
    published: str  # ISO date of the publication the figure is taken from.
    scope: str  # What the figure covers, and what it does not.
    wh: Decimal | None = None  # Energy, where the provider published it.

    def __post_init__(self):
        if self.gco2e < 0:
            raise ValueError("Emissions cannot be negative")
        if self.provenance is EmissionsProvenance.UNKNOWN:
            raise ValueError(
                "An UNKNOWN factor cannot exist. Omit the model from the table instead, "
                "so that lookups return the unknown state rather than a value."
            )
        if self.basis is EmissionsBasis.NOT_APPLICABLE:
            raise ValueError("A published factor must state the basis it is measured on")


@dataclass(frozen=True)
class EmissionsEstimate:
    """The result of an estimate. May legitimately hold no number at all.

    ``gco2e`` is ``None`` when no published factor covers the model. That is the whole
    point of this type: callers cannot mistake an absent estimate for a small one,
    because there is nothing to add up. Sum with :func:`summarise` rather than reaching
    for ``estimate.gco2e or 0``.
    """

    model: str
    gco2e: Decimal | None
    provenance: EmissionsProvenance
    basis: EmissionsBasis
    factor_key: str | None = None
    provider: str | None = None
    source: str | None = None
    published: str | None = None
    scope: str | None = None
    reason: str | None = None  # Set when, and only when, the estimate is unknown.

    def __post_init__(self):
        unknown = self.provenance is EmissionsProvenance.UNKNOWN
        if unknown and self.gco2e is not None:
            raise ValueError("An unknown estimate cannot carry a gCO2e value")
        if unknown and not self.reason:
            raise ValueError("An unknown estimate must say why it is unknown")
        if not unknown and self.gco2e is None:
            raise ValueError(f"A {self.provenance.value} estimate must carry a gCO2e value")
        if not unknown and self.reason:
            raise ValueError("A known estimate must not carry an unknown-reason")

    @property
    def is_known(self) -> bool:
        return self.gco2e is not None


def _factors() -> dict[str, EmissionsFactor]:
    """Per-model emissions factors, keyed by normalised model name.

    Parallel to `CostAnalyzer._initialize_pricing`, and deliberately far shorter. The
    pricing table covers every supported model because every provider publishes prices.
    Almost none of them publish emissions, so this table covers a fraction of the same
    models and the gap is the honest state of the industry, not an omission to be
    filled in later with an interpolation.

    Sources, verified 2026-08-29:

      Google, "Measuring the environmental impact of AI inference", published
      2025-08-21. The median Gemini Apps text prompt consumed 0.24 Wh of energy and
      emitted 0.03 gCO2e (market-based), using 0.26 mL of water. Two caveats that
      travel with the number and are repeated in the methodology document:
        - It is a fleet median across Gemini Apps text prompts, not a per-model figure,
          and not a per-token one. A long prompt and a short one both count 0.03 g.
        - Google's boundary excludes model training and data storage, which is the
          central published critique of the figure. It is an inference-only number.

      Mistral AI, life-cycle assessment of Mistral Large 2, published 2025-07-22 with
      Carbone 4 and ADEME. A 400-token response carried a marginal inference impact of
      1.14 gCO2e and 45 mL of water. Scaled here to 2.85 gCO2e per 1,000 output tokens
      (1.14 / 400 * 1000), which is why it is DERIVED and not MEASURED. Mistral's
      figures reflect a largely nuclear French grid and do not transfer to models served
      elsewhere.

      Anthropic publishes no per-model or per-inference energy or emissions figure. No
      Claude model appears below and none may be added without a published source.
      OpenAI likewise publishes no per-model figure; a widely quoted 0.34 Wh remark
      about ChatGPT is not a documented measurement and is not used here. Azure resells
      OpenAI models and inherits the same absence.

    Coverage is also uneven *within* Google. The 2025 disclosure predates the Gemini 3.x
    line, so those models are absent rather than assumed to match their predecessors.
    """
    google_source = (
        "Google, Measuring the environmental impact of AI inference (2025-08-21): "
        "median Gemini Apps text prompt, 0.24 Wh, 0.03 gCO2e, 0.26 mL water"
    )
    google_scope = (
        "Fleet median across Gemini Apps text prompts, not specific to this model and "
        "not scaled by tokens. Inference only: excludes training and data storage."
    )
    google = {
        "gco2e": Decimal("0.03"),
        "wh": Decimal("0.24"),
        "basis": EmissionsBasis.PER_REQUEST,
        "provenance": EmissionsProvenance.MEASURED,
        "provider": "google",
        "source": google_source,
        "scope": google_scope,
        "published": "2025-08-21",
    }

    mistral_source = (
        "Mistral AI life-cycle assessment with Carbone 4 and ADEME (2025-07-22): "
        "400-token Mistral Large 2 response, 1.14 gCO2e, 45 mL water"
    )
    mistral_scope = (
        "Scaled from a 400-token response to 1,000 output tokens. Input tokens are not "
        "separately attributed. Assumes the French grid Mistral serves from."
    )
    mistral = {
        "gco2e": (Decimal("1.14") / Decimal("400") * Decimal("1000")).quantize(GRAM_PRECISION),
        "wh": None,  # Mistral published emissions and water, not energy, for this figure.
        "basis": EmissionsBasis.PER_1K_OUTPUT_TOKENS,
        "provenance": EmissionsProvenance.DERIVED,
        "provider": "mistral",
        "source": mistral_source,
        "scope": mistral_scope,
        "published": "2025-07-22",
    }

    return {
        # ---------------- Google Gemini ----------------
        # Only the text models that existed when the measurement was published. The
        # Gemini 3.x line is intentionally absent: assuming it matches 2.5 would be a
        # guess wearing a citation.
        "gemini-2.5-pro": EmissionsFactor(**google),
        "gemini-2.5-flash": EmissionsFactor(**google),
        "gemini-2.5-flash-lite": EmissionsFactor(**google),
        "gemini-1.5-pro": EmissionsFactor(**google),
        "gemini-1.5-flash": EmissionsFactor(**google),
        "gemini-pro": EmissionsFactor(**google),
        # ---------------- Mistral ----------------
        # Not in the pricing table, because Substacker does not price Mistral yet. The
        # two tables are parallel, not coupled: a model may be priced and not measured,
        # or measured and not priced.
        "mistral-large-2": EmissionsFactor(**mistral),
        "mistral-large": EmissionsFactor(**mistral),
    }


EMISSIONS_FACTORS: dict[str, EmissionsFactor] = _factors()

# Same suffix stripping the pricing table uses, so "gemini-2.5-pro-latest" and
# "gemini-2.5-pro" resolve to one factor.
_VERSION_SUFFIX = re.compile(r"-(?:latest|preview|\d{8}|\d{4}-\d{2}-\d{2}|\d{4})$")

_NO_FACTOR = (
    "No provider-published emissions figure covers this model. Reporting it as zero "
    "would understate the total, so it is excluded from the estimate and counted "
    "against coverage instead."
)


def normalize_model_name(model_name: str) -> str | None:
    """Map a reported model name onto a key in the factor table.

    Mirrors `CostAnalyzer._normalize_model_name`: exact match, then trailing version or
    date stamps stripped, then the longest matching prefix so that a specific model
    always beats a shorter one. Returns ``None`` when nothing in the table matches,
    which is the common case and not an error.
    """
    if not model_name:
        return None

    model_lower = str(model_name).lower().strip()
    if model_lower in EMISSIONS_FACTORS:
        return model_lower

    stripped = _VERSION_SUFFIX.sub("", model_lower)
    while stripped != model_lower:
        if stripped in EMISSIONS_FACTORS:
            return stripped
        model_lower, stripped = stripped, _VERSION_SUFFIX.sub("", stripped)
    if stripped in EMISSIONS_FACTORS:
        return stripped

    for key in sorted(EMISSIONS_FACTORS, key=len, reverse=True):
        if stripped == key or stripped.startswith(key + "-"):
            return key

    return None


def get_emissions_factor(model_name: str) -> EmissionsFactor | None:
    """Return the published factor for a model, or ``None`` if there is not one."""
    key = normalize_model_name(model_name)
    return EMISSIONS_FACTORS[key] if key else None


def unknown_estimate(model_name: str, reason: str = _NO_FACTOR) -> EmissionsEstimate:
    """Build the explicit unknown state. The only way to represent "no figure"."""
    return EmissionsEstimate(
        model=str(model_name),
        gco2e=None,
        provenance=EmissionsProvenance.UNKNOWN,
        basis=EmissionsBasis.NOT_APPLICABLE,
        reason=reason,
    )


def estimate_emissions(
    model_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    requests: int = 1,
) -> EmissionsEstimate:
    """Estimate gCO2e for one call, or say that it cannot be estimated.

    Args:
        model_name: Model as reported by the provider or the CSV.
        input_tokens: Prompt tokens. Recorded for completeness; no published factor
            currently attributes emissions to input tokens separately, so this argument
            does not change the result for any model in the table today.
        output_tokens: Completion tokens. Drives the per-token factors.
        requests: Number of identical calls, for the per-request factors.

    Returns:
        An `EmissionsEstimate`. Check ``is_known`` before using ``gco2e``; on an unknown
        model ``gco2e`` is ``None`` and ``reason`` explains why. It is never zero as a
        stand-in for "not measured".
    """
    if input_tokens < 0 or output_tokens < 0 or requests < 0:
        raise ValueError("Token counts and request counts cannot be negative")

    key = normalize_model_name(model_name)
    if key is None:
        return unknown_estimate(model_name)

    factor = EMISSIONS_FACTORS[key]

    if factor.basis is EmissionsBasis.PER_REQUEST:
        grams = factor.gco2e * Decimal(requests)
    elif factor.basis is EmissionsBasis.PER_1K_OUTPUT_TOKENS:
        grams = factor.gco2e * Decimal(output_tokens) / Decimal("1000")
    else:  # pragma: no cover - EmissionsFactor rejects any other basis at construction.
        return unknown_estimate(model_name, "Factor has no usable basis")

    return EmissionsEstimate(
        model=str(model_name),
        gco2e=grams.quantize(GRAM_PRECISION, rounding=ROUND_HALF_UP),
        provenance=factor.provenance,
        basis=factor.basis,
        factor_key=key,
        provider=factor.provider,
        source=factor.source,
        published=factor.published,
        scope=factor.scope,
    )


@dataclass
class CarbonCoverage:
    """Running total of gCO2e together with how much of the traffic it actually covers.

    The total is only ever the sum of the calls that *have* a published factor. Quoting
    it without ``coverage_percent`` beside it turns an honest partial measurement into
    an understatement, which is exactly the kind of claim the EU Empowering Consumers
    Directive is aimed at. Keep the two together.
    """

    total_gco2e: Decimal = Decimal("0")
    covered_requests: int = 0
    total_requests: int = 0
    by_provenance: dict[str, int] = field(
        default_factory=lambda: {p.value: 0 for p in EmissionsProvenance}
    )
    unmeasured_models: set[str] = field(default_factory=set)

    def add(self, estimate: EmissionsEstimate, requests: int = 1) -> None:
        """Fold one estimate in. Unknown estimates count against coverage, not toward zero."""
        self.total_requests += requests
        self.by_provenance[estimate.provenance.value] += requests
        if estimate.is_known:
            self.total_gco2e += estimate.gco2e
            self.covered_requests += requests
        else:
            self.unmeasured_models.add(estimate.model)

    @property
    def uncovered_requests(self) -> int:
        return self.total_requests - self.covered_requests

    @property
    def coverage_percent(self) -> float:
        """Share of requests a published factor covers. 0.0 when nothing is covered."""
        if not self.total_requests:
            return 0.0
        return self.covered_requests / self.total_requests * 100

    @property
    def is_complete(self) -> bool:
        """True only when every request was covered by a published factor."""
        return self.total_requests > 0 and self.covered_requests == self.total_requests

    def caveat(self) -> str:
        """One sentence a dashboard can print verbatim next to the total."""
        if not self.total_requests:
            return "No requests analysed."
        calls = "call" if self.total_requests == 1 else "calls"
        if self.is_complete:
            return (
                f"Covers all {self.total_requests} {calls}. Inference only: excludes "
                "training, embodied hardware, storage, network and water."
            )
        remaining = "call" if self.uncovered_requests == 1 else "calls"
        return (
            f"Covers {self.covered_requests} of {self.total_requests} {calls} "
            f"({self.coverage_percent:.0f}%). The other {self.uncovered_requests} {remaining} "
            "ran on models with no published emissions figure and are excluded, so the "
            "real total is higher than the number shown."
        )

    def to_dict(self, include_methodology: bool = True) -> dict:
        """JSON-safe form. ``total_gco2e`` is ``None`` when nothing at all was covered.

        ``include_methodology`` is dropped for nested breakdowns, where repeating the
        document path on every team would only pad the payload.
        """
        payload = {
            "total_gco2e": float(self.total_gco2e) if self.covered_requests else None,
            "covered_requests": self.covered_requests,
            "uncovered_requests": self.uncovered_requests,
            "total_requests": self.total_requests,
            "coverage_percent": round(self.coverage_percent, 1),
            "is_complete": self.is_complete,
            "by_provenance": dict(self.by_provenance),
            "unmeasured_models": sorted(self.unmeasured_models),
            "caveat": self.caveat(),
        }
        if include_methodology:
            payload["methodology"] = "docs/CARBON-METHODOLOGY.md"
        return payload


def summarise(records) -> CarbonCoverage:
    """Aggregate an iterable of ``(model, input_tokens, output_tokens)`` triples.

    Convenience wrapper over `estimate_emissions` and `CarbonCoverage.add` for callers
    that already hold usage rows in memory.
    """
    coverage = CarbonCoverage()
    for model, input_tokens, output_tokens in records:
        coverage.add(estimate_emissions(model, input_tokens, output_tokens))
    return coverage


def factor_coverage_report() -> dict:
    """Which models have a published factor and which providers publish nothing.

    Surfaced by the API so the gap is documented in the product itself rather than only
    in the methodology document.
    """
    models = {}
    for key, factor in sorted(EMISSIONS_FACTORS.items()):
        models[key] = {
            "provider": factor.provider,
            "gco2e": float(factor.gco2e),
            "wh": float(factor.wh) if factor.wh is not None else None,
            "basis": factor.basis.value,
            "provenance": factor.provenance.value,
            "source": factor.source,
            "published": factor.published,
            "scope": factor.scope,
        }
    return {
        "models": models,
        "providers_without_published_figures": {
            "anthropic": "Anthropic publishes no per-model or per-inference energy or emissions figure.",
            "openai": "OpenAI publishes no per-model figure. Informal remarks about ChatGPT are not measurements.",
            "azure": "Azure OpenAI resells OpenAI models and inherits the same absence.",
            "google": "Google's 2025 figure predates the Gemini 3.x line, which is therefore uncovered.",
        },
        "methodology": "docs/CARBON-METHODOLOGY.md",
    }
