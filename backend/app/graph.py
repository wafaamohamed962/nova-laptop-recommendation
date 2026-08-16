import logging
from typing import Callable, Literal

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.evaluator import StructuredExtractor, build_evaluator_node
from app.agents.hardware_architect import derive_hardware_requirements
from app.live_price_tool import ShoppingSearchClient, fetch_live_prices
from app.price_cache import PriceCache
from app.retrieval import fetch_candidates
from app.scoring import score_candidates, select_top_picks
from app.state import LaptopSessionState

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


def route_after_evaluator(state: LaptopSessionState) -> Literal["ask", "search"]:
    return "search" if state.is_ready_to_search else "ask"


def build_search_node(session_factory: SessionFactory | None = None):
    """
    Hardware Architect -> DB Retriever -> Scoring Engine, run in sequence.
    Kept as one graph node (rather than three) because the intermediate
    outputs (SQL requirements, raw candidate rows) are pipeline plumbing that
    LaptopSessionState was never meant to carry -- only the final top picks
    (`top_matched_laptops`) belong in session state.
    """

    def search_node(state: LaptopSessionState) -> dict:
        factory = session_factory
        if factory is None:
            from app.db import SessionLocal

            factory = SessionLocal

        session = factory()
        try:
            requirements = derive_hardware_requirements(state)
            candidates, relaxation_notes = fetch_candidates(session, requirements)
            for note in relaxation_notes:
                logger.info(note)
            scored = score_candidates(candidates, state)
            top_picks = select_top_picks(scored)
        finally:
            session.close()

        return {"top_matched_laptops": top_picks}

    return search_node


def build_live_price_node(
    shopping_client: ShoppingSearchClient | None = None,
    price_cache: PriceCache | None = None,
):
    """
    Phase 5: fetches live prices/sellers/ratings/links for the EXACT
    `top_matched_laptops` Phase 4 just produced. Runs immediately after
    `search` in the graph -- never as a separate/parallel workflow.
    """

    def live_price_node(state: LaptopSessionState) -> dict:
        results = fetch_live_prices(state.top_matched_laptops, shopping_client, price_cache)
        return {"live_price_results": results}

    return live_price_node


def build_graph(
    structured_extractor: StructuredExtractor | None = None,
    session_factory: SessionFactory | None = None,
    shopping_client: ShoppingSearchClient | None = None,
    price_cache: PriceCache | None = None,
):
    graph = StateGraph(LaptopSessionState)
    graph.add_node("evaluator", build_evaluator_node(structured_extractor))
    graph.add_node("search", build_search_node(session_factory))
    graph.add_node("live_price", build_live_price_node(shopping_client, price_cache))
    graph.set_entry_point("evaluator")
    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {"ask": END, "search": "search"},
    )
    graph.add_edge("search", "live_price")
    graph.add_edge("live_price", END)
    return graph.compile()


def run_turn(
    state: LaptopSessionState,
    user_message: str,
    structured_extractor: StructuredExtractor | None = None,
    session_factory: SessionFactory | None = None,
    shopping_client: ShoppingSearchClient | None = None,
    price_cache: PriceCache | None = None,
) -> LaptopSessionState:
    """Append the user's message, run one pass of the graph, return the updated session state."""
    state.add_user_message(user_message)
    compiled = build_graph(structured_extractor, session_factory, shopping_client, price_cache)
    result = compiled.invoke(state)
    if isinstance(result, LaptopSessionState):
        return result
    return LaptopSessionState.model_validate(result)
