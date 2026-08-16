import pytest
import requests

from app.config import settings
from app.live_price_tool import build_query, fetch_live_prices, fetch_price_for_laptop, _normalize
from app.price_cache import PriceCache
from app.serpapi_client import SERPAPI_ENDPOINT, SerpApiError, search_google_shopping
from tests.fakes import FakeShoppingClient

SAMPLE_SERPAPI_RESPONSE = {
    "shopping_results": [
        {
            "title": "ASUS ROG Zephyrus G14",
            "source": "Best Buy",
            "price": "$1,899.00",
            "extracted_price": 1899.0,
            "rating": 4.7,
            "reviews": 342,
            "product_link": "https://example.com/product/1",
        },
        {
            "title": "ASUS ROG Zephyrus G14 (Amazon)",
            "source": "Amazon.com",
            "extracted_price": 1849.99,
            "rating": 4.5,
            "reviews": 1200,
            "link": "https://example.com/product/2",
        },
    ]
}


def _laptop(**overrides) -> dict:
    defaults = dict(id=1, brand="ASUS", model_name="ROG Zephyrus G14")
    defaults.update(overrides)
    return defaults


def test_normalize_maps_serpapi_fields_onto_price_listing():
    listings = _normalize(SAMPLE_SERPAPI_RESPONSE)

    assert len(listings) == 2
    assert listings[0].title == "ASUS ROG Zephyrus G14"
    assert listings[0].seller == "Best Buy"
    assert listings[0].price == 1899.0
    assert listings[0].rating == 4.7
    assert listings[0].reviews_count == 342
    assert listings[0].product_link == "https://example.com/product/1"
    # second item has no product_link, falls back to "link"
    assert listings[1].product_link == "https://example.com/product/2"


def test_normalize_extracts_product_title():
    """Dedicated test for the SerpApi `title` -> PriceListing.title mapping."""
    raw = {
        "shopping_results": [
            {
                "title": "ASUS ROG Zephyrus G14 (2024, Ryzen 9, RTX 4070)",
                "source": "Newegg",
                "extracted_price": 1799.0,
            },
            {
                # no "title" key at all -- should normalize to None, not KeyError
                "source": "Micro Center",
                "extracted_price": 1750.0,
            },
        ]
    }

    listings = _normalize(raw)

    assert listings[0].title == "ASUS ROG Zephyrus G14 (2024, Ryzen 9, RTX 4070)"
    assert listings[1].title is None


def test_build_query_formats_brand_and_model():
    assert build_query(_laptop(brand="ASUS", model_name="ROG Zephyrus G14")) == "ASUS ROG Zephyrus G14"


def test_build_query_strips_spec_dump_and_avoids_duplicate_brand():
    """Reproduces a real observed bug: the raw catalog model_name already
    starts with the brand and ends with a huge '| '-delimited spec dump,
    which SerpApi rejects with a 400. The query must be short and clean."""
    laptop = _laptop(
        brand="MSI",
        model_name=(
            "MSI Titan 18 HX A14VHG-207IN Laptop "
            "(18 Inch | Core i9 14th Gen | 64 GB | Windows 11 | 2 TB SSD)"
        ),
    )

    query = build_query(laptop)

    assert query == "MSI Titan 18 HX A14VHG-207IN"
    assert "|" not in query
    assert query.count("MSI") == 1


def test_build_query_keeps_sku_parenthetical_but_drops_spec_dump():
    laptop = _laptop(
        brand="HP",
        model_name="HP Chromebook 11A-NA0002MU (2E4N0PA) Laptop (11.6 Inch | MediaTek Octa Core | 4 GB)",
    )

    query = build_query(laptop)

    assert query == "HP Chromebook 11A-NA0002MU (2E4N0PA)"


def test_fetch_price_for_laptop_uses_cache_on_second_call(tmp_path):
    laptop = _laptop()
    client = FakeShoppingClient(SAMPLE_SERPAPI_RESPONSE)
    cache = PriceCache(path=tmp_path / "cache.json")

    first = fetch_price_for_laptop(laptop, client, cache)
    second = fetch_price_for_laptop(laptop, client, cache)

    assert len(client.queries) == 1  # second call served entirely from cache
    assert first.from_cache is False
    assert second.from_cache is True
    assert [listing.seller for listing in second.listings] == [listing.seller for listing in first.listings]


