from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.state import AgentState


def build_graph() -> StateGraph:
    from agents.chain_agent import run as chain_run
    from agents.network_agent import run as network_run
    from agents.planner_agent import run as planner_run
    from agents.recon_agent import run as recon_run
    from agents.validation_agent import run as validator_run
    from agents.webapp_agent import run as webapp_run

    graph = StateGraph(AgentState)

    graph.add_node("recon", recon_run)
    graph.add_node("planner", planner_run)
    graph.add_node("webapp", webapp_run)
    graph.add_node("network", network_run)
    graph.add_node("validator", validator_run)
    graph.add_node("chain", chain_run)

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
    graph.add_edge("webapp", "validator")
    graph.add_edge("network", "validator")
    graph.add_edge("validator", "chain")
    graph.add_edge("chain", END)

    return graph


def _route_by_target_type(state: AgentState) -> str:
    t = state.get("target_type", "web")
    if t in ("web", "api"):
        return "webapp"
    if t == "network":
        return "network"
    return "end"


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


async def run_agent_scan(scan_id: str, target_url: str, target_type: str, config: dict) -> AgentState:
    initial: AgentState = {
        "scan_id": scan_id,
        "target_url": target_url,
        "target_type": target_type,
        "config": config,
        "recon_data": None,
        "attack_plan": None,
        "findings": [],
        "attack_chains": [],
        "current_node": "start",
        "progress_events": [],
        "error": None,
    }
    return await get_graph().ainvoke(initial)
