"""
Shared persona classification: what kind of user this session seems to be,
based on major/intent/gaming/AI signals. Used by both app/scoring.py
(dimension weighting -- which specs matter more) and app/response_mapping.py
(reasoning text -- explaining *why* in words), so the explanation a user
sees is always consistent with the score that actually picked the laptop.
"""

from typing import Literal

from app.state import LaptopSessionState

Persona = Literal["ai_workload", "gaming_aaa", "gaming_casual", "performance", "portability", "general"]

PERFORMANCE_MAJOR_KEYWORDS = (
    "computer science",
    "software",
    "engineering",
    "data science",
    "artificial intelligence",
    "machine learning",
    "information technology",
    "programmer",
    "programming",
    "developer",
)
PORTABILITY_MAJOR_KEYWORDS = (
    "medicine",
    "medical",
    "nursing",
    "business",
    "law",
    "arts",
    "humanities",
    "design",
    "journalism",
    "education",
)


def classify_persona(state: LaptopSessionState) -> Persona:
    if state.ai_workload:
        return "ai_workload"
    if state.gaming_preference == "AAA":
        return "gaming_aaa"
    if state.gaming_preference == "casual":
        return "gaming_casual"

    text = f"{state.major or ''} {state.intent or ''}".lower()
    if any(keyword in text for keyword in PERFORMANCE_MAJOR_KEYWORDS):
        return "performance"
    if any(keyword in text for keyword in PORTABILITY_MAJOR_KEYWORDS):
        return "portability"
    return "general"
