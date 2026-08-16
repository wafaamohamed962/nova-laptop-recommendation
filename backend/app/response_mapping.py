"""
Maps internal pipeline output (LaptopSessionState.top_matched_laptops +
.live_price_results) onto the wire-format schemas in api_schemas.py.

The frontend's Laptop.price is a required number -- but a live price lookup
can legitimately fail or come back empty (see app/live_price_tool.py). Rather
than send a fabricated price, a pick with no resolvable price is dropped from
the `recommendations` array entirely; build_assistant_message_content notes
it in the reply text so nothing is silently lost from the user's perspective.

Budget handling: Phase 4's scoring never sees price (there's no price data in
the static catalog -- see ingest.py), so it's purely spec-based. Budget is a
hard filter applied here, once Phase 5 resolves a real USD price for the
picks it already made -- anything over budget_max is excluded entirely, not
just flagged. app/scoring.py deliberately over-selects (min_count=8) so
there's a buffer of candidates to filter down from.
"""

import uuid
from datetime import datetime, timezone

from app.api_schemas import ChatMessage, ChatResponse, Laptop, Recommendation, RecommendationCategory
from app.persona import classify_persona
from app.state import LaptopSessionState

_CATEGORY_KEYWORDS: list[tuple[str, RecommendationCategory]] = [
    ("Best Overall", "best_overall"),
    ("Budget Saver", "budget_saver"),
    ("Power", "power_future_proof"),
    ("Great Match", "best_overall"),  # runner-up picks beyond the core 3 (see scoring.py)
]


def _map_category(selection_reason: str) -> RecommendationCategory:
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in selection_reason:
            return category
    return "best_overall"  # safe default; shouldn't be reachable given scoring.py's fixed labels


def _cheapest_listing(listings: list[dict]) -> dict | None:
    priced = [listing for listing in listings if listing.get("price") is not None]
    if not priced:
        return None
    return min(priced, key=lambda listing: listing["price"])


def _find_price_result(laptop_id: int, live_price_results: list[dict]) -> dict | None:
    return next((r for r in live_price_results if r.get("laptop_id") == laptop_id), None)


def _format_cpu(pick: dict) -> str:
    processor = pick.get("processor") or "Unknown processor"
    cpu_ghz = pick.get("cpu_ghz")
    return f"{processor} ({cpu_ghz} GHz)" if cpu_ghz else processor


def _format_gpu(pick: dict) -> str | None:
    gpu_name = pick.get("gpu_name")
    if not gpu_name:
        return None
    vram = pick.get("gpu_vram_gb")
    return f"{gpu_name} ({vram} GB VRAM)" if vram else gpu_name


def _format_display(pick: dict) -> str:
    screen = pick.get("screen_size_inches")
    return f'{screen}"' if screen else "N/A"


def _persona_reason(state: LaptopSessionState, pick: dict) -> str:
    """Explains *why* this laptop suits this specific user -- e.g. "since
    you're running AI workloads, the RTX 4070 gives you real headroom" --
    rather than just listing specs. Uses the same persona classification
    that drove the scoring weights (app/persona.py), so the stated reason
    always matches the actual reason it was picked."""
    gpu = _format_gpu(pick) or "integrated graphics"
    ram = pick.get("ram_gb")
    cpu = pick.get("processor") or "the processor"
    display = _format_display(pick)
    battery = pick.get("battery_life_hours")

    persona = classify_persona(state)

    if persona == "ai_workload":
        return f"Since you'll be running AI/ML workloads, the {gpu} and {ram}GB RAM give you real headroom to run models locally."
    if persona == "gaming_aaa":
        return f"For AAA gaming, the {gpu} is built to handle demanding modern titles at solid settings."
    if persona == "gaming_casual":
        return "For casual gaming, you've got more graphics power here than you'll typically need."
    if persona == "performance":
        context = state.major or state.intent or "your technical work"
        return (
            f"Since you mentioned {context}, the {cpu} and {gpu} give you the horsepower for "
            "compiling, running VMs, or other demanding tasks."
        )
    if persona == "portability":
        context = state.major or state.intent or "your coursework"
        battery_phrase = f"{battery}h battery life" if battery else "long battery life"
        return f"For {context}, the {display} display and {battery_phrase} make this easy to carry around."

    parts = [f"{ram}GB RAM", gpu, f"{display} display"]
    if battery:
        parts.append(f"~{battery}h battery")
    return f"A well-rounded pick with {', '.join(parts)}."