def test_price_cache_entry_expires(tmp_path):
    cache = PriceCache(path=tmp_path / "cache.json", ttl_seconds=0)
    cache.set("some query", {"foo": "bar"})

    assert cache.get("some query") is None


def test_fetch_price_for_laptop_returns_error_result_without_raising(tmp_path):
    laptop = _laptop(id=2, brand="MSI", model_name="Raider GE78HX")
    client = FakeShoppingClient(error=SerpApiError("SerpApi is down"))
    cache = PriceCache(path=tmp_path / "cache.json")

    result = fetch_price_for_laptop(laptop, client, cache)

    assert result.error == "SerpApi is down"
    assert result.listings == []
    assert cache.get(build_query(laptop)) is None  # failures are not cached


def test_fetch_live_prices_returns_one_result_per_laptop_in_order(tmp_path):
    laptops = [
        _laptop(id=1, brand="ASUS", model_name="A"),
        _laptop(id=2, brand="MSI", model_name="B"),
    ]
    client = FakeShoppingClient({"shopping_results": []})
    cache = PriceCache(path=tmp_path / "cache.json")

    results = fetch_live_prices(laptops, client=client, cache=cache)

    assert [r["laptop_id"] for r in results] == [1, 2]
    assert [r["model_name"] for r in results] == ["A", "B"]


def test_search_google_shopping_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", None)

    def _unexpected_call(*args, **kwargs):
        raise AssertionError("requests.get should not be called without an API key")

    monkeypatch.setattr("app.serpapi_client.requests.get", _unexpected_call)

    with pytest.raises(SerpApiError):
        search_google_shopping("test query")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeErrorResponse:
    """Simulates a real requests.Response that fails raise_for_status(),
    carrying a body SerpApi would actually send back (JSON error detail,
    or occasionally plain text)."""

    def __init__(self, status_code: int, json_body: dict | None = None, text_body: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text_body

    def raise_for_status(self):
        error = requests.HTTPError(f"{self.status_code} Client Error")
        error.response = self
        raise error

    def json(self):
        if self._json_body is None:
            raise ValueError("response body is not JSON")
        return self._json_body


def test_search_google_shopping_calls_serpapi_with_expected_params(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    captured = {}

    def _fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return _FakeResponse({"shopping_results": []})

    monkeypatch.setattr("app.serpapi_client.requests.get", _fake_get)

    result = search_google_shopping("ASUS ROG Zephyrus G14")

    assert captured["url"] == SERPAPI_ENDPOINT
    assert captured["params"]["engine"] == "google_shopping"
    assert captured["params"]["q"] == "ASUS ROG Zephyrus G14"
    assert captured["params"]["api_key"] == "test-key"
    assert captured["timeout"] == 25  # bumped from 10s: sporadic real-world read timeouts
    assert result == {"shopping_results": []}


def test_search_google_shopping_surfaces_real_error_detail_from_json_body(monkeypatch):
    """The bare HTTPError str only has the status code; the actual reason
    SerpApi rejected the request lives in the JSON body and must not be
    swallowed."""
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")

    def _fake_get(url, params, timeout):
        return _FakeErrorResponse(400, json_body={"error": "some SerpApi-specific error"})

    monkeypatch.setattr("app.serpapi_client.requests.get", _fake_get)

    with pytest.raises(SerpApiError, match="some SerpApi-specific error"):
        search_google_shopping("query")


def test_search_google_shopping_falls_back_to_response_text_when_not_json(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")

    def _fake_get(url, params, timeout):
        return _FakeErrorResponse(400, json_body=None, text_body="Bad Request")

    monkeypatch.setattr("app.serpapi_client.requests.get", _fake_get)

    with pytest.raises(SerpApiError, match="Bad Request"):
        search_google_shopping("query")


def test_search_google_shopping_wraps_network_errors(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("app.serpapi_client.requests.get", _raise)

    with pytest.raises(SerpApiError):
        search_google_shopping("query")
