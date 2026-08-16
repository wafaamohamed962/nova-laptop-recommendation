"""
Phase 6: FastAPI wrapper around the LangGraph workflow.

Exposes a single POST /chat endpoint matching the frontend's already-built
ChatService contract (frontend/src/api/httpChatService.ts) -- one endpoint
handling both "start a new conversation" (conversationId: null) and
"continue an existing one", rather than the original spec's separate
/api/chat/start + /api/chat/message. The frontend needed zero changes to
point at this.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api_schemas import ChatRequest, ChatResponse
from app.config import settings
from app.conversation_store import ConversationStore
from app.deps import (
    get_conversation_store,
    get_price_cache,
    get_session_factory,
    get_shopping_client,
    get_structured_extractor,
)
from app.graph import run_turn
from app.response_mapping import build_chat_response
from app.state import LaptopSessionState

app = FastAPI(title="NOVA Laptop Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    store: ConversationStore = Depends(get_conversation_store),
    structured_extractor=Depends(get_structured_extractor),
    session_factory=Depends(get_session_factory),
    shopping_client=Depends(get_shopping_client),
    price_cache=Depends(get_price_cache),
) -> ChatResponse:
    if request.conversation_id is None:
        conversation_id, state = store.create()
    else:
        conversation_id = request.conversation_id
        state = store.get(conversation_id)
        if state is None:
            # The store is in-memory only (see conversation_store.py) and can be
            # wiped by a server restart. Rather than force the client to detect
            # a 404 and manually start over, transparently recover a fresh
            # session under the same conversationId it already has.
            state = LaptopSessionState()

    try:
        state = run_turn(
            state,
            request.message,
            structured_extractor=structured_extractor,
            session_factory=session_factory,
            shopping_client=shopping_client,
            price_cache=price_cache,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {exc}") from exc

    store.save(conversation_id, state)
    return build_chat_response(conversation_id, state)
