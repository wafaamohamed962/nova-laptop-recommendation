"""
In-memory conversation session store, keyed by conversation id.

Deliberately simple: a single dict guarded by nothing more than Python's GIL,
sessions lost on process restart. That's an acceptable tradeoff for this
project's current scope (single-process dev/demo deployment); swapping in a
Redis- or DB-backed store later wouldn't need to change ConversationStore's
interface, just its implementation.
"""

import uuid

from app.state import LaptopSessionState


class ConversationStore:
    def __init__(self):
        self._sessions: dict[str, LaptopSessionState] = {}

    def create(self) -> tuple[str, LaptopSessionState]:
        conversation_id = str(uuid.uuid4())
        state = LaptopSessionState()
        self._sessions[conversation_id] = state
        return conversation_id, state

    def get(self, conversation_id: str) -> LaptopSessionState | None:
        return self._sessions.get(conversation_id)

    def save(self, conversation_id: str, state: LaptopSessionState) -> None:
        self._sessions[conversation_id] = state
