from app.agents.evaluator import EvaluatorExtraction
from app.serpapi_client import SerpApiError


class FakeShoppingClient:
    """Stands in for a real ShoppingSearchClient (SerpApi).

    Give it a dict mapping query -> raw SerpApi-shaped response, or a single
    dict/exception reused for every query. Records every query it was asked
    to search, so tests can assert on call count/order.
    """

    def __init__(self, responses: dict[str, dict] | dict | None = None, error: Exception | None = None):
        self._responses = responses or {}
        self._error = error
        self.queries: list[str] = []

    def search(self, query: str) -> dict:
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        if query in self._responses:
            return self._responses[query]
        # allow a single shared response dict for every query
        if "shopping_results" in self._responses:
            return self._responses
        raise SerpApiError(f"FakeShoppingClient has no scripted response for {query!r}")


class FakeStructuredExtractor:
    """Stands in for `llm.with_structured_output(EvaluatorExtraction)`.

    Give it a list of EvaluatorExtraction objects; each .invoke() call pops the
    next one, in order, so a test can script a multi-turn conversation without
    hitting a real LLM.
    """

    def __init__(self, extractions: list[EvaluatorExtraction]):
        self._extractions = list(extractions)
        self.calls: list[list] = []

    def invoke(self, messages: list) -> EvaluatorExtraction:
        self.calls.append(messages)
        if not self._extractions:
            raise AssertionError("FakeStructuredExtractor ran out of scripted responses")
        return self._extractions.pop(0)
