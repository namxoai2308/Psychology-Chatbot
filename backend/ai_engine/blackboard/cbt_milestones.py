from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import CBT_STAGES
from ai_engine.blackboard.cbt_evidence import CBTEvidence
from ai_engine.blackboard.stage_detector import StageDecision


@dataclass
class CBTMilestoneState:
    event_captured: bool = False
    emotion_captured: bool = False
    automatic_thought_captured: bool = False
    distortion_named: bool = False
    insight_captured: bool = False
    socratic_answer_captured: bool = False
    balanced_reframe_captured: bool = False
    action_step_captured: bool = False
    last_stage: str = "cbt_stage_1_venting"
    stage_visit_counts: dict[str, int] | None = None
    therapist_technique_delivered: dict[str, bool] | None = None
    last_completed_stage: str | None = None
    strict_pacing: bool = False

    def __post_init__(self) -> None:
        if self.stage_visit_counts is None:
            self.stage_visit_counts = {stage: 0 for stage in CBT_STAGES}
        if self.therapist_technique_delivered is None:
            self.therapist_technique_delivered = {stage: False for stage in CBT_STAGES}

    @classmethod
    def from_mapping(cls, value: object, previous_stage: str | None = None) -> "CBTMilestoneState":
        if isinstance(value, CBTMilestoneState):
            state = value
        elif isinstance(value, dict):
            state = cls(
                event_captured=bool(value.get("event_captured", False)),
                emotion_captured=bool(value.get("emotion_captured", False)),
                automatic_thought_captured=bool(value.get("automatic_thought_captured", False)),
                distortion_named=bool(value.get("distortion_named", False)),
                insight_captured=bool(value.get("insight_captured", False)),
                socratic_answer_captured=bool(value.get("socratic_answer_captured", False)),
                balanced_reframe_captured=bool(value.get("balanced_reframe_captured", False)),
                action_step_captured=bool(value.get("action_step_captured", False)),
                last_stage=str(value.get("last_stage") or previous_stage or "cbt_stage_1_venting"),
                stage_visit_counts=dict(value.get("stage_visit_counts")) if isinstance(value.get("stage_visit_counts"), dict) else None,
                therapist_technique_delivered=dict(value.get("therapist_technique_delivered"))
                if isinstance(value.get("therapist_technique_delivered"), dict)
                else None,
                last_completed_stage=value.get("last_completed_stage") if isinstance(value.get("last_completed_stage"), str) else None,
                strict_pacing=True,
            )
        else:
            state = cls(last_stage=previous_stage if previous_stage in CBT_STAGES else "cbt_stage_1_venting")
            _prime_from_previous_stage(state, previous_stage)
        return state

    def as_dict(self) -> dict[str, object]:
        return {
            "event_captured": self.event_captured,
            "emotion_captured": self.emotion_captured,
            "automatic_thought_captured": self.automatic_thought_captured,
            "distortion_named": self.distortion_named,
            "insight_captured": self.insight_captured,
            "socratic_answer_captured": self.socratic_answer_captured,
            "balanced_reframe_captured": self.balanced_reframe_captured,
            "action_step_captured": self.action_step_captured,
            "last_stage": self.last_stage,
            "stage_visit_counts": dict(self.stage_visit_counts or {}),
            "therapist_technique_delivered": dict(self.therapist_technique_delivered or {}),
            "last_completed_stage": self.last_completed_stage,
        }


def detect_cbt_stage_with_milestones(
    previous_stage: str | None,
    user_message: str,
    evidence: CBTEvidence,
    milestones: CBTMilestoneState,
) -> StageDecision:
    previous = previous_stage if previous_stage in CBT_STAGES else milestones.last_stage
    if previous not in CBT_STAGES:
        previous = "cbt_stage_1_venting"
    stage = _stage_from_evidence(evidence, milestones, previous)
    _update_milestones(stage, evidence, milestones)
    transition = _transition(previous, stage)
    status = "ready_to_advance" if transition == "ADVANCE" else "in_progress"
    confidence = max(evidence.confidence or 0.68, _confidence_for_stage(stage, evidence))
    evidence_lines = [
        _stage_reason(stage, evidence),
        "CBT milestones: "
        + ", ".join(
            f"{key}={value}"
            for key, value in milestones.as_dict().items()
            if key != "stage_visit_counts"
        ),
    ]
    return StageDecision(
        previous_stage=previous,
        current_stage=stage,
        stage_transition=transition,
        stage_completion_status=status,
        stage_confidence=min(confidence, 0.95),
        stage_evidence=evidence_lines,
        stage_transition_reason=f"{transition}: {evidence_lines[0]}",
        stage_goal=_stage_goal(stage),
    )


