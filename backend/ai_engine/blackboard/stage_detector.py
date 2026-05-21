from __future__ import annotations

import re
from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import (
    CBT_STAGES,
    cbt_allowed_yalom,
    cbt_default_yalom,
    cbt_stage_goal,
    has_any,
    normalize_text,
)
from ai_engine.blackboard.cbt_evidence import CBTEvidence, cbt_evidence_from_mapping, extract_cbt_evidence_heuristic
from ai_engine.blackboard.mbi_contract import MBI_STAGES, mbi_allowed_yalom, mbi_default_yalom, mbi_stage_goal
from ai_engine.blackboard.mbi_evidence import MBIEvidence, extract_mbi_evidence_heuristic
from ai_engine.blackboard.ba_contract import BA_STAGES, ba_allowed_yalom, ba_default_yalom, ba_stage_goal
from ai_engine.blackboard.ba_evidence import BAEvidence, extract_ba_evidence_heuristic


STAGE_GOALS = {
    **{stage: cbt_stage_goal(stage) for stage in CBT_STAGES},
    **{stage: mbi_stage_goal(stage) for stage in MBI_STAGES},
    **{stage: ba_stage_goal(stage) for stage in BA_STAGES},
}


STAGE_NUMBERS = {
    **{stage: i + 1 for i, stage in enumerate(CBT_STAGES)},
    **{stage: i + 1 for i, stage in enumerate(MBI_STAGES)},
    **{stage: i + 1 for i, stage in enumerate(BA_STAGES)},
}


ROUTE_STAGES = {
    "CBT": CBT_STAGES,
    "MBI": MBI_STAGES,
    "BA": BA_STAGES,
}


@dataclass(frozen=True)
class StageDecision:
    previous_stage: str
    current_stage: str
    stage_transition: str
    stage_completion_status: str
    stage_confidence: float
    stage_evidence: list[str]
    stage_transition_reason: str
    stage_goal: str

    @property
    def clinical_stage_number(self) -> int:
        return STAGE_NUMBERS.get(self.current_stage, 1)


def detect_stage(
    route: str,
    previous_stage: str | None,
    user_message: str,
    chat_history: str = "",
    cbt_evidence: CBTEvidence | dict | None = None,
    mbi_evidence: MBIEvidence | dict | None = None,
    ba_evidence: BAEvidence | dict | None = None,
) -> StageDecision:
    route_key = (route or "CBT").upper()
    if route_key == "MBI":
        return _detect_mbi(previous_stage, user_message, chat_history, mbi_evidence)
    if route_key == "BA":
        return _detect_ba(previous_stage, user_message, chat_history, ba_evidence)
    return _detect_cbt(previous_stage, user_message, chat_history, cbt_evidence)


def yalom_factors_for_stage(route: str, stage: str, user_message: str = "") -> list[str]:
    route_key = (route or "CBT").upper()
    msg = _norm(user_message)
    if route_key == "MBI":
        return mbi_default_yalom(stage, user_message)
    if route_key == "BA":
        return ba_default_yalom(stage, user_message)
    if stage in CBT_STAGES:
        return cbt_default_yalom(stage, user_message)
    return ["NONE"]


def allowed_yalom_factors_for_stage(route: str, stage: str) -> set[str]:
    route_key = (route or "CBT").upper()
    if route_key == "MBI":
        return mbi_allowed_yalom(stage)
    if route_key == "BA":
        return ba_allowed_yalom(stage)
    if stage in CBT_STAGES:
        return cbt_allowed_yalom(stage)
    return {"NONE"}


def _detect_cbt(
    previous_stage: str | None,
    user_message: str,
    chat_history: str,
    cbt_evidence: CBTEvidence | dict | None = None,
) -> StageDecision:
    previous = _valid_previous(previous_stage, "CBT")
    evidence_model = (
        cbt_evidence
        if isinstance(cbt_evidence, CBTEvidence)
        else cbt_evidence_from_mapping(cbt_evidence, user_message)
        if cbt_evidence is not None
        else extract_cbt_evidence_heuristic(user_message, chat_history)
    )
    from ai_engine.blackboard.cbt_milestones import CBTMilestoneState, detect_cbt_stage_with_milestones

    return detect_cbt_stage_with_milestones(
        previous,
        user_message,
        evidence_model,
        CBTMilestoneState.from_mapping(None, previous),
    )


