"""Per-model price table for the cost rollups in Settings.

Costs are quoted in USD per million tokens. Numbers track Anthropic's
public pricing as of 2026-01; update them when the published rates
change. ``unknown`` model IDs price out as ``None`` so the UI shows
"—" rather than misleading false-precision numbers.

Mock and local providers (Ollama / Claude Code) carry no per-call cost
to surface — the cost service substitutes friendly labels at the
endpoint layer instead of using this table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRate:
    input_per_mtok_usd: float
    output_per_mtok_usd: float


# All values approximate; the source of truth is Anthropic's pricing page.
_RATES: dict[str, ModelRate] = {
    "claude-opus-4-7": ModelRate(15.0, 75.0),
    "claude-opus-4-6": ModelRate(15.0, 75.0),
    "claude-sonnet-4-6": ModelRate(3.0, 15.0),
    "claude-haiku-4-5": ModelRate(1.0, 5.0),
    "claude-haiku-4-5-20251001": ModelRate(1.0, 5.0),
}


def rate_for(model: str | None) -> ModelRate | None:
    if not model:
        return None
    return _RATES.get(model)


def estimate_cost_usd(
    *,
    model: str | None,
    tokens_in: int | None,
    tokens_out: int | None,
) -> float | None:
    """Return USD cost or ``None`` if the model rate is unknown.

    A ``None`` token count is treated as zero — partial reporting is
    better than dropping the row entirely.
    """
    rate = rate_for(model)
    if rate is None:
        return None
    in_tokens = max(0, int(tokens_in or 0))
    out_tokens = max(0, int(tokens_out or 0))
    cost_in = in_tokens * rate.input_per_mtok_usd / 1_000_000
    cost_out = out_tokens * rate.output_per_mtok_usd / 1_000_000
    return cost_in + cost_out


__all__ = ["ModelRate", "estimate_cost_usd", "rate_for"]
