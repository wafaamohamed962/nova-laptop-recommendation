from app.agents.evaluator import EvaluatorExtraction
from app.graph import route_after_evaluator, run_turn
from app.state import LaptopSessionState
from tests.conftest import make_laptop, make_session_factory
from tests.fakes import FakeStructuredExtractor


def _sample_session_factory():
    return make_session_factory(
        [
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=6.0, cpu_ghz=3.5),
            make_laptop(os="Windows", ram_gb=32, has_dedicated_gpu=True, gpu_vram_gb=8.0, cpu_ghz=4.2),
            make_laptop(os="Windows", ram_gb=8, has_dedicated_gpu=False, cpu_ghz=2.0),
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=4.0, cpu_ghz=3.0),
            make_laptop(os="macOS", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=4.0, cpu_ghz=3.2),
        ]
    )


def test_search_node_populates_top_matched_laptops_directly():
    from app.graph import build_search_node

    node = build_search_node(session_factory=_sample_session_factory())
    state = LaptopSessionState(
        intent="gaming",
        budget_max=2000,
        os_preference="Windows",
        gaming_preference="AAA",
        is_ready_to_search=True,
    )

    updates = node(state)

    assert "top_matched_laptops" in updates
    assert len(updates["top_matched_laptops"]) == 3
    assert all(pick["os"] == "Windows" for pick in updates["top_matched_laptops"])


def test_route_after_evaluator_ask_when_not_ready():
    state = LaptopSessionState(is_ready_to_search=False)
    assert route_after_evaluator(state) == "ask"


def test_route_after_evaluator_search_when_ready():
    state = LaptopSessionState(is_ready_to_search=True)
    assert route_after_evaluator(state) == "search"


def test_first_turn_asks_a_clarifying_question():
    extractor = FakeStructuredExtractor([EvaluatorExtraction(intent="gaming")])
    state = LaptopSessionState()

    result = run_turn(state, "I want a gaming laptop", structured_extractor=extractor)

    assert result.intent == "gaming"
    assert result.is_ready_to_search is False
    assert result.next_question_to_user is not None
    assert result.conversation_history[-2] == {"role": "user", "content": "I want a gaming laptop"}
    assert result.conversation_history[-1]["role"] == "assistant"


def test_multi_turn_conversation_reaches_ready_state():
    state = LaptopSessionState()

    state = run_turn(
        state,
        "I want a gaming laptop",
        structured_extractor=FakeStructuredExtractor([EvaluatorExtraction(intent="gaming")]),
    )
    assert state.is_ready_to_search is False

    state = run_turn(
        state,
        "Budget is around $1500",
        structured_extractor=FakeStructuredExtractor([EvaluatorExtraction(budget_max=1500)]),
    )
    assert state.is_ready_to_search is False

    state = run_turn(
        state,
        "AAA titles, and Windows please",
        structured_extractor=FakeStructuredExtractor(
            [EvaluatorExtraction(gaming_preference="AAA", os_preference="Windows")]
        ),
        session_factory=_sample_session_factory(),
    )

    assert state.is_ready_to_search is True
    assert state.next_question_to_user is None
    assert state.intent == "gaming"
    assert state.budget_max == 1500
    assert state.os_preference == "Windows"
    assert state.gaming_preference == "AAA"
    # ready-turn shouldn't append a new assistant question to the transcript
    assert state.conversation_history[-1] == {"role": "user", "content": "AAA titles, and Windows please"}
    # the search pipeline should have run and populated top picks
    assert len(state.top_matched_laptops) == 3
    reasons = {pick["selection_reason"] for pick in state.top_matched_laptops}
    assert any("Best Overall" in r for r in reasons)


def test_ready_state_does_not_clobber_previously_collected_slots():
    """A later turn that only supplies one new slot must not wipe out earlier ones."""
    state = LaptopSessionState(
        intent="work", budget_max=1000, os_preference="macOS", gaming_preference="none"
    )
    extractor = FakeStructuredExtractor([EvaluatorExtraction(budget_max=1200)])

    result = run_turn(
        state,
        "Actually bump my budget to $1200",
        structured_extractor=extractor,
        session_factory=_sample_session_factory(),
    )

    assert result.budget_max == 1200
    assert result.intent == "work"
    assert result.os_preference == "macOS"
    assert result.is_ready_to_search is True
    assert len(result.top_matched_laptops) >= 1
