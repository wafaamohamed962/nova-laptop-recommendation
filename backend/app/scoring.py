"""
Multi-Criteria Scoring & Top-k Selector Engine.

Scores each candidate on four dimensions (performance, VRAM, portability,
value), weighted by a persona profile derived from the session's major/intent/
gaming/AI signals, then picks 3 diverse laptops: the best weighted match, a
lean/lower-spec "budget" pick, and a max-spec "power" pick.

Value-dimension note: there's no price data in the static catalog (see
ingest.py), so `value_score` is a neutral 0.5 placeholder for every candidate
right now -- it exists so the 4-dimension weighted structure is already wired
up and ready to receive a real price-per-spec signal once Phase 5 fetches
live prices for whatever this stage selects.
"""

from dataclasses import dataclass
from statistics import median

from app.models import Laptop
from app.state import LaptopSessionState

DimensionWeights = dict[str, float]

_PERFORMANCE_MAJOR_KEYWORDS = (
    "computer science",
    "software",
    "engineering",
    "data science",
    "artificial intelligence",
    "machine learning",
    "information technology",
)
_PORTABILITY_MAJOR_KEYWORDS = (
    "medicine",
    "medical",
    "nursing",
    "business",
    "law",
    "arts",
    "humanities",
    "design",
    "journalism",
    "education",
)


def select_weight_profile(state: LaptopSessionState) -> DimensionWeights:
    if state.gaming_preference == "AAA" or state.ai_workload:
        return {"performance": 0.35, "vram": 0.35, "portability": 0.15, "value": 0.15}

    text = f"{state.major or ''} {state.intent or ''}".lower()
    if any(keyword in text for keyword in _PERFORMANCE_MAJOR_KEYWORDS):
        return {"performance": 0.35, "vram": 0.25, "portability": 0.20, "value": 0.20}
    if any(keyword in text for keyword in _PORTABILITY_MAJOR_KEYWORDS):
        return {"performance": 0.20, "vram": 0.10, "portability": 0.45, "value": 0.25}
    return {"performance": 0.25, "vram": 0.20, "portability": 0.30, "value": 0.25}


def _normalize(raw_values: list[float | None], impute: str = "median", invert: bool = False) -> list[float]:
    """Min-max normalize to [0, 1]. `impute` controls how None is filled in:
    'median' for genuinely-unknown values (e.g. missing battery-life data),
    'zero' for values that are absent because the feature isn't present at
    all (e.g. no VRAM because there's no dedicated GPU)."""
    present = [v for v in raw_values if v is not None]
    if not present:
        return [0.5] * len(raw_values)

    fill = median(present) if impute == "median" else 0.0
    filled = [v if v is not None else fill for v in raw_values]

    lo, hi = min(filled), max(filled)
    if hi == lo:
        return [0.5] * len(filled)  # no differentiation on this axis -> neutral

    normalized = [(v - lo) / (hi - lo) for v in filled]
    return [1.0 - v for v in normalized] if invert else normalized


@dataclass
class ScoredLaptop:
    laptop: Laptop
    performance_score: float
    vram_score: float
    portability_score: float
    value_score: float
    total_score: float


def score_candidates(candidates: list[Laptop], state: LaptopSessionState) -> list[ScoredLaptop]:
    if not candidates:
        return []

    weights = select_weight_profile(state)

    cpu_ghz_n = _normalize([c.cpu_ghz for c in candidates], impute="median")
    ram_n = _normalize([float(c.ram_gb) for c in candidates], impute="median")
    performance_scores = [(a + b) / 2 for a, b in zip(cpu_ghz_n, ram_n)]

    vram_scores = _normalize([c.gpu_vram_gb for c in candidates], impute="zero")

    screen_inverted = _normalize([c.screen_size_inches for c in candidates], impute="median", invert=True)
    battery_n = _normalize([c.battery_life_hours for c in candidates], impute="median")
    portability_scores = [(a + b) / 2 for a, b in zip(screen_inverted, battery_n)]

    value_scores = [0.5] * len(candidates)

    scored = []
    for laptop, perf, vram, port, val in zip(
        candidates, performance_scores, vram_scores, portability_scores, value_scores
    ):
        total = (
            weights["performance"] * perf
            + weights["vram"] * vram
            + weights["portability"] * port
            + weights["value"] * val
        )
        scored.append(ScoredLaptop(laptop, perf, vram, port, val, total))
    return scored


def _to_dict(scored: ScoredLaptop, reason: str) -> dict:
    laptop = scored.laptop
    return {
        "id": laptop.id,
        "brand": laptop.brand,
        "model_name": laptop.model_name,
        "processor": laptop.processor,
        "cpu_ghz": laptop.cpu_ghz,
        "ram_gb": laptop.ram_gb,
        "storage_gb": laptop.storage_gb,
        "screen_size_inches": laptop.screen_size_inches,
        "gpu_name": laptop.gpu_name,
        "gpu_vram_gb": laptop.gpu_vram_gb,
        "has_dedicated_gpu": laptop.has_dedicated_gpu,
        "os": laptop.os,
        "battery_life_hours": laptop.battery_life_hours,
        "baseline_price": laptop.baseline_price,
        "selection_reason": reason,
        "score_breakdown": {
            "performance": round(scored.performance_score, 3),
            "vram": round(scored.vram_score, 3),
            "portability": round(scored.portability_score, 3),
            "value": round(scored.value_score, 3),
            "total": round(scored.total_score, 3),
        },
    }


def select_top_picks(scored: list[ScoredLaptop]) -> list[dict]:
    """Best Overall Match (highest weighted score), Budget Saver (lowest raw
    spec footprint -- a proxy pending real prices from Phase 5), and a
    Power/Future-Proof Pick (highest raw performance+VRAM). Falls back
    gracefully, and dedupes, when the candidate pool is smaller than 3."""
    if not scored:
        return []

    # Dedup by the laptop's real DB id when it has one (the normal case: candidates
    # come from a committed DB query), falling back to Python object identity when
    # it doesn't (e.g. uncommitted ORM objects in tests, where .id is None for
    # everything and would otherwise make every candidate look like the same one).
    def identity_key(s: ScoredLaptop):
        return s.laptop.id if s.laptop.id is not None else id(s.laptop)

    by_total = sorted(scored, key=lambda s: s.total_score, reverse=True)
    best_overall = by_total[0]

    by_power = sorted(scored, key=lambda s: s.performance_score + s.vram_score, reverse=True)
    power_pick = next((s for s in by_power if identity_key(s) != identity_key(best_overall)), best_overall)

    chosen = {identity_key(best_overall), identity_key(power_pick)}
    remaining = [s for s in scored if identity_key(s) not in chosen]
    pool_for_budget = remaining or scored
    budget_saver = min(pool_for_budget, key=lambda s: s.performance_score + s.vram_score)

    candidates_with_reasons = [
        (best_overall, "Best Overall Match"),
        (budget_saver, "Budget Saver (spec-based estimate; live pricing pending)"),
        (power_pick, "Power / Future-Proof Pick"),
    ]

    results: list[dict] = []
    seen: set = set()
    for scored_laptop, reason in candidates_with_reasons:
        key = identity_key(scored_laptop)
        if key in seen:
            continue
        seen.add(key)
        results.append(_to_dict(scored_laptop, reason))
    return results
