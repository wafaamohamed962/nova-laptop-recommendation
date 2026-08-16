"""
Local smoke test for the deployed Modal vLLM server.

Verifies:
  1. The OpenAI-compatible endpoint responds to a plain chat completion.
  2. The endpoint can produce JSON that validates against a Pydantic model,
     using vLLM's guided-decoding (`extra_body={"guided_json": ...}`) --
     this is the same mechanism the Evaluator Agent will use in Phase 3
     to extract structured slots (intent, budget, etc.) from user messages.

Usage:
    1. Deploy the server: modal deploy deploy_modal.py
    2. Copy .env.example to .env and fill in VLLM_BASE_URL / VLLM_API_KEY
    3. python test_modal_client.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

BASE_URL = os.environ.get("VLLM_BASE_URL")
API_KEY = os.environ.get("VLLM_API_KEY")
MODEL_NAME = os.environ.get("VLLM_SERVED_MODEL_NAME", "qwen2.5-7b-instruct")


class ExtractedLaptopSlots(BaseModel):
    """Mirrors the kind of structured extraction the Evaluator Agent will do."""

    intent: str = Field(description="One of: university, gaming, work, general")
    budget_max: float | None = Field(default=None, description="Max budget in USD, if mentioned")
    needs_dedicated_gpu: bool = Field(description="True if the user implies gaming/AI/rendering needs")


def check_env() -> None:
    missing = [name for name, val in [("VLLM_BASE_URL", BASE_URL), ("VLLM_API_KEY", API_KEY)] if not val]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}. Copy .env.example to .env and fill it in.")
        sys.exit(1)


def test_plain_chat(client: OpenAI) -> None:
    print("\n--- Test 1: Plain chat completion ---")
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a concise laptop shopping assistant."},
            {"role": "user", "content": "In one sentence, what matters most when choosing a laptop for gaming?"},
        ],
        max_tokens=100,
        temperature=0.3,
    )
    content = response.choices[0].message.content
    print(f"Response: {content}")
    assert content and len(content.strip()) > 0, "Empty response from model"
    print("PASSED")


def test_structured_json(client: OpenAI) -> None:
    print("\n--- Test 2: Structured JSON extraction (Pydantic-validated) ---")
    user_message = "I'm a CS major and I want to play some AAA games too, budget around $1500."

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "Extract laptop shopping requirements from the user's message as JSON.",
            },
            {"role": "user", "content": user_message},
        ],
        max_tokens=200,
        temperature=0.0,
        extra_body={"guided_json": ExtractedLaptopSlots.model_json_schema()},
    )
    raw_content = response.choices[0].message.content
    print(f"Raw JSON: {raw_content}")

    parsed = ExtractedLaptopSlots.model_validate_json(raw_content)
    print(f"Validated Pydantic object: {parsed}")

    assert parsed.needs_dedicated_gpu is True, "Expected GPU need to be inferred from 'AAA games'"
    assert parsed.budget_max == 1500, f"Expected budget_max=1500, got {parsed.budget_max}"
    print("PASSED")


def main() -> None:
    check_env()
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    test_plain_chat(client)
    test_structured_json(client)
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
