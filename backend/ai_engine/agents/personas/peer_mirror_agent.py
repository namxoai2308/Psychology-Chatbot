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

async def peer_mirror_agent(state: GroupTherapyState) -> GroupTherapyState:
    required_factors = state.get("required_yalom_factors", ["NONE"])
    NAM_SUPPORTED_FACTORS = ["Universality", "Catharsis"]
    
    if not any(factor in NAM_SUPPORTED_FACTORS for factor in required_factors):
        logger.info("Nam observed blackboard and skipped contribution.")
        return no_contribution(
            sender="peer_mirror_agent",
            reason="Required Yalom factors do not need Universality/Catharsis.",
        )
        
    logger.info("Nam is observing blackboard for a possible contribution.")
    
    protocol = state.get("active_protocol", {}) or {}
    protocol_rules = "\n".join(f"- {rule}" for rule in protocol.get("rules", []))
    existing_drafts = json.dumps(state.get("peer_drafts", []), ensure_ascii=False)

    prompt = _render(
        _PROMPTS.peer_mirror, 
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
    
    contribution = parse_peer_contribution(txt, sender="Peer Mirror")
    if _should_use_nam_fallback(contribution, state, required_factors):
        contribution = PeerContribution(
            decision="CONTRIBUTE",
            contribution_type="universality",
            therapeutic_function="emotional_mirroring_and_shame_reduction",
            yalom_factor="Universality",
            text="Nghe như bạn đang cô đơn ngay cả khi xung quanh có nhiều người. Cảm giác đó không phải hiếm, và bạn không phải người duy nhất từng thấy mình lạc lõng như vậy.",
            reason="Deterministic Nam fallback for clear Universality/Catharsis need after empty low-confidence model skip.",
            confidence=0.82,
            safety_risk=False,
        )
    policy = validate_peer_contribution(
        route=state.get("therapy_route", "CBT"),
        current_stage=state.get("current_stage", state.get("current_phase", "")),
        sender="peer_mirror_agent",
        required_factors=required_factors,
        yalom_factor=contribution.yalom_factor or "Universality",
        text=contribution.text,
    )
    if contribution.decision == "CONTRIBUTE" and not policy.allowed:
        repaired = _safe_nam_fallback(state, required_factors)
        if repaired is not None:
            repair_policy = validate_peer_contribution(
                route=state.get("therapy_route", "CBT"),
                current_stage=state.get("current_stage", state.get("current_phase", "")),
                sender="peer_mirror_agent",
                required_factors=required_factors,
                yalom_factor=repaired.yalom_factor,
                text=repaired.text,
            )
            if repair_policy.allowed:
                contribution = repaired
            else:
                logger.info("Nam deterministic repair rejected by persona policy: %s", repair_policy.reason)
                return no_contribution(sender="peer_mirror_agent", reason=repair_policy.reason)
        else:
            logger.info("Nam contribution rejected by persona policy: %s", policy.reason)
            return no_contribution(sender="peer_mirror_agent", reason=policy.reason)

    return contribution_update(
        sender="peer_mirror_agent",
        contribution=contribution,
        default_type="peer_reflection",
        default_factor="Universality",
    )


def _should_use_nam_fallback(contribution: PeerContribution, state: GroupTherapyState, required_factors: list[str]) -> bool:
    if str(contribution.decision or "").upper() == "CONTRIBUTE":
        return False
    if contribution.safety_risk or (contribution.reason and contribution.confidence >= 0.5):
        return False
    if not any(factor in {"Universality", "Catharsis"} for factor in required_factors):
        return False
    current_stage = str(state.get("current_stage", state.get("current_phase", "")))
    if current_stage not in {"cbt_stage_1_venting", "ba_stage_1_energy_check"}:
        return False
    if current_stage == "cbt_stage_1_venting":
        return True
    user_msg = str(state.get("user_message", "")).lower()
    if current_stage == "ba_stage_1_energy_check":
        return any(token in user_msg for token in ("nằm", "lười", "tệ", "cạn", "năng lượng", "chẳng muốn", "không muốn"))
    return any(token in user_msg for token in ("cô đơn", "lạc lõng", "một mình", "yếu đuối", "xấu hổ"))


def _safe_nam_fallback(state: GroupTherapyState, required_factors: list[str]) -> PeerContribution | None:
    if not any(factor in {"Universality", "Catharsis"} for factor in required_factors):
        return None
    current_stage = str(state.get("current_stage", state.get("current_phase", "")))
    if current_stage not in {"cbt_stage_1_venting", "cbt_stage_3_distortions", "ba_stage_1_energy_check"}:
        return None
    if "Catharsis" in required_factors:
        return PeerContribution(
            decision="CONTRIBUTE",
            contribution_type="catharsis",
            therapeutic_function="emotional_mirroring_and_shame_reduction",
            yalom_factor="Catharsis",
            text="Mình nghe thấy bạn đang phải giữ rất nhiều cảm xúc bên trong. Chỉ riêng việc nói ra điều đó cũng đã nặng rồi.",
            reason="Deterministic Nam repair after an over-restrictive or off-role draft.",
            confidence=0.86,
            safety_risk=False,
        )
    return PeerContribution(
        decision="CONTRIBUTE",
        contribution_type="universality",
        therapeutic_function="emotional_mirroring_and_shame_reduction",
        yalom_factor="Universality",
        text="Cảm giác này không phải là điều chỉ riêng bạn mới gặp. Có nhiều người cũng từng thấy mình lạc lõng trong áp lực như vậy.",
        reason="Deterministic Nam repair after an over-restrictive or off-role draft.",
        confidence=0.86,
        safety_risk=False,
    )
