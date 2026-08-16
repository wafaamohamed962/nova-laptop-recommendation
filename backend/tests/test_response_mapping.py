from app.response_mapping import (
    build_assistant_message_content,
    build_chat_response,
    build_recommendations,
)
from app.state import LaptopSessionState


def _pick(**overrides) -> dict:
    defaults = dict(
        id=1,
        brand="ASUS",
        model_name="ROG Zephyrus G14",
        processor="AMD Ryzen 9",
        cpu_ghz=3.5,
        ram_gb=32,
        storage_gb=1024,
        screen_size_inches=14.0,
        gpu_name="GeForce RTX 4070",
        gpu_vram_gb=8.0,
        has_dedicated_gpu=True,
        os="Windows",
        battery_life_hours=10.0,
        baseline_price=None,
        selection_reason="Best Overall Match",
        score_breakdown={"performance": 0.9, "vram": 0.8, "portability": 0.5, "value": 0.5, "total": 0.75},
    )
    defaults.update(overrides)
    return defaults


def _price_result(laptop_id: int, listings: list[dict]) -> dict:
    return {
        "laptop_id": laptop_id,
        "brand": "ASUS",
        "model_name": "ROG Zephyrus G14",
        "query": "ASUS ROG Zephyrus G14",
        "listings": listings,
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "from_cache": False,
        "error": None,
    }


def _listing(**overrides) -> dict:
    defaults = dict(
        title="ASUS ROG Zephyrus G14",
        seller="Best Buy",
        price=1899.0,
        currency="USD",
        rating=4.7,
        reviews_count=342,
        product_link="https://example.com/product",
    )
    defaults.update(overrides)
    return defaults


def test_build_recommendations_maps_category_from_selection_reason():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[
            _pick(id=1, selection_reason="Best Overall Match"),
            _pick(id=2, selection_reason="Budget Saver (spec-based estimate; live pricing pending)"),
            _pick(id=3, selection_reason="Power / Future-Proof Pick"),
        ],
        live_price_results=[
            _price_result(1, [_listing()]),
            _price_result(2, [_listing()]),
            _price_result(3, [_listing()]),
        ],
    )

    recs = build_recommendations(state)

    categories = {r.id: r.category for r in recs}
    assert categories["1"] == "best_overall"
    assert categories["2"] == "budget_saver"
    assert categories["3"] == "power_future_proof"


def test_build_recommendations_picks_cheapest_listing():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[
            _price_result(1, [_listing(seller="Best Buy", price=1899.0), _listing(seller="Amazon", price=1799.0)])
        ],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert recs[0].laptop.price == 1799.0
    assert recs[0].laptop.product_url == "https://example.com/product"


def test_build_recommendations_drops_pick_with_no_resolvable_price():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1), _pick(id=2)],
        live_price_results=[
            _price_result(1, [_listing()]),
            _price_result(2, []),  # empty listings, no baseline_price fallback either
        ],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert recs[0].id == "1"


def test_build_recommendations_falls_back_to_baseline_price_when_no_listings():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1, baseline_price=999.0)],
        live_price_results=[_price_result(1, [])],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert recs[0].laptop.price == 999.0


def test_build_recommendations_handles_missing_live_price_result_entirely():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[],  # Phase 5 didn't run / returned nothing for this id
    )

    recs = build_recommendations(state)

    assert recs == []


def test_laptop_field_formatting():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing()])],
    )

    laptop = build_recommendations(state)[0].laptop

    assert laptop.cpu == "AMD Ryzen 9 (3.5 GHz)"
    assert laptop.gpu == "GeForce RTX 4070 (8.0 GB VRAM)"
    assert laptop.ram == "32 GB"
    assert laptop.storage == "1024 GB"
    assert laptop.display == '14.0"'


