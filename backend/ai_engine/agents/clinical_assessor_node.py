import json
import logging

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_evidence import CBTEvidence, extract_cbt_evidence_heuristic, sanitize_llm_cbt_evidence
from ai_engine.blackboard.cbt_evidence_normalizer import normalize_cbt_assessor_payload
from ai_engine.blackboard.cbt_contract import has_any, normalize_text
from ai_engine.blackboard.cbt_milestones import CBTMilestoneState, detect_cbt_stage_with_milestones
from ai_engine.blackboard.mbi_evidence import extract_mbi_evidence_heuristic
from ai_engine.blackboard.ba_evidence import extract_ba_evidence_heuristic
from ai_engine.blackboard.case_formulation import build_case_formulation
from ai_engine.blackboard.psychosocial_safety import assess_psychosocial_safety
from ai_engine.blackboard.stage_detector import (
    allowed_yalom_factors_for_stage,
    detect_stage,
    yalom_factors_for_stage,
)
from ai_engine.state import GroupTherapyState
from ai_engine.services.llm_service import FAST_MODEL, generate_text_async

logger = logging.getLogger(__name__)


class AssessorDecision(BaseModel):
    clinical_summary: str = Field(default="", description="Brief blackboard summary of the user's emotional state and need.")
    required_yalom_factors: list[str] = Field(default=["NONE"], description="Yalom factors needed right now.")
    safety_flags: dict = Field(default_factory=dict, description="Safety observations.")


class CBTAssessorEvidenceDecision(BaseModel):
    clinical_summary: str = Field(default="", description="Brief blackboard summary of the user's emotional state and need.")
    safety_flags: dict = Field(default_factory=dict, description="Safety observations.")
    cbt_evidence: CBTEvidence = Field(default_factory=CBTEvidence)


async def clinical_assessor_node(state: GroupTherapyState) -> GroupTherapyState:
    logger.info("Clinical assessor updating blackboard.")
    protocol = state.get("active_protocol", {})
    protocol_dept = protocol.get("department") or protocol.get("modality", "General CBT Therapy")
    protocol_goals = protocol.get("goals") or "; ".join(protocol.get("rules", [])) or "Assess, Empathize, Treat, Relapse Prevention"
    chat_hist = state.get("chat_history", "")
    user_msg = state.get("user_message", "")
    if not user_msg:
        return {}

    previous_stage = state.get("current_stage") or state.get("current_phase")
    if str(protocol_dept).upper() == "CBT":
        return await _clinical_assessor_cbt(
            state=state,
            protocol_dept=protocol_dept,
            protocol_goals=protocol_goals,
            previous_stage=previous_stage,
            user_msg=user_msg,
            chat_hist=chat_hist,
        )

    return await _clinical_assessor_non_cbt(
        state=state,
        protocol_dept=protocol_dept,
        protocol_goals=protocol_goals,
        previous_stage=previous_stage,
        user_msg=user_msg,
        chat_hist=chat_hist,
    )


async def _clinical_assessor_non_cbt(
    state: GroupTherapyState,
    protocol_dept: str,
    protocol_goals: str,
    previous_stage: str | None,
    user_msg: str,
    chat_hist: str,
) -> GroupTherapyState:
    route_key = str(protocol_dept).upper()
    stage_evidence_details = None
    if route_key == "MBI":
        evidence_model = extract_mbi_evidence_heuristic(user_msg, chat_hist)
        stage_decision = detect_stage(protocol_dept, previous_stage, user_msg, chat_hist, mbi_evidence=evidence_model)
        stage_evidence_details = evidence_model.model_dump()
    elif route_key == "BA":
        evidence_model = extract_ba_evidence_heuristic(user_msg, chat_hist)
        stage_decision = detect_stage(protocol_dept, previous_stage, user_msg, chat_hist, ba_evidence=evidence_model)
        stage_evidence_details = evidence_model.model_dump()
    else:
        stage_decision = detect_stage(protocol_dept, previous_stage, user_msg, chat_hist)
    prompt = f"""
    You are the Clinical Assessor in the background tracking the user's progress through {protocol_dept}.
    Protocol Goals: {protocol_goals}

    IMPORTANT: The current stage has already been determined by a deterministic stage machine.
    Do NOT override this stage or the deterministic Yalom factors. Use it only to write clinical_summary and safety_flags.
    Stage machine result:
    - previous_stage: {stage_decision.previous_stage}
    - current_stage: {stage_decision.current_stage}
    - stage_transition: {stage_decision.stage_transition}
    - stage_completion_status: {stage_decision.stage_completion_status}
    - stage_confidence: {stage_decision.stage_confidence}
    - stage_evidence: {json.dumps(stage_decision.stage_evidence, ensure_ascii=False)}
    - stage_goal: {stage_decision.stage_goal}

    Based on the Chat History and the latest User Message, update the shared blackboard for the therapist and peer observers.
    Do not change stage. Only summarize the user's emotional state and the kind of group support that may help.

    Return JSON format:
    - clinical_summary
    - required_yalom_factors
    - safety_flags

    Chat History:
    {chat_hist}

    Latest User Message:
    {user_msg}
    """

    try:
        txt = await generate_text_async(
            model=FAST_MODEL,
            contents=prompt,
            model_type=state.get("selected_model", "gemini"),
            config={"response_mime_type": "application/json", "response_schema": AssessorDecision},
        )
        data = json.loads(txt)
        clinical_summary = data.get("clinical_summary", "")
        safety_flags = data.get("safety_flags", {})
    except Exception as e:
        logger.warning("Clinical assessor fallback after JSON error: %s", e)
        clinical_summary = "Không đủ dữ liệu phân tích tự động; ưu tiên lắng nghe, phản hồi an toàn và không đưa lời khuyên cứng."
        safety_flags = {}

    factors = _deterministic_yalom_factors(protocol_dept, stage_decision.current_stage, user_msg, chat_hist)
    update = _stage_update(stage_decision, clinical_summary, factors, safety_flags)
    if stage_evidence_details is not None:
        update["stage_evidence_details"] = stage_evidence_details
    update["case_formulation"] = build_case_formulation(
        route=route_key,
        current_stage=stage_decision.current_stage,
        user_message=user_msg,
        chat_history=chat_hist,
        previous=state.get("case_formulation"),
        evidence_details=stage_evidence_details,
    )
    update["psychosocial_safety"] = assess_psychosocial_safety(
        user_message=user_msg,
        chat_history=chat_hist,
        safety_flags=safety_flags,
    )
    return update


