from typing import Literal, Optional

from pydantic import BaseModel, Field

GamingPreference = Literal["AAA", "casual", "none"]
OsPreference = Literal["Windows", "macOS", "Linux", "no preference"]


class LaptopSessionState(BaseModel):
    conversation_history: list[dict] = Field(default_factory=list)
    intent: Optional[str] = None  # e.g., "university", "gaming", "work"
    major: Optional[str] = None  # e.g., "Computer Science", "Medicine"
    gaming_preference: Optional[GamingPreference] = None
    ai_workload: Optional[bool] = None  # True if user needs to run local LLMs
    os_preference: Optional[OsPreference] = None
    budget_max: Optional[float] = None  # e.g., 1200.0
    is_ready_to_search: bool = False
    next_question_to_user: Optional[str] = None
    top_matched_laptops: list[dict] = Field(default_factory=list)
    final_recommendation_markdown: Optional[str] = None

    def add_user_message(self, content: str) -> None:
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.conversation_history.append({"role": "assistant", "content": content})