def test_reasoning_explains_ai_workload_persona():
    state = LaptopSessionState(
        is_ready_to_search=True,
        ai_workload=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert "AI/ML workloads" in recs[0].reasoning
    assert "GeForce RTX 4070" in recs[0].reasoning


def test_reasoning_explains_programmer_intent_wants_strong_gpu():
    """Reproduces the reported ask: a self-described programmer should get a
    tailored explanation naming the GPU, not just a generic spec dump."""
    state = LaptopSessionState(
        is_ready_to_search=True,
        intent="I'm a programmer",
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert "programmer" in recs[0].reasoning
    assert "GeForce RTX 4070" in recs[0].reasoning
    assert "horsepower" in recs[0].reasoning


def test_reasoning_explains_aaa_gaming_persona():
    state = LaptopSessionState(
        is_ready_to_search=True,
        gaming_preference="AAA",
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert "AAA gaming" in recs[0].reasoning


def test_reasoning_explains_portability_persona_with_major():
    state = LaptopSessionState(
        is_ready_to_search=True,
        major="Medicine",
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert "Medicine" in recs[0].reasoning
    assert "battery" in recs[0].reasoning.lower()


def test_reasoning_falls_back_to_spec_summary_with_no_persona_signal():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert "well-rounded" in recs[0].reasoning
    assert "32GB RAM" in recs[0].reasoning


def test_message_content_when_not_ready_echoes_next_question():
    state = LaptopSessionState(is_ready_to_search=False, next_question_to_user="What's your budget?")
    content = build_assistant_message_content(state, [])
    assert content == "What's your budget?"


def test_message_content_when_ready_with_recommendations():
    state = LaptopSessionState(is_ready_to_search=True, top_matched_laptops=[_pick(), _pick(id=2)])
    recs = build_recommendations(
        LaptopSessionState(
            is_ready_to_search=True,
            top_matched_laptops=state.top_matched_laptops,
            live_price_results=[_price_result(1, [_listing()]), _price_result(2, [_listing()])],
        )
    )
    content = build_assistant_message_content(state, recs)
    assert "2 laptops" in content


def test_message_content_notes_dropped_picks_lacking_price():
    state = LaptopSessionState(is_ready_to_search=True, top_matched_laptops=[_pick(id=1), _pick(id=2)])
    recs = build_recommendations(
        LaptopSessionState(
            is_ready_to_search=True,
            top_matched_laptops=state.top_matched_laptops,
            live_price_results=[_price_result(1, [_listing()]), _price_result(2, [])],
        )
    )
    content = build_assistant_message_content(state, recs)
    assert "1 laptop" in content
    assert "other close match" in content


def test_message_content_when_ready_but_all_prices_failed():
    state = LaptopSessionState(is_ready_to_search=True, top_matched_laptops=[_pick()])
    content = build_assistant_message_content(state, [])
    assert "trouble fetching current prices" in content


def test_message_content_when_ready_with_zero_candidates_at_all():
    state = LaptopSessionState(is_ready_to_search=True, top_matched_laptops=[])
    content = build_assistant_message_content(state, [])
    assert "couldn't find any laptops" in content


def test_budget_within_budget_is_kept_with_a_positive_note():
    state = LaptopSessionState(
        is_ready_to_search=True,
        budget_max=1500,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1200.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert "Within your $1,500 budget" in recs[0].reasoning


def test_budget_over_budget_is_hard_excluded():
    """The system must never return a device priced above the user's stated
    budget -- not flagged, not sorted last, excluded entirely."""
    state = LaptopSessionState(
        is_ready_to_search=True,
        budget_max=1500,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=1899.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert recs == []


def test_budget_mixed_pool_keeps_only_in_budget_picks():
    state = LaptopSessionState(
        is_ready_to_search=True,
        budget_max=1500,
        top_matched_laptops=[
            _pick(id=1, selection_reason="Best Overall Match"),
            _pick(id=2, selection_reason="Budget Saver (spec-based estimate; live pricing pending)"),
        ],
        live_price_results=[
            _price_result(1, [_listing(price=1899.0, currency="USD")]),  # over budget -> excluded
            _price_result(2, [_listing(price=999.0, currency="USD")]),  # in budget -> kept
        ],
    )

    recs = build_recommendations(state)

    assert [r.id for r in recs] == ["2"]


def test_budget_non_usd_currency_is_not_filtered():
    """A listing that somehow comes back in a non-USD currency isn't wrongly
    excluded (or wrongly admitted) by comparing mismatched currencies --
    budget_max is always USD (the evaluator asks for it in USD)."""
    state = LaptopSessionState(
        is_ready_to_search=True,
        budget_max=1500,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=50000.0, currency="EGP")])],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert "budget" not in recs[0].reasoning.lower()


def test_budget_not_set_skips_filtering_entirely():
    state = LaptopSessionState(
        is_ready_to_search=True,
        budget_max=None,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing(price=999999.0, currency="USD")])],
    )

    recs = build_recommendations(state)

    assert len(recs) == 1
    assert "budget" not in recs[0].reasoning.lower()


def test_message_content_when_all_picks_are_over_budget():
    state = LaptopSessionState(is_ready_to_search=True, budget_max=1500, top_matched_laptops=[_pick(id=1)])
    content = build_assistant_message_content(state, [])
    assert "$1,500" in content
    assert "budget" in content.lower()


def test_build_chat_response_shape():
    state = LaptopSessionState(
        is_ready_to_search=True,
        top_matched_laptops=[_pick(id=1)],
        live_price_results=[_price_result(1, [_listing()])],
    )

    response = build_chat_response("conv-123", state)

    assert response.conversation_id == "conv-123"
    assert response.done is True
    assert response.message.role == "assistant"
    assert len(response.message.recommendations) == 1
    # wire format uses camelCase
    dumped = response.model_dump(by_alias=True)
    assert "conversationId" in dumped
    assert "productUrl" in dumped["message"]["recommendations"][0]["laptop"]