async def _clinical_assessor_cbt(
    state: GroupTherapyState,
    protocol_dept: str,
    protocol_goals: str,
    previous_stage: str | None,
    user_msg: str,
    chat_hist: str,
) -> GroupTherapyState:
    prompt = f"""
    You are the Clinical Assessor evidence extractor for a CBT blackboard therapy system.
    Your job is NOT to choose the final CBT stage. A deterministic finite-state controller will do that.
    Extract only observable CBT evidence from the user's Vietnamese message and recent history.

    Protocol Goals: {protocol_goals}
    Previous stage: {previous_stage or "unknown"}

    Evidence definitions:
    - emotion_present: user expresses affect such as worry, shame, sadness, anger, overload, pressure.
    - event_present: user names a concrete event/context such as exam, interview, conflict, message, deadline, symptom.
    - abc_present: user provides enough event/thought/emotion material to separate an ABC chain.
    - automatic_thought: the user's thought/belief, if clearly stated. Keep it as a short quote, otherwise empty.
    - automatic_thought_present: user states a belief, prediction, self-label, or conditional conclusion.
    - distortion_candidates: possible CBT distortion labels from: catastrophizing, all_or_nothing, mind_reading, labeling, personalization, overgeneralization.
    - distortion_reflection: user is identifying a thinking pattern/trap such as exaggeration, absolutism, mind-reading, labeling, or catastrophizing.
    - socratic_reasoning: user is weighing evidence, uncertainty, alternative explanations, or a double-standard/friend perspective.
    - insight_present: user doubts/observes the thought, e.g. "maybe I am exaggerating", "I cannot be sure".
    - balanced_reframe: user has a more balanced alternative thought, not just a positive word.
    - action_step: user names a concrete next step or small behavioral plan.
    - action_commitment: user commits to or chooses a concrete next step, timing, or relapse plan.
    - peer_boundary_intent: user asks to reduce/stop peer input, return to therapist focus, or keep the decision with the therapist.
    - overload: acute panic/overload that should slow down analysis.
    - hope_request: user asks whether recovery is possible or expresses strong hopelessness.
    - confidence: 0.0-1.0 confidence in evidence extraction.
    - evidence_quotes: exact short user quotes supporting the fields.

    Do not infer more than the user actually said.
    Do not output current_stage.
    Do not output Yalom factors.

    Chat History:
    {chat_hist}

    Latest User Message:
    {user_msg}

    Return JSON with:
    - clinical_summary
    - safety_flags
    - cbt_evidence
    """

    try:
        txt = await generate_text_async(
            model=FAST_MODEL,
            contents=prompt,
            model_type=state.get("selected_model", "gemini"),
            config={
                "response_mime_type": "application/json",
                "response_schema": CBTAssessorEvidenceDecision,
                "temperature": 0.1,
            },
        )
        data = CBTAssessorEvidenceDecision.model_validate(normalize_cbt_assessor_payload(json.loads(txt)))
        evidence = data.cbt_evidence
        if not evidence.evidence_quotes:
            evidence.evidence_quotes = [user_msg]
        evidence.source = "llm"
        evidence = sanitize_llm_cbt_evidence(evidence, user_msg)
        clinical_summary = data.clinical_summary
        safety_flags = data.safety_flags
    except Exception as e:
        logger.warning("CBT evidence extractor fallback after JSON error: %s", e)
        evidence = extract_cbt_evidence_heuristic(user_msg, chat_hist)
        clinical_summary = "Không đủ dữ liệu phân tích tự động; ưu tiên lắng nghe, phản hồi an toàn và đi theo CBT stage guardrail."
        safety_flags = {}

    milestones = CBTMilestoneState.from_mapping(state.get("cbt_milestones"), previous_stage)
    stage_decision = detect_cbt_stage_with_milestones(previous_stage, user_msg, evidence, milestones)
    factors = _deterministic_yalom_factors(
        protocol_dept,
        stage_decision.current_stage,
        user_msg,
        chat_hist,
        evidence=evidence,
        peer_state=_peer_state_from_graph_state(state),
    )
    update = _stage_update(stage_decision, clinical_summary, factors, safety_flags)
    evidence_details = evidence.model_dump()
    update["stage_evidence_details"] = evidence_details
    update["cbt_milestones"] = milestones.as_dict()
    update["case_formulation"] = build_case_formulation(
        route="CBT",
        current_stage=stage_decision.current_stage,
        user_message=user_msg,
        chat_history=chat_hist,
        previous=state.get("case_formulation"),
        evidence_details=evidence_details,
    )
    update["psychosocial_safety"] = assess_psychosocial_safety(
        user_message=user_msg,
        chat_history=chat_hist,
        safety_flags=safety_flags,
    )
    return update


