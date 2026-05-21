import json
import logging

from ai_engine.state import GroupTherapyState
from ai_engine.services.llm_service import FAST_MODEL, generate_text_async
from ai_engine.blackboard.yalom_persona_contract import validate_peer_contribution
from ai_engine.agents.personas.blackboard_peer import (
    PeerContribution,
    contribution_update,
    no_contribution,
    parse_peer_contribution,
)
from ai_engine.runtime import _PROMPTS, _render

logger = logging.getLogger(__name__)

async def veteran_peer_agent(state: GroupTherapyState) -> GroupTherapyState:
    required_factors = state.get("required_yalom_factors", ["NONE"])
    LINH_SUPPORTED_FACTORS = ["Hope", "Interpersonal Learning"]
    
    if not any(factor in LINH_SUPPORTED_FACTORS for factor in required_factors):
        logger.info("Linh observed blackboard and skipped contribution.")
        return no_contribution(
            sender="veteran_peer_agent",
            reason="Required Yalom factors do not need Hope/Interpersonal Learning.",
        )
        
    logger.info("Linh is observing blackboard for a possible contribution.")
    
    protocol = state.get("active_protocol", {}) or {}
    protocol_rules = "\n".join(f"- {rule}" for rule in protocol.get("rules", []))
    existing_drafts = json.dumps(state.get("peer_drafts", []), ensure_ascii=False)

    prompt = _render(
        _PROMPTS.veteran_peer, 
        clinical_stage_number=state.get('clinical_stage_number', 1),
        current_stage=state.get('current_stage', state.get('current_phase', 'Assessment')),
        stage_goal=state.get('stage_goal', state.get('stage_goal_description', '')),
        clinical_summary=state.get("clinical_summary", ""),
        required_yalom_factors=", ".join(required_factors),
        therapy_route=state.get("therapy_route", "CBT"),
        protocol_rules=protocol_rules,
        user_message=state.get('user_message', ''),
        peer_drafts=existing_drafts,
        chat_history=state.get('chat_history', ''),
        safety_flags=json.dumps(state.get("safety_flags", {}), ensure_ascii=False),
    )
    
    txt = await generate_text_async(
        model=FAST_MODEL,
        contents=prompt,
        model_type=state.get("selected_model", "gemini"),
        config={"response_mime_type": "application/json", "response_schema": PeerContribution}
    )

    contribution = parse_peer_contribution(txt, sender="Veteran Peer")
    if _should_use_linh_fallback(contribution, state, required_factors):
        contribution = _linh_fallback_contribution(required_factors)
    policy = validate_peer_contribution(
        route=state.get("therapy_route", "CBT"),
        current_stage=state.get("current_stage", state.get("current_phase", "")),
        sender="veteran_peer_agent",
        required_factors=required_factors,
        yalom_factor=contribution.yalom_factor or "Hope",
        text=contribution.text,
    )
    if contribution.decision == "CONTRIBUTE" and not policy.allowed:
        logger.info("Linh contribution rejected by persona policy: %s", policy.reason)
        repaired = _linh_fallback_contribution(required_factors)
        repair_policy = validate_peer_contribution(
            route=state.get("therapy_route", "CBT"),
            current_stage=state.get("current_stage", state.get("current_phase", "")),
            sender="veteran_peer_agent",
            required_factors=required_factors,
            yalom_factor=repaired.yalom_factor or "Hope",
            text=repaired.text,
        )
        if repair_policy.allowed:
            return contribution_update(
                sender="veteran_peer_agent",
                contribution=repaired,
                default_type="peer_reframe",
                default_factor="Hope",
            )
        return no_contribution(sender="veteran_peer_agent", reason=policy.reason)

    return contribution_update(
        sender="veteran_peer_agent",
        contribution=contribution,
        default_type="peer_reframe",
        default_factor="Hope",
    )


def _should_use_linh_fallback(contribution: PeerContribution, state: GroupTherapyState, required_factors: list[str]) -> bool:
    if str(contribution.decision or "").upper() == "CONTRIBUTE":
        return False
    if contribution.safety_risk:
        return False
    if not any(factor in {"Hope", "Interpersonal Learning"} for factor in required_factors):
        return False
    current_stage = str(state.get("current_stage", state.get("current_phase", "")))
    if current_stage in {"cbt_stage_4_socratic", "mbi_stage_1_grounding", "mbi_stage_2_decentering", "mbi_stage_3_body_scan"}:
        return False
    return True


def _linh_fallback_contribution(required_factors: list[str]) -> PeerContribution:
    if "Interpersonal Learning" in required_factors:
        return PeerContribution(
            decision="CONTRIBUTE",
            contribution_type="interpersonal_learning",
            therapeutic_function="realistic_interpersonal_witness",
            yalom_factor="Interpersonal Learning",
            text="Chị từng thấy một câu mở đầu nhẹ như: 'mình muốn nói chuyện mà không muốn làm căng' giúp cuộc trò chuyện bớt đối đầu hơn.",
            reason="Deterministic Linh fallback for Interpersonal Learning after model skip.",
            confidence=0.84,
            safety_risk=False,
        )
    return PeerContribution(
        decision="CONTRIBUTE",
        contribution_type="hope_story",
        therapeutic_function="realistic_hope_witness",
        yalom_factor="Hope",
        text="Chị từng có lúc thấy mọi thứ rất tối và tưởng mình không nhích lên được. Điều giúp chị bắt đầu lại là một bước rất nhỏ đủ an toàn.",
        reason="Deterministic Linh fallback for Hope after model skip.",
        confidence=0.84,
        safety_risk=False,
    )
