"""
FastAPI dependency providers. Each one returns None by default, which is the
signal run_turn/build_graph already use to mean "construct the real thing
lazily" (real LLM, real DB session, real SerpApi client). Tests override
these via app.dependency_overrides to inject fakes instead.
"""

from app.conversation_store import ConversationStore

_default_store = ConversationStore()


def get_conversation_store() -> ConversationStore:
    return _default_store


def get_structured_extractor():
    return None


def get_session_factory():
    return None


def get_shopping_client():
    return None


def get_price_cache():
    return None