def _deterministic_yalom_factors(
    protocol_dept: str,
    stage: str,
    user_msg: str,
    chat_hist: str = "",
    *,
    evidence: CBTEvidence | None = None,
    peer_state: dict | None = None,
) -> list[str]:
    default_factors = yalom_factors_for_stage(protocol_dept, stage, user_msg)
    if str(protocol_dept).upper() == "CBT":
        if evidence is None:
            evidence = extract_cbt_evidence_heuristic(user_msg, chat_hist)
        default_factors = _cbt_state_sensitive_yalom(stage, user_msg, default_factors, evidence=evidence, peer_state=peer_state)
    allowed_factors = allowed_yalom_factors_for_stage(protocol_dept, stage)
    factors = [factor for factor in default_factors if factor in allowed_factors]
    if not factors:
        return ["NONE"] if "NONE" in allowed_factors else default_factors
    return factors


def _cbt_history_sensitive_yalom(stage: str, user_msg: str, chat_hist: str, default_factors: list[str]) -> list[str]:
    evidence = extract_cbt_evidence_heuristic(user_msg, chat_hist)
    return _cbt_state_sensitive_yalom(stage, user_msg, default_factors, evidence=evidence, peer_state=None)


def _cbt_state_sensitive_yalom(
    stage: str,
    user_msg: str,
    default_factors: list[str],
    *,
    evidence: CBTEvidence,
    peer_state: dict | None = None,
) -> list[str]:
    peer_state = peer_state or {}
    if evidence.peer_boundary_intent:
        return ["NONE"]
    if stage == "cbt_stage_4_socratic":
        return ["NONE"]
    if (
        stage == "cbt_stage_5_action"
        and peer_state.get("last_peer_sender") == "veteran_peer_agent"
        and int(peer_state.get("consecutive_peer_turns") or 0) >= 1
        and not _explicit_veteran_peer_request(evidence, user_msg)
    ):
        return ["NONE"]
    if stage != "cbt_stage_1_venting":
        if stage == "cbt_stage_3_distortions" and not evidence.distortion_reflection and not evidence.automatic_thought_present:
            if evidence.action_step and not evidence.action_commitment:
                return ["Universality"]
            return ["NONE"]
        return default_factors
    if evidence.distortion_reflection or evidence.socratic_reasoning:
        return ["NONE"]
    if evidence.hope_request:
        return ["Hope"]
    return default_factors


def _explicit_veteran_peer_request(evidence: CBTEvidence, user_msg: str) -> bool:
    if evidence.hope_request:
        return True
    msg = normalize_text(user_msg)
    return has_any(
        msg,
        (
            "kinh nghiệm",
            "kinh nghiem",
            "học được",
            "hoc duoc",
            "từng vượt qua",
            "tung vuot qua",
        ),
    )


def _peer_state_from_graph_state(state: GroupTherapyState) -> dict:
    return {
        "last_peer_sender": state.get("last_peer_sender"),
        "consecutive_peer_turns": state.get("consecutive_peer_turns", 0),
        "peer_silence_cooldown": state.get("peer_silence_cooldown", 0),
    }


def _stage_update(stage_decision, clinical_summary: str, factors: list[str], safety_flags: dict) -> GroupTherapyState:
    safety_flags = safety_flags if isinstance(safety_flags, dict) else {}
    return {
        "previous_stage": stage_decision.previous_stage,
        "clinical_stage_number": stage_decision.clinical_stage_number,
        "current_stage": stage_decision.current_stage,
        "current_phase": stage_decision.current_stage,
        "stage_goal": stage_decision.stage_goal,
        "stage_goal_description": stage_decision.stage_goal,
        "stage_confidence": stage_decision.stage_confidence,
        "stage_evidence": stage_decision.stage_evidence,
        "stage_transition": stage_decision.stage_transition,
        "stage_transition_reason": stage_decision.stage_transition_reason,
        "stage_completion_status": stage_decision.stage_completion_status,
        "clinical_summary": clinical_summary,
        "required_yalom_factors": factors,
        "safety_flags": safety_flags,
        "peer_drafts": "CLEAR",
        "peer_contribution_decisions": "CLEAR",
    }
