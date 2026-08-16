"""
Evaluator Agent: the conversational "tech clerk" strategist.

Design note (deviation from a pure LLM-decides-everything approach): the LLM's
job here is narrowed to *slot extraction only* -- pulling intent/budget/OS/etc.
out of the latest user message. Whether the session is actually ready to search,
and what question to ask next, is decided by deterministic code in this module
(compute_readiness / QUESTION_TEMPLATES) rather than trusted to the LLM's own
judgment. This makes "are we ready yet" testable and reliable without depending
on the model consistently getting a boolean right, while still using the LLM
for what it's good at (free-text -> structured slots).
"""

from typing import Literal, Optional, Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app.state import LaptopSessionState

SYSTEM_PROMPT = """\
You are a knowledgeable, friendly laptop shopping assistant (a "tech clerk"). \
Your only job right now is to extract structured shopping requirements from the \
conversation so far. Do not answer questions or recommend products yet.

Extract only what the user has actually stated or clearly implied. Leave a field \
unset (null) if it was not mentioned in this conversation. Do not guess.

Field guidance:
- intent: the primary use case in a couple of words, e.g. "university", "gaming", \
"work", "general". If the user mentions a major/field of study, infer "university".
- major: the user's major or field of study, only if explicitly mentioned.
- gaming_preference: "AAA" if they mention demanding/modern games, "casual" for \
light/indie gaming, "none" if they explicitly say they don't game. Leave null if \
gaming was never discussed.
- ai_workload: true if they mention running local AI/ML models, LLMs, deep learning, \
or similar; false if they explicitly say they don't need that; null if never discussed.
- os_preference: "Windows", "macOS", "Linux", or "no preference" if they say they're \
flexible. Leave null if never discussed.
- brand_preference: the specific brand they want (e.g. "ASUS", "Dell", "HP", "Lenovo", \
"MSI", "Apple"), or "no preference" if they say they're open to any brand. Leave null \
if never discussed.
- budget_max: the maximum amount in US dollars (USD) the user is willing to spend, as \
a plain number.

Here is what we already know from earlier in the conversation (do not repeat it in \
your extraction unless the user just changed it): {known_state}
"""

QUESTION_TEMPLATES: dict[str, str] = {
    "intent": "To start, what will you mainly use this laptop for — school, gaming, work, or something else?",
    "budget_max": "What's your budget for this laptop, in US dollars — roughly the max you'd like to spend?",
    "gaming_or_ai": (
        "Will you be doing any gaming, or running AI/ML workloads like local LLMs, on this laptop?"
    ),
    "os_preference": "Do you have an OS preference — Windows, macOS, Linux — or no preference?",
    "brand_preference": "Do you have a brand preference — like ASUS, Dell, HP, Lenovo, MSI, or Apple — or no preference?",
    "major": "What's your major or field of study? That helps me match the right specs.",
}


class EvaluatorExtraction(BaseModel):
    intent: Optional[str] = None
    major: Optional[str] = None
    gaming_preference: Optional[Literal["AAA", "casual", "none"]] = None
    ai_workload: Optional[bool] = None
    os_preference: Optional[Literal["Windows", "macOS", "Linux", "no preference"]] = None
    brand_preference: Optional[str] = None
    budget_max: Optional[float] = None


class StructuredExtractor(Protocol):
    """Anything with .invoke(messages) -> EvaluatorExtraction. Real impl: an LLM
    wrapped in with_structured_output(); tests use a hand-built fake."""

    def invoke(self, messages: list) -> EvaluatorExtraction: ...


_UNIVERSITY_KEYWORDS = ("university", "college", "student", "school")

_ALWAYS_REQUIRED = ("intent", "budget_max", "os_preference", "brand_preference")


def build_messages(state: LaptopSessionState) -> list:
    known_state = {
        "intent": state.intent,
        "major": state.major,
        "gaming_preference": state.gaming_preference,
        "ai_workload": state.ai_workload,
        "os_preference": state.os_preference,
        "brand_preference": state.brand_preference,
        "budget_max": state.budget_max,
    }
    messages: list = [SystemMessage(content=SYSTEM_PROMPT.format(known_state=known_state))]
    for turn in state.conversation_history:
        role, content = turn.get("role"), turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def merge_extraction(state: LaptopSessionState, extraction: EvaluatorExtraction) -> dict:
    """Only overwrite a slot when the extractor actually surfaced a new value."""
    updates: dict = {}
    for field in EvaluatorExtraction.model_fields:
        new_value = getattr(extraction, field)
        if new_value is not None:
            updates[field] = new_value
    return updates


def compute_readiness(merged_values: dict) -> tuple[bool, Optional[str]]:
    """
    merged_values: the session's slot values *after* applying this turn's updates
    (intent, major, gaming_preference, ai_workload, os_preference, brand_preference,
    budget_max).

    Returns (is_ready_to_search, next_question_to_user_or_None).
    """
    for slot in _ALWAYS_REQUIRED:
        if merged_values.get(slot) is None:
            return False, QUESTION_TEMPLATES[slot]

    intent = (merged_values.get("intent") or "").lower()
    is_university = any(keyword in intent for keyword in _UNIVERSITY_KEYWORDS)
    if is_university and merged_values.get("major") is None:
        return False, QUESTION_TEMPLATES["major"]

    if merged_values.get("gaming_preference") is None and merged_values.get("ai_workload") is None:
        return False, QUESTION_TEMPLATES["gaming_or_ai"]

    return True, None


def build_evaluator_node(structured_extractor: StructuredExtractor | None = None):
    """
    Factory so the real LLM-backed extractor can be swapped for a fake in tests.
    If structured_extractor is None, it's constructed lazily on first call
    (avoids requiring VLLM_BASE_URL to be set just to import this module).
    """

    def evaluator_node(state: LaptopSessionState) -> dict:
        extractor = structured_extractor
        if extractor is None:
            from app.llm import get_chat_llm

            extractor = get_chat_llm().with_structured_output(EvaluatorExtraction, method="function_calling")

        extraction = extractor.invoke(build_messages(state))
        slot_updates = merge_extraction(state, extraction)

        merged_values = {
            "intent": slot_updates.get("intent", state.intent),
            "major": slot_updates.get("major", state.major),
            "gaming_preference": slot_updates.get("gaming_preference", state.gaming_preference),
            "ai_workload": slot_updates.get("ai_workload", state.ai_workload),
            "os_preference": slot_updates.get("os_preference", state.os_preference),
            "brand_preference": slot_updates.get("brand_preference", state.brand_preference),
            "budget_max": slot_updates.get("budget_max", state.budget_max),
        }
        is_ready, next_question = compute_readiness(merged_values)

        conversation_history = list(state.conversation_history)
        if next_question:
            conversation_history.append({"role": "assistant", "content": next_question})

        return {
            **slot_updates,
            "is_ready_to_search": is_ready,
            "next_question_to_user": next_question,
            "conversation_history": conversation_history,
        }

    return evaluator_node
