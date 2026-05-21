from ai_engine.state import GroupTherapyState
from ai_engine.blackboard.route_response_validator import validate_therapist_response
from ai_engine.blackboard.orchestrator_output_normalizer import normalize_orchestrator_payload
from ai_engine.blackboard.therapist_supervisor import build_supervisor_audit
from ai_engine.blackboard.yalom_persona_contract import route_peer_allowed, validate_peer_contribution
from ai_engine.blackboard.case_formulation import format_case_formulation
from ai_engine.blackboard.psychosocial_safety import assess_psychosocial_safety, safety_fallback
from ai_engine.services.clinical_knowledge import stage_knowledge
from ai_engine.services.therapist_style import format_therapist_style_card
from ai_engine.services.llm_service import FAST_MODEL, generate_text_async
from ai_engine.runtime import _PROMPTS, _render
import json
import logging
import random
import re
from difflib import SequenceMatcher
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DraftDecision(BaseModel):
    sender: str = Field(description="peer_mirror_agent or veteran_peer_agent")
    action: str = Field(default="discard", description="include, rewrite, or discard")
    reason: str = ""
    rewritten_text: str = ""

class OrchestratorOutput(BaseModel):
    clinical_reasoning_scratchpad: str = Field(description="Brief clinical/group reasoning before final response.")
    case_formulation: str = Field(default="", description="One short hypothesis about the user's pattern this turn.")
    stage_task: str = Field(default="", description="The active therapy task for the current stage.")
    response_strategy: str = Field(default="", description="The one technique used in doctor_speech.")
    selected_technique: str = Field(default="", description="Specific technique selected from stage knowledge.")
    route_alignment: str = Field(default="", description="How the response stays within the current route.")
    risk_check: str = Field(default="", description="Brief safety/scope check.")
    cognitive_distortion: str = Field(default="None", description="Nhãn lỗi tư duy theo CBT (nếu có)")
    therapist_plan: str = Field(default="", description="How the therapist will use/discard peer drafts.")
    draft_decisions: list[DraftDecision] = Field(default_factory=list)
    doctor_speech: str = Field(default="", description="Therapist message that must be shown to the user.")


