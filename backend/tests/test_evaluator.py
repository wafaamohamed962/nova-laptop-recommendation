from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.evaluator import (
    EvaluatorExtraction,
    build_messages,
    compute_readiness,
    merge_extraction,
)
from app.state import LaptopSessionState


def test_merge_extraction_only_overwrites_provided_fields():
    state = LaptopSessionState(intent="gaming", budget_max=1000.0)
    extraction = EvaluatorExtraction(os_preference="Windows")

    updates = merge_extraction(state, extraction)

    assert updates == {"os_preference": "Windows"}


def test_merge_extraction_keeps_explicit_false_and_none_gaming():
    state = LaptopSessionState()
    extraction = EvaluatorExtraction(ai_workload=False, gaming_preference="none")

    updates = merge_extraction(state, extraction)

    assert updates == {"ai_workload": False, "gaming_preference": "none"}


def test_compute_readiness_missing_intent_asks_intent_first():
    ready, question = compute_readiness({"budget_max": 1000, "os_preference": "Windows"})
    assert ready is False
    assert "use this laptop for" in question


def test_compute_readiness_missing_budget():
    ready, question = compute_readiness(
        {"intent": "gaming", "os_preference": "Windows", "gaming_preference": "AAA"}
    )
    assert ready is False
    assert "budget" in question.lower()


def test_compute_readiness_university_intent_requires_major():
    ready, question = compute_readiness(
        {
            "intent": "university",
            "budget_max": 1200,
            "os_preference": "Windows",
            "gaming_preference": "none",
            "major": None,
        }
    )
    assert ready is False
    assert "major" in question.lower()


def test_compute_readiness_missing_gaming_and_ai_signal():
    ready, question = compute_readiness(
        {"intent": "work", "budget_max": 1200, "os_preference": "Windows"}
    )
    assert ready is False
    assert "gaming" in question.lower() or "ai" in question.lower()


def test_compute_readiness_true_when_all_core_slots_present():
    ready, question = compute_readiness(
        {
            "intent": "gaming",
            "budget_max": 1500,
            "os_preference": "Windows",
            "gaming_preference": "AAA",
        }
    )
    assert ready is True
    assert question is None


def test_build_messages_converts_history_to_lc_messages_in_order():
    state = LaptopSessionState(
        intent="gaming",
        budget_max=1500,
        conversation_history=[
            {"role": "user", "content": "I want a gaming laptop"},
            {"role": "assistant", "content": "What's your budget?"},
            {"role": "user", "content": "Around $1500"},
        ],
    )

    messages = build_messages(state)

    assert isinstance(messages[0], SystemMessage)
    assert "gaming" in messages[0].content  # known_state is embedded in the system prompt
    assert [type(m) for m in messages[1:]] == [HumanMessage, AIMessage, HumanMessage]
    assert messages[1].content == "I want a gaming laptop"
    assert messages[3].content == "Around $1500"


def test_build_messages_handles_empty_history():
    state = LaptopSessionState()

    messages = build_messages(state)

    assert len(messages) == 1
    assert isinstance(messages[0], SystemMessage)


def test_compute_readiness_true_for_university_with_major_and_no_gaming():
    ready, question = compute_readiness(
        {
            "intent": "university, computer science",
            "budget_max": 1200,
            "os_preference": "no preference",
            "major": "Computer Science",
            "ai_workload": True,
        }
    )
    assert ready is True
    assert question is None