def _detect_mbi(
    previous_stage: str | None,
    user_message: str,
    chat_history: str,
    mbi_evidence: MBIEvidence | dict | None = None,
) -> StageDecision:
    previous = _valid_previous(previous_stage, "MBI")
    evidence_model = (
        mbi_evidence
        if isinstance(mbi_evidence, MBIEvidence)
        else MBIEvidence.model_validate(mbi_evidence)
        if isinstance(mbi_evidence, dict)
        else extract_mbi_evidence_heuristic(user_message, chat_history)
    )
    evidence: list[str] = []
    target = previous
    transition = "STAY"
    status = "in_progress"
    confidence = evidence_model.confidence or 0.68
    previous_index = MBI_STAGES.index(previous) if previous in MBI_STAGES else 0

    if evidence_model.panic_or_overload:
        target = "mbi_stage_1_grounding"
        transition = _transition(previous, target, "MBI")
        confidence = max(confidence, 0.86)
        evidence.append("User reports acute overload or body panic cues.")
    elif previous_index >= 3 and not evidence_model.panic_or_overload:
        target = "mbi_stage_4_mindful_action"
        transition = _transition(previous, target, "MBI")
        status = "ready_to_advance"
        confidence = max(confidence, 0.82)
        evidence.append("User is already in mindful-action closure; maintain closure unless acute overload returns.")
    elif evidence_model.mindful_action_ready or (evidence_model.breathing_settled and previous_index >= 2):
        target = "mbi_stage_4_mindful_action"
        transition = _transition(previous, target, "MBI")
        status = "ready_to_advance"
        confidence = max(confidence, 0.82)
        evidence.append("User is regulated enough to close with a mindful action.")
    elif evidence_model.body_sensation:
        target = "mbi_stage_3_body_scan"
        transition = _transition(previous, target, "MBI")
        status = "ready_to_advance"
        confidence = max(confidence, 0.83)
        evidence.append("User identifies a concrete body sensation.")
    elif evidence_model.thought_observed or evidence_model.breathing_settled:
        target = "mbi_stage_2_decentering"
        transition = _transition(previous, target, "MBI")
        status = "ready_to_advance"
        confidence = max(confidence, 0.8)
        evidence.append("User is caught by recurring thoughts but not asking for logic debate.")

    if evidence_model.evidence_quotes:
        evidence.extend(f"Evidence quote: {quote}" for quote in evidence_model.evidence_quotes[:3])
    evidence.append(
        "MBI evidence features: "
        f"panic={evidence_model.panic_or_overload}, "
        f"settled={evidence_model.breathing_settled}, "
        f"thought={evidence_model.thought_observed}, "
        f"body={evidence_model.body_sensation}, "
        f"present={evidence_model.present_moment_contact}, "
        f"action_ready={evidence_model.mindful_action_ready}, "
        f"source={evidence_model.source}."
    )
    return _decision(previous, target, transition, status, confidence, evidence, "MBI")