def _normalized_text(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
    return " ".join(text.strip().split())


def _too_similar(left: str, right: str) -> bool:
    left_norm = _normalized_text(left)
    right_norm = _normalized_text(right)
    if not left_norm or not right_norm:
        return False
    if left_norm in right_norm or right_norm in left_norm:
        return True
    left_words = set(left_norm.split())
    right_words = set(right_norm.split())
    if left_words and right_words:
        overlap = len(left_words & right_words) / min(len(left_words), len(right_words))
        if overlap >= 0.78:
            return True
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= 0.72


def _therapist_bridge_fallback(state: GroupTherapyState, included_peer_count: int) -> str:
    current_stage = str(state.get("current_stage", "")).lower()
    user_message = state.get("user_message", "")
    if "cbt_stage_3_distortions" in current_stage:
        return _stage_specific_therapist_message(state)
    if "cbt_stage_4_socratic" in current_stage or "phóng đại" in user_message.lower():
        return (
            "Tôi muốn giữ lại phát hiện rất quan trọng của bạn: bạn đã nhận ra ý nghĩ đó có phần phóng đại. "
            "Khi nó tự động xuất hiện, bằng chứng nào ủng hộ và bằng chứng nào làm nó bớt tuyệt đối hơn?"
        )
    if included_peer_count:
        return (
            "Tôi sẽ giữ phần chia sẻ của bạn đồng hành như một tiếng nói phụ, còn mình quay lại điều bạn đang cần nhất lúc này. "
            "Trong áp lực này, suy nghĩ nào đang làm cảm xúc của bạn tăng mạnh nhất?"
        )
    return (
        "Tôi đang lắng nghe bạn và muốn đi chậm ở đúng điểm quan trọng nhất. "
        "Phần nào trong chuyện này đang khiến bạn thấy nặng nhất ngay lúc này?"
    )


def _stage_specific_therapist_message(state: GroupTherapyState) -> str:
    result = validate_therapist_response(
        str(state.get("current_stage", "")),
        "",
        state.get("user_message", ""),
    )
    return result.fallback_response or _therapist_bridge_fallback(state, included_peer_count=0)


def _doctor_speech_misses_stage_goal(state: GroupTherapyState, speech: str) -> bool:
    return not validate_therapist_response(
        str(state.get("current_stage", "")),
        speech,
        state.get("user_message", ""),
    ).valid


def _soft_accept_stage_response(validation) -> bool:
    scores = validation.quality_scores or {}
    return (
        validation.fallback_used
        and scores.get("stage_fit", 0) >= 2
        and scores.get("safety", 0) >= 2
        and scores.get("focus", 0) >= 1
    )


def _build_structured_therapist_plan(
    *,
    state: GroupTherapyState,
    peer_drafts: list[dict],
    draft_decisions: list[dict],
    doctor_speech: str,
    orchestrator_data: dict,
) -> dict:
    current_stage = str(state.get("current_stage", ""))
    required_factors = state.get("required_yalom_factors", ["NONE"])
    discarded = [
        str(decision.get("sender"))
        for decision in draft_decisions
        if str(decision.get("action", "discard")).lower() == "discard"
    ]
    included = [
        str(decision.get("sender"))
        for decision in draft_decisions
        if str(decision.get("action", "")).lower() in {"include", "rewrite"}
    ]
    if "NONE" in required_factors:
        discarded = sorted(set(discarded + [str(draft.get("sender")) for draft in peer_drafts if isinstance(draft, dict)]))
    return {
        "user_need": state.get("clinical_summary", ""),
        "stage_objective": state.get("stage_goal", ""),
        "chosen_technique": orchestrator_data.get("selected_technique") or orchestrator_data.get("response_strategy", ""),
        "why_now": orchestrator_data.get("route_alignment") or state.get("case_formulation", {}).get("next_intervention_rationale", ""),
        "what_not_to_do": _what_not_to_do(current_stage),
        "peer_draft_decision": {
            "required_yalom_factors": required_factors,
            "included_or_rewritten": included,
            "discarded": discarded,
        },
        "safety_concern": orchestrator_data.get("risk_check", ""),
        "final_response_preview": doctor_speech,
    }


def _what_not_to_do(current_stage: str) -> str:
    if "cbt_stage_1" in current_stage:
        return "Do not challenge thoughts or ask evidence questions yet."
    if "cbt_stage_4" in current_stage:
        return "Do not include peers by default or ask generic venting questions."
    if current_stage.startswith("mbi_"):
        return "Do not turn mindfulness work into CBT debate."
    if current_stage.startswith("ba_"):
        return "Do not moralize low energy or assign large tasks."
    return "Do not diagnose, overpromise, or push the user."


def _clean_speaker_attribution(text: str) -> str:
    replacements = {
        "chị Nam": "Nam",
        "Chị Nam": "Nam",
        "anh Linh": "chị Linh",
        "Anh Linh": "Chị Linh",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


async def orchestrator_node(state: GroupTherapyState) -> GroupTherapyState:
    logger.info("Therapist orchestrator reading blackboard and peer drafts.")
    
    msg = state.get('user_message', '')
    if not msg:
        return {}

    validator_enabled = bool(state.get("validator_enabled", True))
    safety_critic_enabled = bool(state.get("safety_critic_enabled", True))
    peer_enabled = bool(state.get("peer_enabled", True))

    peer_drafts = state.get("peer_drafts", [])
    if not isinstance(peer_drafts, list):
        peer_drafts = []
    if not peer_enabled:
        peer_drafts = []
    contribution_decisions = state.get("peer_contribution_decisions", [])
    if not isinstance(contribution_decisions, list):
        contribution_decisions = []
    if not peer_enabled:
        contribution_decisions = []

    protocol = state.get("active_protocol", {}) or {}
    protocol_rules = "\n".join(f"- {rule}" for rule in protocol.get("rules", []))
    current_stage = state.get("current_stage", state.get("current_phase", "Assessment"))
    route = str(state.get("therapy_route", "CBT"))
    clinical_knowledge = stage_knowledge(route, str(current_stage), str(state.get("cognitive_distortion", "None")))
    case_formulation_text = format_case_formulation(state.get("case_formulation"))
    therapist_style = format_therapist_style_card()
    pre_safety_report = state.get("psychosocial_safety") or assess_psychosocial_safety(
        user_message=msg,
        chat_history=state.get("chat_history", ""),
        safety_flags=state.get("safety_flags", {}),
    )

    prompt_content = _render(_PROMPTS.orchestrator, 
                             user_message=msg, 
                             clinical_stage_number=state.get("clinical_stage_number", 1),
                             current_stage=current_stage,
                             stage_goal=state.get("stage_goal", state.get("stage_goal_description", "")),
                             clinical_summary=state.get("clinical_summary", ""),
                             case_formulation=case_formulation_text,
                             therapist_style=therapist_style,
                             psychosocial_safety=json.dumps(pre_safety_report, ensure_ascii=False),
                             clinical_knowledge=clinical_knowledge,
                             required_yalom_factors=", ".join(state.get("required_yalom_factors", ["NONE"])),
                             therapy_route=route,
                             protocol_rules=protocol_rules,
                             peer_drafts=json.dumps(peer_drafts, ensure_ascii=False, indent=2),
                             peer_contribution_decisions=json.dumps(contribution_decisions, ensure_ascii=False, indent=2),
                             safety_flags=json.dumps(state.get("safety_flags", {}), ensure_ascii=False),
                             chat_history=state.get('chat_history', ''))
    
    txt = await generate_text_async(
        model=FAST_MODEL,
        contents=prompt_content,
        model_type=state.get("selected_model", "gemini"),
        config={"response_mime_type": "application/json", "response_schema": OrchestratorOutput}
    )
    
    try:
        data = OrchestratorOutput.model_validate(normalize_orchestrator_payload(json.loads(txt))).model_dump()
    except Exception as e:
        logger.warning("Orchestrator JSON parse failed; using fallback: %s", e)
        data = {
            "clinical_reasoning_scratchpad": "",
            "case_formulation": "",
            "stage_task": "",
            "response_strategy": "",
            "risk_check": "Fallback because model did not return valid JSON.",
            "cognitive_distortion": "None",
            "therapist_plan": "Fallback because model did not return valid JSON.",
            "draft_decisions": [],
            "doctor_speech": "Tôi đang lắng nghe bạn. Điều quan trọng nhất lúc này với bạn là phần nào trong chuyện vừa xảy ra?",
        }
        
    doctor_speech = _clean_speaker_attribution(data.get("doctor_speech", "").strip())
    cognitive_distortion = data.get("cognitive_distortion", "None")
    draft_decisions = data.get("draft_decisions", [])

    required_factors = state.get("required_yalom_factors", ["NONE"])
    peer_allowed = peer_enabled and isinstance(required_factors, list) and "NONE" not in required_factors

    final_output = []
    drafts_by_sender = {d.get("sender"): d for d in peer_drafts if isinstance(d, dict)}
    for decision in draft_decisions if peer_allowed else []:
        sender = decision.get("sender")
        action = str(decision.get("action", "discard")).lower()
        draft = drafts_by_sender.get(sender)
        if not draft or draft.get("safety_risk"):
            continue
        if not route_peer_allowed(
            route,
            str(state.get("current_stage", "")),
            str(sender),
            required_factors,
        ):
            continue
        candidate_text = draft.get("text", "").strip() if action == "include" else decision.get("rewritten_text", "").strip()
        candidate_text = _clean_speaker_attribution(candidate_text)
        peer_policy = validate_peer_contribution(
            route=route,
            current_stage=str(state.get("current_stage", "")),
            sender=str(sender),
            required_factors=required_factors,
            yalom_factor=str(draft.get("yalom_factor", "NONE")),
            text=candidate_text,
        )
        if not peer_policy.allowed:
            logger.info("Orchestrator rejected peer output by persona policy: %s", peer_policy.reason)
            continue
        if action == "include":
            final_output.append({
                "sender": sender,
                "text": candidate_text,
                "typing_time_ms": draft.get("typing_time_ms", int(random.uniform(3500, 7000))),
            })
        elif action == "rewrite" and candidate_text:
            final_output.append({
                "sender": sender,
                "text": candidate_text,
                "typing_time_ms": draft.get("typing_time_ms", int(random.uniform(3500, 7000))),
            })

    if peer_allowed and not final_output:
        for draft in peer_drafts:
            if not isinstance(draft, dict) or draft.get("safety_risk"):
                continue
            sender = str(draft.get("sender", ""))
            candidate_text = _clean_speaker_attribution(str(draft.get("text", "")).strip())
            if not candidate_text:
                continue
            if not route_peer_allowed(route, str(state.get("current_stage", "")), sender, required_factors):
                continue
            peer_policy = validate_peer_contribution(
                route=route,
                current_stage=str(state.get("current_stage", "")),
                sender=sender,
                required_factors=required_factors,
                yalom_factor=str(draft.get("yalom_factor", "NONE")),
                text=candidate_text,
            )
            if peer_policy.allowed:
                logger.info("Using valid peer draft after orchestrator omitted explicit include/rewrite decision.")
                final_output.append(
                    {
                        "sender": sender,
                        "text": candidate_text,
                        "typing_time_ms": draft.get("typing_time_ms", int(random.uniform(3500, 7000))),
                    }
                )
                break

    if not doctor_speech:
        doctor_speech = "Tôi đang ở đây với bạn. Từ những điều vừa được phản chiếu, phần nào khiến bạn thấy được chạm tới nhất?"

    included_peer_texts = [msg.get("text", "") for msg in final_output]
    if any(_too_similar(doctor_speech, peer_text) for peer_text in included_peer_texts):
        logger.info("Doctor speech was too similar to an included peer draft; using bridge fallback.")
        doctor_speech = _therapist_bridge_fallback(state, included_peer_count=len(included_peer_texts))

    fallback_used = False
    validator_repair_used = False
    initial_validation_reason = ""
    if validator_enabled:
        initial_cbt_validation = validate_therapist_response(
            str(state.get("current_stage", "")),
            doctor_speech,
            state.get("user_message", ""),
        )
        cbt_validation = initial_cbt_validation
        if not initial_cbt_validation.valid:
            if _soft_accept_stage_response(initial_cbt_validation):
                logger.info("Doctor speech failed strict validator but passed soft stage/safety gate: %s", initial_cbt_validation.reason)
                cbt_validation = type(initial_cbt_validation)(
                    True,
                    f"Soft-accepted stage response after strict miss: {initial_cbt_validation.reason}",
                    doctor_speech,
                    False,
                    initial_cbt_validation.quality_scores,
                )
            else:
                logger.info("Doctor speech failed CBT validator; using fallback: %s", initial_cbt_validation.reason)
                validator_repair_used = True
                initial_validation_reason = initial_cbt_validation.reason
                doctor_speech = initial_cbt_validation.fallback_response
                cbt_validation = validate_therapist_response(
                    str(state.get("current_stage", "")),
                    doctor_speech,
                    state.get("user_message", ""),
                )
    else:
        logger.info("Therapist response validator disabled by system variant.")
        cbt_validation = None

    combined_candidate = "\n".join([item.get("text", "") for item in final_output] + [doctor_speech])
    if safety_critic_enabled:
        post_safety_report = assess_psychosocial_safety(
            user_message=msg,
            assistant_text=combined_candidate,
            chat_history=state.get("chat_history", ""),
            safety_flags=state.get("safety_flags", {}),
        )
        if post_safety_report.get("high_risk"):
            logger.warning("Psychosocial safety high risk; replacing final output with safety fallback.")
            final_output = []
            doctor_speech = safety_fallback(post_safety_report)
            fallback_used = True
    else:
        logger.info("Post-generation psychosocial safety critic disabled by system variant.")
        post_safety_report = {
            "overall_severity": "disabled",
            "critics": [],
            "high_risk": False,
            "medium_risk": False,
        }

    final_output.append({
        "sender": "therapist_coordinator_agent",
        "text": doctor_speech,
        "typing_time_ms": int(random.uniform(3000, 6000))
    })
    supervisor_audit = build_supervisor_audit(
        state=state,
        orchestrator_data=data,
        doctor_speech=doctor_speech,
        final_output=final_output,
        validator_enabled=validator_enabled,
    )
    structured_plan = _build_structured_therapist_plan(
        state=state,
        peer_drafts=peer_drafts,
        draft_decisions=draft_decisions,
        doctor_speech=doctor_speech,
        orchestrator_data=data,
    )

    therapist_validator = {
        "enabled": validator_enabled,
        "valid": cbt_validation.valid if cbt_validation is not None else None,
        "reason": cbt_validation.reason if cbt_validation is not None else "disabled_by_variant",
        "fallback_used": fallback_used,
        "validator_repair_used": validator_repair_used,
        "initial_reason": initial_validation_reason,
        "quality_scores": cbt_validation.quality_scores if cbt_validation is not None else {},
    }

    return {
        "final_output": final_output,
        "cognitive_distortion": cognitive_distortion,
        "therapist_plan": data.get("therapist_plan", ""),
        "structured_therapist_plan": structured_plan,
        "psychosocial_safety": post_safety_report,
        "therapist_validator": therapist_validator,
        "peer_used": bool(final_output[:-1]),
        "fallback_used": fallback_used,
        "validator_repair_used": validator_repair_used,
        "therapist_debug": {
            "case_formulation": state.get("case_formulation", {}),
            "llm_case_formulation": data.get("case_formulation", ""),
            "case_formulation_text": case_formulation_text,
            "therapist_style": therapist_style,
            "psychosocial_safety": post_safety_report,
            "structured_therapist_plan": structured_plan,
            "stage_task": data.get("stage_task", ""),
            "response_strategy": data.get("response_strategy", ""),
            "selected_technique": data.get("selected_technique", ""),
            "route_alignment": data.get("route_alignment", ""),
            "risk_check": data.get("risk_check", ""),
            "supervisor_audit": supervisor_audit.model_dump(),
            "variant_controls": {
                "peer_enabled": peer_enabled,
                "validator_enabled": validator_enabled,
                "safety_critic_enabled": safety_critic_enabled,
            },
        },
        "next_speaker": "FINISH"
    }
