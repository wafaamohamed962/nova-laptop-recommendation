"""
Phase 5 — Live Price Tool.

Takes the top-matched laptops Phase 4 already selected (`top_matched_laptops`,
produced by app.scoring.select_top_picks) and enriches each one with live
titles, prices, sellers, ratings, and product links from SerpApi Google Shopping,
caching successful lookups locally for 24h. This module does not select or
re-rank laptops -- it only looks up prices for laptops someone else already
chose. Budget enforcement (excluding anything over budget) happens downstream
in app/response_mapping.py, once these live prices are known.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional, Protocol

from app.price_cache import PriceCache
from app.price_schemas import LivePriceResult, PriceListing
from app.serpapi_client import SerpApiError, search_google_shopping

logger = logging.getLogger(__name__)

# `model_name` in the catalog is the raw scraped listing title, e.g.
# "MSI Titan 18 HX A14VHG-207IN Laptop (18 Inch | Core i9 14th Gen | 64 GB |
# Windows 11 | 2 TB SSD)" -- everything from " Laptop (" onward is a spec
# dump, not part of the product name. Left in, it produces a huge query with
# literal "|" characters that SerpApi rejects outright with a 400.
_SPEC_DUMP_RE = re.compile(r"\s+Laptop\s*\(.*$", re.IGNORECASE)


class ShoppingSearchClient(Protocol):
    """Anything with .search(query) -> raw SerpApi JSON dict. Real impl:
    SerpApiShoppingClient; tests use a hand-built fake."""

    def search(self, query: str) -> dict: ...


class SerpApiShoppingClient:
    def search(self, query: str) -> dict:
        return search_google_shopping(query)


def build_query(laptop: dict) -> str:
    brand = (laptop.get("brand") or "").strip()
    model_name = (laptop.get("model_name") or "").strip()
    clean_model = _SPEC_DUMP_RE.sub("", model_name).strip()

    # model_name already starts with the brand name in this catalog -- only
    # prepend brand if it doesn't, rather than always duplicating it.
    if brand and clean_model.lower().startswith(brand.lower()):
        return clean_model
    return f"{brand} {clean_model}".strip()


def _normalize(raw: dict, limit: int = 5) -> list[PriceListing]:
    listings = []
    for item in (raw.get("shopping_results") or [])[:limit]:
        extracted_price = item.get("extracted_price")
        listings.append(
            PriceListing(
                title=item.get("title"),
                seller=item.get("source") or "Unknown seller",
                price=float(extracted_price) if isinstance(extracted_price, (int, float)) else None,
                currency=item.get("currency") or "USD",
                rating=item.get("rating"),
                reviews_count=item.get("reviews"),
                product_link=item.get("product_link") or item.get("link"),
            )
        )
    return listings


def fetch_price_for_laptop(
    laptop: dict,
    client: ShoppingSearchClient,
    cache: PriceCache,
) -> LivePriceResult:
    query = build_query(laptop)
    laptop_id: Optional[int] = laptop.get("id")
    brand = laptop.get("brand", "")
    model_name = laptop.get("model_name", "")

    cached = cache.get(query)
    if cached is not None:
        return LivePriceResult.model_validate({**cached, "from_cache": True})

    try:
        raw = client.search(query)
    except SerpApiError as exc:
        logger.warning("Live price lookup failed for %r: %s", query, exc)
        return LivePriceResult(
            laptop_id=laptop_id,
            brand=brand,
            model_name=model_name,
            query=query,
            listings=[],
            fetched_at=datetime.now(timezone.utc),
            from_cache=False,
            error=str(exc),
        )

    result = LivePriceResult(
        laptop_id=laptop_id,
        brand=brand,
        model_name=model_name,
        query=query,
        listings=_normalize(raw),
        fetched_at=datetime.now(timezone.utc),
        from_cache=False,
    )
    # Only cache successes -- a transient failure should be retried next turn,
    # not stuck showing an error for the full 24h TTL.
    cache.set(query, result.model_dump(mode="json"))
    return result


def fetch_live_prices(
    top_matched_laptops: list[dict],
    client: Optional[ShoppingSearchClient] = None,
    cache: Optional[PriceCache] = None,
) -> list[dict]:
    active_client = client or SerpApiShoppingClient()
    active_cache = cache or PriceCache()

    results = [
        fetch_price_for_laptop(laptop, active_client, active_cache) for laptop in top_matched_laptops
    ]
    return [r.model_dump(mode="json") for r in results]
