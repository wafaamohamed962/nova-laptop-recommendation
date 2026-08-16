from app.agents.evaluator import EvaluatorExtraction


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
