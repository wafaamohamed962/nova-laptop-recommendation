"""
Wire-format schemas for the /chat endpoint. These deliberately mirror the
frontend's TypeScript types field-for-field (frontend/src/types/chat.ts and
frontend/src/types/laptop.ts) -- Phase 6 targets the contract the frontend
was already built against, rather than the two-endpoint design in the
original spec, so nothing on the frontend needs to change.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


def _to_camel(snake: str) -> str:
    first, *rest = snake.split("_")
    return first + "".join(word.title() for word in rest)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class Laptop(CamelModel):
    id: str
    brand: str
    model: str
    cpu: str
    gpu: Optional[str] = None
    ram: str
    storage: str
    display: str
    price: float
    currency: str = "USD"
    product_url: Optional[str] = None
    image_url: Optional[str] = None


RecommendationCategory = Literal["best_overall", "budget_saver", "power_future_proof"]


class Recommendation(CamelModel):
    id: str
    category: RecommendationCategory
    laptop: Laptop
    reasoning: Optional[str] = None
    score: Optional[float] = None


MessageRole = Literal["user", "assistant", "system"]
MessageStatus = Literal["sending", "sent", "error"]


class ChatMessage(CamelModel):
    id: str
    role: MessageRole
    content: str
    timestamp: str
    status: Optional[MessageStatus] = None
    recommendations: Optional[list[Recommendation]] = None


class ChatRequest(CamelModel):
    conversation_id: Optional[str] = None
    message: str


class ChatResponse(CamelModel):
    conversation_id: str
    message: ChatMessage
    done: Optional[bool] = None