def _build_reasoning(pick: dict, state: LaptopSessionState, budget_max: float | None) -> str:
    breakdown = pick.get("score_breakdown", {})
    total = breakdown.get("total")
    score_note = f" Match score: {round(total * 100)}/100." if total is not None else ""
    reasoning = f"{pick.get('selection_reason', '')} -- {_persona_reason(state, pick)}{score_note}"
    if budget_max is not None:
        reasoning += f" Within your ${budget_max:,.0f} budget."
    return reasoning


def _map_laptop_pick(pick: dict, state: LaptopSessionState) -> Recommendation | None:
    price_result = _find_price_result(pick["id"], state.live_price_results)
    listing = _cheapest_listing(price_result["listings"]) if price_result else None
    price = listing["price"] if listing else pick.get("baseline_price")
    if price is None:
        return None  # no resolvable price anywhere -- don't fabricate one

    currency = (listing or {}).get("currency", "USD")
    # Budget is always expressed in USD (the evaluator asks for it in USD --
    # see app/agents/evaluator.py). Only enforce the hard filter when we can
    # actually trust the comparison; a non-USD listing is left unfiltered
    # rather than wrongly excluded or wrongly admitted.
    if state.budget_max is not None and currency == "USD" and price > state.budget_max:
        return None

    breakdown = pick.get("score_breakdown", {})
    laptop = Laptop(
        id=str(pick["id"]),
        brand=pick["brand"],
        model=pick["model_name"],
        cpu=_format_cpu(pick),
        gpu=_format_gpu(pick),
        ram=f"{pick['ram_gb']} GB",
        storage=f"{pick['storage_gb']} GB",
        display=_format_display(pick),
        price=price,
        currency=currency,
        product_url=(listing or {}).get("product_link"),
        image_url=None,  # not captured by Phase 5's PriceListing today
    )
    return Recommendation(
        id=str(pick["id"]),
        category=_map_category(pick.get("selection_reason", "")),
        laptop=laptop,
        reasoning=_build_reasoning(pick, state, state.budget_max if currency == "USD" else None),
        score=round(breakdown["total"] * 100, 1) if breakdown.get("total") is not None else None,
    )


def build_recommendations(state: LaptopSessionState) -> list[Recommendation]:
    mapped = [_map_laptop_pick(pick, state) for pick in state.top_matched_laptops]
    return [r for r in mapped if r is not None]


def build_assistant_message_content(state: LaptopSessionState, recommendations: list[Recommendation]) -> str:
    if not state.is_ready_to_search:
        return state.next_question_to_user or "Could you tell me a bit more about what you're looking for?"

    total_picks = len(state.top_matched_laptops)
    if not recommendations:
        if total_picks == 0:
            return "I couldn't find any laptops matching your requirements. Want to adjust your budget or preferences?"
        if state.budget_max is not None:
            return (
                f"I found some strong matches, but none of them fit within your ${state.budget_max:,.0f} "
                "budget once I checked live prices. Want to raise your budget or adjust other preferences?"
            )
        return (
            "I found some strong matches, but I'm having trouble fetching current prices right now "
            "-- please try again in a moment."
        )

    intro = f"I found {len(recommendations)} laptop{'s' if len(recommendations) != 1 else ''} for you:"
    dropped = total_picks - len(recommendations)
    if dropped > 0 and state.budget_max is not None:
        intro += f" ({dropped} other close match{'es' if dropped != 1 else ''} were over budget or lacked live pricing.)"
    elif dropped > 0:
        intro += f" ({dropped} other close match{'es' if dropped != 1 else ''} lacked live pricing right now.)"

    return intro


def build_chat_response(conversation_id: str, state: LaptopSessionState) -> ChatResponse:
    recommendations = build_recommendations(state)
    content = build_assistant_message_content(state, recommendations)

    message = ChatMessage(
        id=str(uuid.uuid4()),
        role="assistant",
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="sent",
        recommendations=recommendations or None,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        message=message,
        done=state.is_ready_to_search,
    )
