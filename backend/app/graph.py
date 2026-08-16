from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.evaluator import StructuredExtractor, build_evaluator_node
from app.state import LaptopSessionState


def route_after_evaluator(state: LaptopSessionState) -> Literal["ask", "search"]:
    return "search" if state.is_ready_to_search else "ask"


def ready_for_search_node(state: LaptopSessionState) -> dict:
    """
    Placeholder terminal node. Phase 4 replaces this with the Hardware Architect
    -> DB Retriever -> Scoring Engine pipeline; the graph wiring (the conditional
    edge into this node) does not need to change when that lands.
    """
    return {}


def build_graph(structured_extractor: StructuredExtractor | None = None):
    graph = StateGraph(LaptopSessionState)
    graph.add_node("evaluator", build_evaluator_node(structured_extractor))
    graph.add_node("ready_for_search", ready_for_search_node)
    graph.set_entry_point("evaluator")
    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {"ask": END, "search": "ready_for_search"},
    )
    graph.add_edge("ready_for_search", END)
    return graph.compile()


def run_turn(
    state: LaptopSessionState,
    user_message: str,
    structured_extractor: StructuredExtractor | None = None,
) -> LaptopSessionState:
    """Append the user's message, run one pass of the graph, return the updated session state."""
    state.add_user_message(user_message)
    compiled = build_graph(structured_extractor)
    result = compiled.invoke(state)
    if isinstance(result, LaptopSessionState):
        return result
    return LaptopSessionState.model_validate(result)
