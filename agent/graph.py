from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from agent.nodes import (
    retrieve_chunks,
    should_use_fallback,
    fallback_to_abstract,
    generate_explanation,
)
from shared.models import Chunk


class AgentState(TypedDict):
    paper_id: str
    abstract: str
    chunks: List[Chunk]
    context: str
    used_fallback: bool
    explanation: str
    error: Optional[str]
    rate_limited: bool
    retry_after_seconds: Optional[int]


def _build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_chunks)
    graph.add_node("fallback", fallback_to_abstract)
    graph.add_node("generate", generate_explanation)

    graph.set_entry_point("retrieve")

    graph.add_conditional_edges(
        "retrieve",
        should_use_fallback,
        {
            "generate": "generate",
            "fallback": "fallback",
        },
    )
    graph.add_edge("fallback", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


_compiled_graph = _build_graph()


def run_agent(paper_id: str, abstract: str) -> dict:
    initial_state: AgentState = {
        "paper_id": paper_id,
        "abstract": abstract,
        "chunks": [],
        "context": "",
        "used_fallback": False,
        "explanation": "",
        "error": None,
        "rate_limited": False,
        "retry_after_seconds": None,
    }

    try:
        return _compiled_graph.invoke(initial_state)
    except Exception as e:
        return {
            **initial_state,
            "explanation": (
                "⚠️ Something went wrong running the analysis. "
                "Please try again in a moment."
            ),
            "error": str(e),
        }