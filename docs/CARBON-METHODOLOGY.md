# Carbon methodology

How Substacker turns usage records into grams of CO₂-equivalent, what that number covers,
and — more importantly — what it does not.

**Last reviewed:** 2026-08-29

This document exists because an emissions figure without its boundaries is not a
measurement, it is a marketing claim. Under the EU Empowering Consumers for the Green
Transition Directive (2024/825), which applies EU-wide from **27 September 2026**, generic
or unsubstantiated environmental claims are prohibited, with penalties reaching 4% of
in-country turnover per member state. Everything below is written to be checkable.

## The short version

- We estimate **inference emissions only**, from figures the model providers themselves
  publish.
- Where a provider publishes nothing, we return **no number** — not zero.
- Every total is reported with the **share of traffic it actually covers**. A total without
  that share is an understatement.

## What is included

| Included | Source |
|---|---|
| Energy consumed serving an inference request | Provider-published production measurements and life-cycle assessments |
| Operational emissions from that energy | The provider's own gCO₂e figure, which embeds their grid assumptions |

## What is excluded

Everything below is outside the boundary. None of it is in the number.

- **Model training.** Amortised training emissions are excluded. For frontier models this
  is a large omission.
- **Embodied hardware.** Manufacture, transport and end-of-life of the servers.
- **Data storage.** Vector stores, logs, retained context.
- **Network transfer** between the client and the provider.
- **Water.** Providers publish it (Google: 0.26 mL per median prompt; Mistral: 45 mL per
  400-token response) but we do not aggregate it, because a partial water figure across a
  mixed-provider workload would mislead more than it informs.
- **Your own infrastructure.** If you run the Vmnebula runtime, container compute is metered
  separately — see the platform's region-aware estimator. Substacker covers the model calls.

This boundary is the same one Google draws, and it attracts the same criticism: a
per-prompt figure that omits training and storage understates lifetime impact. We repeat
the boundary rather than defend it.

## Provenance — three states, never blended

Every estimate carries one of:

| Provenance | Meaning |
|---|---|
| `measured` | The provider published this figure from its own production measurement. |
| `derived` | Scaled arithmetically from a published life-cycle assessment. The arithmetic is shown below. |
| `unknown` | No published figure exists. **There is no number.** |

An `unknown` estimate carries `gco2e = None` and a stated reason. The type system enforces
this: an unknown cannot hold a value, a known cannot omit one, and the factor table refuses
an entry with `unknown` provenance. You cannot accidentally add an unmeasured call to a
total as zero, because there is nothing to add.

## The factor table

### Google — Gemini family

**0.03 gCO₂e and 0.24 Wh per request**, from *Measuring the environmental impact of AI
inference* (2025-08-21). Basis: per request, not per token.

> **Known weakness, stated plainly.** Google published one figure for the **median Gemini
> Apps text prompt**. It did not publish per-model figures. We apply that single figure
> across the whole Gemini family, including `gemini-2.5-pro`.
>
> Median Apps traffic is dominated by smaller, Flash-class prompts, so this **almost
> certainly understates larger Pro-class models** — and it does not vary with response
> length, because the published basis does not. It is labelled `measured` because the
> underlying figure is a real production measurement, but the *attribution to a specific
> model* is an assumption we are making, not something Google stated.
>
> Treat Gemini Pro numbers as a floor. If Google publishes per-model figures, replace this
> row before relying on it in any external claim.

### Mistral — Large family

**2.85 gCO₂e per 1,000 output tokens**, `derived`. Mistral's life-cycle assessment
(2025-07-22) reports **1.14 gCO₂e for a 400-token response** from Mistral Large 2:

```
1.14 gCO₂e ÷ 400 tokens × 1000 = 2.85 gCO₂e per 1k output tokens
```

Linear scaling in output tokens is our assumption, not Mistral's finding.

### Providers that publish nothing

**Anthropic** publishes no model-specific emissions figures. **OpenAI** publishes no
per-model figures. Calls to those models return `unknown`.

This is the single largest limitation of the whole feature. For a workload that is mostly
Claude or GPT, coverage will be low and the reported total will cover a small minority of
actual traffic. The UI must say so; see below.

## Bases are not interchangeable

Providers do not publish in a common unit. Google publishes **per request**; Mistral
publishes **per response of a stated length**, which we scale **per 1k output tokens**.
Converting between the two requires assumptions neither provider supports, so the basis
travels with the estimate rather than being normalised away.

A consequence worth understanding: for Gemini models, a 50-token reply and a 5,000-token
reply currently produce the **same** estimate, because the published basis is per request.

## Coverage — why the total never travels alone

`CarbonCoverage` reports:

- `total_gco2e` — the sum of covered calls only, or `None` when nothing was covered
- `coverage_percent` — the share of requests a published factor covered
- `unmeasured_models` — which models were excluded
- `caveat()` — one sentence, printable verbatim, stating the direction of the error

The caveat says the real total is **higher** than the number shown, because unmeasured
calls are excluded rather than zeroed. Quoting the total without the coverage figure turns
an honest partial measurement into an understatement. Do not do it, in the product or in
any external material.

## Using these numbers externally

If a figure from Substacker appears in a customer-facing claim, a sustainability report or
marketing material:

1. State the boundary — inference only, excluding training, hardware, storage and network.
2. State the coverage percentage.
3. State the date and provider of the underlying figures.
4. Do not describe anything as "carbon neutral", "climate neutral" or "zero emissions" on
   the basis of this data. It does not support those claims, and offset-based neutrality
   claims are specifically restricted from 27 September 2026.

## Revision

Published factors change. Google's per-prompt figure fell substantially year over year, and
providers add and remove disclosures. Re-check every factor against its source before it
appears in anything external, and update `published` dates when you do.

## Sources

- Google, *Measuring the environmental impact of AI inference*, 2025-08-21 —
  https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference
- Mistral AI, life-cycle assessment of Mistral Large 2, 2025-07-22
- Directive (EU) 2024/825 (Empowering Consumers for the Green Transition)
- GHG Protocol, Scope 2 Guidance — location-based vs market-based accounting
