from __future__ import annotations

from typing import Annotated, Any, Dict, List, TypedDict


def merge_lists(left: list, right: Any) -> list:
    if right == "CLEAR" or right is None:
        return []
    if not left:
        left = []
    if not right:
        right = []
    if isinstance(right, list):
        return left + right
    return left + [right]


def merge_drafts(left: list, right: Any) -> list:
    # Legacy reducer kept for old modules while blackboard uses peer_drafts.
    return merge_lists(left, right)


class GroupTherapyState(TypedDict, total=False):
    chat_history: str
    user_message: str
    user_name: str
    user_id: str
    selected_model: str
    system_variant: str
    variant: str
    peer_enabled: bool
    validator_enabled: bool
    safety_critic_enabled: bool
    fallback_used: bool
    latency_ms: float
    last_peer_sender: str
    consecutive_peer_turns: int
    peer_silence_cooldown: int

    # Onboarding / frontend control.
    onboarding_status: str
    assessment: dict
    ui_action: str

    # Routing / clinical protocol.
    risk_level: str
    therapy_route: str
    active_protocol: dict

    # Canonical blackboard state.
    clinical_summary: str
    previous_stage: str
    current_stage: str
    stage_goal: str
    clinical_stage_number: int
    stage_confidence: float
    stage_evidence: List[str]
    stage_evidence_details: Dict[str, Any]
    stage_transition: str
    stage_transition_reason: str
    stage_completion_status: str
    cbt_milestones: Dict[str, Any]
    required_yalom_factors: List[str]
    peer_drafts: Annotated[list, merge_lists]
    peer_contribution_decisions: Annotated[list, merge_lists]
    therapist_plan: str
    structured_therapist_plan: Dict[str, Any]
    therapist_validator: Dict[str, Any]
    therapist_debug: Dict[str, Any]
    case_formulation: Dict[str, Any]
    psychosocial_safety: Dict[str, Any]
    safety_flags: Dict[str, Any]

    # Output.
    final_output: List[Dict[str, Any]]
    final_reply: str

    # Compatibility fields scheduled for deletion after callers migrate.
    current_phase: str
    stage_goal_description: str
    peer_turn_count: int
    doctor_action: str
    moderator_reason: str
    intent: str
    cognitive_distortion: str
    sub_style: str
    next_speaker: str
    drafts: Annotated[list, merge_drafts]


HospitalState = GroupTherapyState
