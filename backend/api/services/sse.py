from __future__ import annotations

import json
from typing import Any


PEER_NODE_NAMES = {
    "peer_mirror_agent",
    "veteran_peer_agent",
    "Blackboard_Peer_Nam",
    "Blackboard_Peer_Linh",
    "therapist_coordinator_agent",
}


def encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def graph_update_payload(update: dict[str, Any]) -> dict[str, Any]:
    if "__done__" in update:
        payload = {"done": True}
        metadata = update.get("__metadata__")
        if isinstance(metadata, dict):
            payload.update(metadata)
        return payload

    node_name = list(update.keys())[0]
    node_data = update[node_name]
    payload: dict[str, Any] = {"node": node_name}
    if not isinstance(node_data, dict):
        return payload

    if node_name in ["Orchestrator", "Therapist_Orchestrator"]:
        payload["next_speaker"] = node_data.get("next_speaker")
        payload["therapist_plan"] = node_data.get("therapist_plan")
        payload["therapist_validator"] = node_data.get("therapist_validator")
        payload["therapist_debug"] = node_data.get("therapist_debug", {})
    elif node_name == "Clinical_Assessor":
        payload["current_stage"] = node_data.get("current_stage")
        payload["previous_stage"] = node_data.get("previous_stage")
        payload["stage_transition"] = node_data.get("stage_transition")
        payload["stage_confidence"] = node_data.get("stage_confidence")
        payload["stage_evidence"] = node_data.get("stage_evidence", [])
        payload["stage_evidence_details"] = node_data.get("stage_evidence_details", {})
        payload["stage_completion_status"] = node_data.get("stage_completion_status")
    elif node_name == "Onboarding":
        payload["ui_action"] = node_data.get("ui_action")
        payload["final_reply"] = node_data.get("final_reply", "")
        if node_data.get("final_reply"):
            payload["final_output"] = [
                {
                    "sender": "Nhà trị liệu",
                    "text": node_data.get("final_reply", ""),
                    "typing_time_ms": 800,
                }
            ]
    elif node_name in PEER_NODE_NAMES:
        payload["peer_drafts"] = node_data.get("peer_drafts", [])
        payload["peer_contribution_decisions"] = node_data.get("peer_contribution_decisions", [])
    elif node_name in ["Guardrails", "Crisis"]:
        payload["final_output"] = node_data.get("final_output", [])
        payload["final_reply"] = node_data.get("final_reply", "")
        payload["ui_action"] = node_data.get("ui_action", "NONE")
        payload["system_variant"] = node_data.get("system_variant", node_data.get("variant"))
        payload["route"] = node_data.get("therapy_route")
        payload["stage"] = node_data.get("current_stage", node_data.get("current_phase"))
        payload["peer_used"] = node_data.get("peer_used")
        payload["fallback_used"] = node_data.get("fallback_used")
    return payload
