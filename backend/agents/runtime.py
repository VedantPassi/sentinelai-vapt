from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.state import AgentState


def build_graph() -> StateGraph:
    from agents.chain_agent import run as chain_run
    from agents.cloud_agent import run as cloud_run
    from agents.container_agent import run as container_run
    from agents.graph_agent import run as graph_run
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
    graph.add_node("container", container_run)
    graph.add_node("cloud", cloud_run)
    graph.add_node("validator", validator_run)
    graph.add_node("chain", chain_run)
    graph.add_node("graph", graph_run)

    graph.set_entry_point("recon")
    graph.add_edge("recon", "planner")
    graph.add_conditional_edges(
        "planner",
        _route_by_target_type,
        {
            "webapp": "webapp",
            "network": "network",
            "container": "container",
            "cloud": "cloud",
            "end": END,
        },
    )
    graph.add_edge("webapp", "validator")
    graph.add_edge("network", "validator")
    graph.add_edge("container", "validator")
    graph.add_edge("cloud", "validator")
    graph.add_edge("validator", "chain")
    graph.add_edge("chain", "graph")
    graph.add_edge("graph", END)

    return graph


def _route_by_target_type(state: AgentState) -> str:
    t = state.get("target_type", "web")
    if t in ("web", "api"):
        return "webapp"
    if t == "network":
        return "network"
    if t == "container":
        return "container"
    if t == "cloud":
        return "cloud"
    return "end"


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


async def run_agent_scan(scan_id: str, target_url: str, target_type: str, config: dict) -> AgentState:
    from core.events import publish_scan_event_sync

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

    last_event_count = 0
    final_state: AgentState = initial

    async for chunk in get_graph().astream(initial):
        for node_state in chunk.values():
            final_state = node_state
            events = final_state.get("progress_events", [])
            for event in events[last_event_count:]:
                publish_scan_event_sync(scan_id, {
                    "node": event.node,
                    "status": event.status,
                    "message": event.message,
                    "timestamp": event.timestamp,
                })
            last_event_count = len(events)

    return final_state
