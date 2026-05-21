from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ai_engine.agents.clinical_assessor_node import clinical_assessor_node
from ai_engine.agents.guardrails_node import guardrails_node
from ai_engine.agents.onboarding_agent import onboarding_node
from ai_engine.agents.orchestrator_node import orchestrator_node
from ai_engine.agents.personas.peer_mirror_agent import peer_mirror_agent
from ai_engine.agents.personas.veteran_peer_agent import veteran_peer_agent
from ai_engine.blackboard.state import GroupTherapyState
from ai_engine.graph.nodes import (
    crisis_node,
    make_onboarding_router,
    memory_updater_node,
    single_agent_plain_node,
    single_agent_stage_prompt_node,
)
from ai_engine.graph.variants import SystemVariant, normalize_system_variant


def build_graph(system_variant: str | SystemVariant = SystemVariant.OURS_FULL) -> StateGraph:
    variant = normalize_system_variant(system_variant)
    graph = StateGraph(GroupTherapyState)

    graph.add_node("Onboarding", onboarding_node)
    graph.add_node("Guardrails", guardrails_node)
    graph.add_node("Crisis", crisis_node)
    graph.add_node("MemoryUpdater", memory_updater_node)

    graph.set_entry_point("Onboarding")

    if variant == SystemVariant.SINGLE_AGENT_PLAIN:
        graph.add_node("Single_Agent_Plain", single_agent_plain_node)
        graph.add_conditional_edges("Onboarding", make_onboarding_router("Single_Agent_Plain"))
        graph.add_edge("Single_Agent_Plain", "Guardrails")
    elif variant == SystemVariant.SINGLE_AGENT_STAGE_PROMPT:
        graph.add_node("Clinical_Assessor", clinical_assessor_node)
        graph.add_node("Single_Agent_Stage", single_agent_stage_prompt_node)
        graph.add_conditional_edges("Onboarding", make_onboarding_router("Clinical_Assessor"))
        graph.add_edge("Clinical_Assessor", "Single_Agent_Stage")
        graph.add_edge("Single_Agent_Stage", "Guardrails")
    elif variant == SystemVariant.OURS_NO_PEER:
        graph.add_node("Clinical_Assessor", clinical_assessor_node)
        graph.add_node("Therapist_Orchestrator", orchestrator_node)
        graph.add_conditional_edges("Onboarding", make_onboarding_router("Clinical_Assessor"))
        graph.add_edge("Clinical_Assessor", "Therapist_Orchestrator")
        graph.add_edge("Therapist_Orchestrator", "Guardrails")
    else:
        graph.add_node("Clinical_Assessor", clinical_assessor_node)
        graph.add_node("Blackboard_Peer_Nam", peer_mirror_agent)
        graph.add_node("Blackboard_Peer_Linh", veteran_peer_agent)
        graph.add_node("Therapist_Orchestrator", orchestrator_node)
        graph.add_conditional_edges("Onboarding", make_onboarding_router("Clinical_Assessor"))
        graph.add_edge("Clinical_Assessor", "Blackboard_Peer_Nam")
        graph.add_edge("Clinical_Assessor", "Blackboard_Peer_Linh")
        graph.add_edge("Blackboard_Peer_Nam", "Therapist_Orchestrator")
        graph.add_edge("Blackboard_Peer_Linh", "Therapist_Orchestrator")
        graph.add_edge("Therapist_Orchestrator", "Guardrails")

    graph.add_edge("Guardrails", "MemoryUpdater")
    graph.add_edge("Crisis", "MemoryUpdater")
    graph.add_edge("MemoryUpdater", END)
    return graph


builder = build_graph()
hospital_app = builder.compile(checkpointer=MemorySaver())