def cbt_yalom_for_milestone_stage(stage: str, user_message: str) -> list[str]:
    from ai_engine.blackboard.cbt_evidence import extract_cbt_evidence_heuristic

    evidence = extract_cbt_evidence_heuristic(user_message)
    if evidence.peer_boundary_intent:
        return ["NONE"]
    if stage == "cbt_stage_1_venting":
        if evidence.hope_request:
            return ["Hope"]
        return ["Universality", "Catharsis"]
    if stage == "cbt_stage_3_distortions":
        if evidence.distortion_reflection or evidence.automatic_thought_present or evidence.distortion_candidates:
            return ["Universality"]
        return ["NONE"]
    if stage == "cbt_stage_5_action":
        if evidence.balanced_reframe:
            return ["Hope"]
        if evidence.action_commitment:
            return ["Interpersonal Learning"]
        return ["NONE"]
    return ["NONE"]


def cbt_peer_for_milestone_stage(stage: str, factors: list[str], user_message: str) -> str:
    from ai_engine.blackboard.cbt_evidence import extract_cbt_evidence_heuristic

    evidence = extract_cbt_evidence_heuristic(user_message)
    if not factors or "NONE" in factors or stage == "cbt_stage_4_socratic":
        return "NONE"
    if "Hope" in factors or "Interpersonal Learning" in factors:
        return "veteran_peer_agent"
    if "Universality" in factors or "Catharsis" in factors:
        if stage == "cbt_stage_1_venting":
            return "peer_mirror_agent"
        if stage == "cbt_stage_3_distortions" and (
            evidence.distortion_reflection or evidence.automatic_thought_present or evidence.distortion_candidates
        ):
            return "peer_mirror_agent"
    return "NONE"


def _stage_from_evidence(evidence: CBTEvidence, milestones: CBTMilestoneState, previous: str) -> str:
    previous_index = CBT_STAGES.index(previous) if previous in CBT_STAGES else 0
    abc_ready = _abc_ready(evidence)
    thought_ready = _thought_ready(evidence)
    distortion_ready = _distortion_ready(evidence)
    socratic_ready = _socratic_ready(evidence)
    balanced_ready = bool(evidence.balanced_reframe)
    action_ready = bool(evidence.action_commitment or evidence.action_step)
    strict = milestones.strict_pacing
    previous_visits = _visit_count(milestones, previous)
    stage1_ready_to_leave = not strict or previous_visits >= 2
    stage2_ready_to_leave = not strict or previous_visits >= 2
    stage3_ready_to_leave = not strict or previous_visits >= 2
    stage4_ready_to_leave = not strict or previous_visits >= 2

    if evidence.hope_request and previous_index < 1 and not balanced_ready and not action_ready:
        return "cbt_stage_1_venting" if previous_index <= 1 else previous
    if evidence.peer_boundary_intent and previous_index < 2:
        return "cbt_stage_2_abc_model"
    if previous == "cbt_stage_1_venting":
        if not stage1_ready_to_leave:
            return "cbt_stage_1_venting"
        if abc_ready or (thought_ready and (milestones.event_captured or evidence.event_present)) or _visit_count(milestones, "cbt_stage_1_venting") >= 3:
            return "cbt_stage_2_abc_model"
        return "cbt_stage_1_venting"
    if previous == "cbt_stage_2_abc_model" and _visit_count(milestones, "cbt_stage_2_abc_model") >= 3:
        return "cbt_stage_3_distortions"
    if previous == "cbt_stage_3_distortions" and _visit_count(milestones, "cbt_stage_3_distortions") >= 3:
        return "cbt_stage_4_socratic"
    if previous == "cbt_stage_4_socratic" and stage4_ready_to_leave and balanced_ready:
        return "cbt_stage_5_action"
    if previous == "cbt_stage_4_socratic" and stage4_ready_to_leave and action_ready and (
        balanced_ready or socratic_ready or milestones.socratic_answer_captured or not strict
    ):
        return "cbt_stage_5_action"
    if previous == "cbt_stage_3_distortions" and balanced_ready and not strict:
        return "cbt_stage_5_action"
    if previous == "cbt_stage_3_distortions" and stage3_ready_to_leave and socratic_ready and milestones.distortion_named:
        return "cbt_stage_4_socratic"
    if previous == "cbt_stage_2_abc_model" and stage2_ready_to_leave and distortion_ready and (
        milestones.automatic_thought_captured or thought_ready or abc_ready
    ):
        return "cbt_stage_3_distortions"
    if previous_index >= 4:
        return "cbt_stage_5_action"
    if previous_index >= 3:
        return "cbt_stage_4_socratic"
    if previous_index >= 2:
        return "cbt_stage_3_distortions"
    if abc_ready or thought_ready:
        if previous_index < 1 and thought_ready and not abc_ready and strict:
            return "cbt_stage_1_venting"
        return "cbt_stage_2_abc_model"
    if evidence.overload or evidence.hope_request or evidence.emotion_present:
        return "cbt_stage_1_venting" if previous_index <= 1 else previous
    return previous


