"""
Thin wrapper over SerpApi's Google Shopping engine. Isolated in its own
module so it's trivial to mock in tests (nothing else in this file touches
the network).
"""

import requests

from app.config import settings

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
# 10s was too tight -- confirmed live, sporadic read timeouts on real
# shopping queries that otherwise succeed given a bit more time.
REQUEST_TIMEOUT_SECONDS = 25


class SerpApiError(RuntimeError):
    pass


def search_google_shopping(query: str, num_results: int = 5) -> dict:
    api_key = settings.serpapi_api_key
    if not api_key:
        raise SerpApiError(
            "SERPAPI_API_KEY must be set (see backend/.env.example) before live "
            "prices can be fetched."
        )

    try:
        response = requests.get(
            SERPAPI_ENDPOINT,
            params={
                "engine": "google_shopping",
                "q": query,
                "api_key": api_key,
                "num": num_results,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        # SerpApi puts the actual reason (invalid param, bad key, etc.) in
        # the JSON response body -- the bare HTTPError str only has the
        # status code, which hides it.
        try:
            detail = exc.response.json().get("error", exc.response.text)
        except ValueError:
            detail = exc.response.text
        raise SerpApiError(f"SerpApi request failed for query {query!r}: {detail}") from exc
    except requests.RequestException as exc:
        raise SerpApiError(f"SerpApi request failed for query {query!r}: {exc}") from exc

    return response.json()
