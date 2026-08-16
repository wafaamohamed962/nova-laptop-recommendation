import pytest
from fastapi.testclient import TestClient

from app.agents.evaluator import EvaluatorExtraction
from app.conversation_store import ConversationStore
from app.deps import (
    get_conversation_store,
    get_price_cache,
    get_session_factory,
    get_shopping_client,
    get_structured_extractor,
)
from app.main import app
from tests.conftest import make_laptop, make_session_factory
from tests.fakes import FakeShoppingClient, FakeStructuredExtractor


@pytest.fixture
def client():
    test_client = TestClient(app)
    store = ConversationStore()  # same instance must persist across requests within a test
    app.dependency_overrides[get_conversation_store] = lambda: store
    yield test_client
    app.dependency_overrides.clear()


def _sample_session_factory():
    return make_session_factory(
        [
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=6.0, cpu_ghz=3.5),
            make_laptop(os="Windows", ram_gb=32, has_dedicated_gpu=True, gpu_vram_gb=8.0, cpu_ghz=4.2),
            make_laptop(os="Windows", ram_gb=8, has_dedicated_gpu=False, cpu_ghz=2.0),
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=4.0, cpu_ghz=3.0),
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=4.0, cpu_ghz=2.8),
            make_laptop(os="Windows", ram_gb=24, has_dedicated_gpu=True, gpu_vram_gb=6.0, cpu_ghz=3.2),
            make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=8.0, cpu_ghz=3.6),
            make_laptop(os="Windows", ram_gb=32, has_dedicated_gpu=True, gpu_vram_gb=12.0, cpu_ghz=4.5),
        ]
    )


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_new_conversation_asks_clarifying_question(client):
    app.dependency_overrides[get_structured_extractor] = lambda: FakeStructuredExtractor(
        [EvaluatorExtraction(intent="gaming")]
    )

    response = client.post("/chat", json={"conversationId": None, "message": "I want a gaming laptop"})

    assert response.status_code == 200
    body = response.json()
    assert body["conversationId"]
    assert body["done"] is False
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"]
    assert body["message"]["recommendations"] is None


def test_chat_unknown_conversation_id_recovers_a_fresh_session(client):
    """
    The conversation store is in-memory only and can be wiped by a server
    restart. A client holding a now-unknown conversationId (e.g. after a
    dev-server reload) should transparently get a fresh session under that
    same id, not a 404 it has to manually recover from.
    """
    app.dependency_overrides[get_structured_extractor] = lambda: FakeStructuredExtractor(
        [EvaluatorExtraction(intent="gaming")]
    )

    response = client.post("/chat", json={"conversationId": "stale-id-from-before-restart", "message": "hi"})

    assert response.status_code == 200
    assert response.json()["conversationId"] == "stale-id-from-before-restart"
    assert response.json()["done"] is False


def test_chat_continues_conversation_across_turns(client):
    extractor1 = FakeStructuredExtractor([EvaluatorExtraction(intent="gaming")])
    app.dependency_overrides[get_structured_extractor] = lambda: extractor1
    first = client.post("/chat", json={"conversationId": None, "message": "I want a gaming laptop"})
    conversation_id = first.json()["conversationId"]

    extractor2 = FakeStructuredExtractor([EvaluatorExtraction(budget_max=1500)])
    app.dependency_overrides[get_structured_extractor] = lambda: extractor2
    second = client.post("/chat", json={"conversationId": conversation_id, "message": "budget is 1500"})

    assert second.status_code == 200
    assert second.json()["conversationId"] == conversation_id
    assert second.json()["done"] is False


def test_chat_full_flow_returns_priced_recommendations(client, tmp_path):
    from app.price_cache import PriceCache

    session_factory = _sample_session_factory()
    shopping_client = FakeShoppingClient(
        {
            "shopping_results": [
                {"title": "Test Listing", "source": "Best Buy", "extracted_price": 1299.0, "rating": 4.5}
            ]
        }
    )
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_shopping_client] = lambda: shopping_client
    app.dependency_overrides[get_price_cache] = lambda: PriceCache(path=tmp_path / "cache.json")

    extractor1 = FakeStructuredExtractor([EvaluatorExtraction(intent="gaming")])
    app.dependency_overrides[get_structured_extractor] = lambda: extractor1
    first = client.post("/chat", json={"conversationId": None, "message": "gaming laptop"})
    conversation_id = first.json()["conversationId"]

    extractor2 = FakeStructuredExtractor([EvaluatorExtraction(budget_max=1500)])
    app.dependency_overrides[get_structured_extractor] = lambda: extractor2
    second = client.post("/chat", json={"conversationId": conversation_id, "message": "budget 1500"})

    extractor3 = FakeStructuredExtractor([EvaluatorExtraction(brand_preference="no preference")])
    app.dependency_overrides[get_structured_extractor] = lambda: extractor3
    third = client.post("/chat", json={"conversationId": conversation_id, "message": "no brand preference"})

    extractor4 = FakeStructuredExtractor(
        [EvaluatorExtraction(gaming_preference="AAA", os_preference="Windows")]
    )
    app.dependency_overrides[get_structured_extractor] = lambda: extractor4
    fourth = client.post("/chat", json={"conversationId": conversation_id, "message": "AAA, Windows"})

    assert fourth.status_code == 200
    body = fourth.json()
    assert body["done"] is True
    recommendations = body["message"]["recommendations"]
    assert recommendations is not None
    assert len(recommendations) >= 5  # "at least 5 results"
    for rec in recommendations:
        assert rec["category"] in ("best_overall", "budget_saver", "power_future_proof")
        laptop = rec["laptop"]
        assert laptop["price"] == 1299.0
        assert isinstance(laptop["ram"], str)
        assert "reasoning" in rec


def test_chat_backend_failure_returns_500_not_a_crash(client):
    class BoomExtractor:
        def invoke(self, messages):
            raise RuntimeError("simulated LLM outage")

    app.dependency_overrides[get_structured_extractor] = lambda: BoomExtractor()

    response = client.post("/chat", json={"conversationId": None, "message": "hi"})

    assert response.status_code == 500
    assert "simulated LLM outage" in response.json()["detail"]