def _update_milestones(stage: str, evidence: CBTEvidence, milestones: CBTMilestoneState) -> None:
    milestones.last_stage = stage
    if milestones.stage_visit_counts is None:
        milestones.stage_visit_counts = {known_stage: 0 for known_stage in CBT_STAGES}
    if milestones.therapist_technique_delivered is None:
        milestones.therapist_technique_delivered = {known_stage: False for known_stage in CBT_STAGES}
    milestones.stage_visit_counts[stage] = milestones.stage_visit_counts.get(stage, 0) + 1
    if milestones.stage_visit_counts[stage] >= 1:
        milestones.therapist_technique_delivered[stage] = True
        milestones.last_completed_stage = stage
    milestones.emotion_captured = milestones.emotion_captured or evidence.emotion_present
    milestones.event_captured = milestones.event_captured or evidence.event_present or evidence.abc_present
    milestones.automatic_thought_captured = milestones.automatic_thought_captured or _thought_ready(evidence)
    milestones.distortion_named = milestones.distortion_named or (
        stage == "cbt_stage_3_distortions" and (evidence.distortion_reflection or bool(evidence.distortion_candidates))
    )
    milestones.insight_captured = milestones.insight_captured or evidence.insight_present or evidence.distortion_reflection
    milestones.socratic_answer_captured = milestones.socratic_answer_captured or evidence.socratic_reasoning
    milestones.balanced_reframe_captured = milestones.balanced_reframe_captured or evidence.balanced_reframe
    milestones.action_step_captured = milestones.action_step_captured or evidence.action_commitment or evidence.action_step


def _transition(previous: str, stage: str) -> str:
    if previous == stage:
        return "STAY"
    previous_index = CBT_STAGES.index(previous) if previous in CBT_STAGES else 0
    stage_index = CBT_STAGES.index(stage) if stage in CBT_STAGES else previous_index
    if stage_index > previous_index:
        return "ADVANCE"
    if stage_index < previous_index:
        return "REGRESS"
    return "STAY"


def _stage_goal(stage: str) -> str:
    return {
        "cbt_stage_1_venting": "Validate emotion and stabilize alliance before analysis.",
        "cbt_stage_2_abc_model": "Separate event, automatic thought, and emotion.",
        "cbt_stage_3_distortions": "Name one thinking trap gently.",
        "cbt_stage_4_socratic": "Check evidence or use double-standard question.",
        "cbt_stage_5_action": "Form a balanced thought and one small next step.",
    }[stage]


def _stage_reason(stage: str, evidence: CBTEvidence) -> str:
    if stage == "cbt_stage_1_venting":
        return "User is still primarily expressing emotion/context."
    if stage == "cbt_stage_2_abc_model":
        return "User is identifying event/thought/emotion material for ABC separation."
    if stage == "cbt_stage_3_distortions":
        return f"User is ready to name a thinking trap; distortions={evidence.distortion_candidates}."
    if stage == "cbt_stage_4_socratic":
        return "User is testing evidence or using a double-standard perspective."
    return "User is forming a balanced thought, action step, or relapse plan."


def _confidence_for_stage(stage: str, evidence: CBTEvidence) -> float:
    if stage == "cbt_stage_5_action" and (evidence.balanced_reframe or evidence.action_commitment):
        return 0.9
    if stage == "cbt_stage_4_socratic" and evidence.socratic_reasoning:
        return 0.88
    if stage == "cbt_stage_3_distortions" and _distortion_ready(evidence):
        return 0.86
    if stage == "cbt_stage_2_abc_model" and _abc_ready(evidence):
        return 0.86
    return 0.78


def _abc_ready(evidence: CBTEvidence) -> bool:
    return bool(evidence.abc_present)


def _thought_ready(evidence: CBTEvidence) -> bool:
    return bool(evidence.automatic_thought_present or evidence.has_automatic_thought)


def _distortion_ready(evidence: CBTEvidence) -> bool:
    return bool(evidence.distortion_reflection or evidence.distortion_candidates or (evidence.insight_present and _thought_ready(evidence)))


def _socratic_ready(evidence: CBTEvidence) -> bool:
    return bool(evidence.socratic_reasoning or evidence.insight_present)


def _prime_from_previous_stage(milestones: CBTMilestoneState, previous_stage: str | None) -> None:
    if previous_stage not in CBT_STAGES:
        return
    previous_index = CBT_STAGES.index(previous_stage)
    milestones.last_stage = previous_stage
    if milestones.stage_visit_counts is None:
        milestones.stage_visit_counts = {stage: 0 for stage in CBT_STAGES}
    milestones.stage_visit_counts[previous_stage] = max(milestones.stage_visit_counts.get(previous_stage, 0), 1)
    if milestones.therapist_technique_delivered is None:
        milestones.therapist_technique_delivered = {stage: False for stage in CBT_STAGES}
    milestones.therapist_technique_delivered[previous_stage] = True
    if previous_index >= 0:
        milestones.emotion_captured = True
    if previous_index >= 1:
        milestones.event_captured = True
    if previous_index >= 2:
        milestones.automatic_thought_captured = True
        milestones.distortion_named = True
    if previous_index >= 3:
        milestones.insight_captured = True
    if previous_index >= 4:
        milestones.action_step_captured = True


def _visit_count(milestones: CBTMilestoneState, stage: str) -> int:
    return int((milestones.stage_visit_counts or {}).get(stage) or 0)