def _detect_ba(
    previous_stage: str | None,
    user_message: str,
    chat_history: str,
    ba_evidence: BAEvidence | dict | None = None,
) -> StageDecision:
    previous = _valid_previous(previous_stage, "BA")
    evidence_model = (
        ba_evidence
        if isinstance(ba_evidence, BAEvidence)
        else BAEvidence.model_validate(ba_evidence)
        if isinstance(ba_evidence, dict)
        else extract_ba_evidence_heuristic(user_message, chat_history)
    )
    evidence: list[str] = []
    target = previous
    transition = "STAY"
    status = "in_progress"
    confidence = evidence_model.confidence or 0.68
    normalized_message = normalize_text(user_message)

    if evidence_model.action_completed or evidence_model.reward_or_mood_shift:
        target = "ba_stage_4_momentum_reward"
        transition = _transition(previous, target, "BA")
        status = "completed"
        confidence = max(confidence, 0.86)
        evidence.append("User reports completing the micro-action.")
    elif evidence_model.barrier_named or evidence_model.schedule_named:
        target = "ba_stage_3_barrier_schedule"
        transition = _transition(previous, target, "BA")
        status = "ready_to_advance"
        confidence = max(confidence, 0.84)
        evidence.append("User named a barrier or schedule cue for the micro-action.")
    elif evidence_model.chosen_micro_action:
        committed_action = any(
            marker in normalized_message
            for marker in (
                "mình chọn",
                "tôi chọn",
                "em chọn",
                "mình sẽ",
                "tôi sẽ",
                "em sẽ",
                "mình thử",
                "tôi thử",
                "em thử",
            )
        )
        tentative_action = has_any(normalized_message, ("có thể thử", "nghe vẫn", "hơi buồn cười", "quá nhỏ", "quá sức"))
        if committed_action and not tentative_action:
            target = "ba_stage_3_barrier_schedule"
        else:
            target = "ba_stage_2_micro_action"
        transition = _transition(previous, target, "BA")
        status = "ready_to_advance"
        confidence = max(confidence, 0.82)
        evidence.append("User selected or is considering a concrete micro-action.")
    elif evidence_model.energy_rating:
        target = "ba_stage_2_micro_action"
        transition = _transition(previous, target, "BA")
        status = "ready_to_advance"
        confidence = max(confidence, 0.84)
        evidence.append("User provided an energy level.")
    elif evidence_model.low_energy or evidence_model.avoidance_or_shutdown or evidence_model.self_blame:
        target = "ba_stage_1_energy_check"
        transition = _transition(previous, target, "BA")
        confidence = max(confidence, 0.76)
        evidence.append("User describes low activation, depletion, or self-blame.")

    if evidence_model.evidence_quotes:
        evidence.extend(f"Evidence quote: {quote}" for quote in evidence_model.evidence_quotes[:3])
    evidence.append(
        "BA evidence features: "
        f"low_energy={evidence_model.low_energy}, "
        f"avoidance={evidence_model.avoidance_or_shutdown}, "
        f"self_blame={evidence_model.self_blame}, "
        f"energy={evidence_model.energy_rating}, "
        f"action={evidence_model.chosen_micro_action}, "
        f"barrier={evidence_model.barrier_named}, "
        f"schedule={evidence_model.schedule_named}, "
        f"completed={evidence_model.action_completed}, "
        f"source={evidence_model.source}."
    )
    return _decision(previous, target, transition, status, confidence, evidence, "BA")


def _decision(
    previous: str,
    target: str,
    transition: str,
    status: str,
    confidence: float,
    evidence: list[str],
    route: str,
) -> StageDecision:
    if confidence < 0.65:
        target = previous
        transition = "STAY"
        status = "in_progress"
        evidence.append("Confidence below threshold; keep previous stage.")
    if not evidence:
        evidence.append("No strong transition evidence; keep current stage.")
    reason = f"{transition}: {evidence[0]}"
    return StageDecision(
        previous_stage=previous,
        current_stage=target,
        stage_transition=transition,
        stage_completion_status=status,
        stage_confidence=round(confidence, 2),
        stage_evidence=evidence,
        stage_transition_reason=reason,
        stage_goal=STAGE_GOALS[target],
    )


def _valid_previous(previous_stage: str | None, route: str) -> str:
    stages = ROUTE_STAGES[route]
    return previous_stage if previous_stage in stages else stages[0]


def _transition(previous: str, target: str, route: str) -> str:
    if previous == target:
        return "STAY"
    stages = ROUTE_STAGES[route]
    prev_i = stages.index(previous) if previous in stages else 0
    target_i = stages.index(target) if target in stages else 0
    if target_i > prev_i:
        return "ADVANCE"
    if target_i < prev_i:
        return "REGRESS"
    return "RESET"


def _norm(text: str) -> str:
    return normalize_text(text)


def _has_any(text: str, needles: list[str]) -> bool:
    return has_any(text, needles)
