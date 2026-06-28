from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.state import AgentState


def build_graph() -> StateGraph:
    from agents.network_agent import run as network_run
    from agents.planner_agent import run as planner_run
    from agents.recon_agent import run as recon_run
    from agents.webapp_agent import run as webapp_run

    graph = StateGraph(AgentState)

    graph.add_node("recon", recon_run)
    graph.add_node("planner", planner_run)
    graph.add_node("webapp", webapp_run)
    graph.add_node("network", network_run)

    graph.set_entry_point("recon")
    graph.add_edge("recon", "planner")
    graph.add_conditional_edges(
        "planner",
        _route_by_target_type,
        {
            "webapp": "webapp",
            "network": "network",
            "end": END,
        },
    )
    graph.add_edge("webapp", END)
    graph.add_edge("network", END)

    return graph


def _route_by_target_type(state: AgentState) -> str:
    t = state.get("target_type", "web")
    if t in ("web", "api"):
        return "webapp"
    if t == "network":
        return "network"
    return "end"


compiled_graph = build_graph().compile()
