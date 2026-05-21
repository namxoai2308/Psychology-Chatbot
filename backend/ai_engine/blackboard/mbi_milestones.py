from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import has_any, normalize_text
from ai_engine.blackboard.mbi_contract import MBI_STAGES, mbi_stage_goal
from ai_engine.blackboard.mbi_evidence import MBIEvidence
from ai_engine.blackboard.stage_detector import StageDecision


@dataclass
class MBIMilestoneState:
    grounding_started: bool = False
    breathing_settled: bool = False
    thought_observed: bool = False
    body_sensation_named: bool = False
    mindful_action_selected: bool = False
    relapse_observed: bool = False
    last_stage: str = "mbi_stage_1_grounding"
    stage_visit_counts: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.stage_visit_counts is None:
            self.stage_visit_counts = {stage: 0 for stage in MBI_STAGES}

    def as_dict(self) -> dict[str, object]:
        return {
            "grounding_started": self.grounding_started,
            "breathing_settled": self.breathing_settled,
            "thought_observed": self.thought_observed,
            "body_sensation_named": self.body_sensation_named,
            "mindful_action_selected": self.mindful_action_selected,
            "relapse_observed": self.relapse_observed,
            "last_stage": self.last_stage,
            "stage_visit_counts": dict(self.stage_visit_counts or {}),
        }


def detect_mbi_stage_with_milestones(
    previous_stage: str | None,
    user_message: str,
    evidence: MBIEvidence,
    milestones: MBIMilestoneState,
) -> StageDecision:
    previous = previous_stage if previous_stage in MBI_STAGES else milestones.last_stage
    msg = normalize_text(user_message)
    stage = _stage_from_message(msg, evidence, previous)
    _update_milestones(stage, msg, evidence, milestones)
    transition = _transition(previous, stage)
    evidence_lines = [
        _stage_reason(stage),
        "MBI milestones: "
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
        stage_completion_status="ready_to_advance" if transition == "ADVANCE" else "in_progress",
        stage_confidence=max(evidence.confidence or 0.68, _confidence(stage, msg)),
        stage_evidence=evidence_lines,
        stage_transition_reason=f"{transition}: {evidence_lines[0]}",
        stage_goal=mbi_stage_goal(stage),
    )


def mbi_yalom_for_milestone_stage(stage: str, user_message: str) -> list[str]:
    return ["NONE"]


def _stage_from_message(msg: str, evidence: MBIEvidence, previous: str) -> str:
    if _grounding_return(msg) or (evidence.panic_or_overload and not evidence.breathing_settled):
        return "mbi_stage_1_grounding"
    if _mindful_action(msg) or _closure_after_action(msg):
        return "mbi_stage_4_mindful_action"
    if _body_scan(msg) or evidence.body_sensation:
        return "mbi_stage_3_body_scan"
    if _decentering(msg) or evidence.thought_observed or evidence.breathing_settled:
        return "mbi_stage_2_decentering"
    return previous


def _update_milestones(stage: str, msg: str, evidence: MBIEvidence, milestones: MBIMilestoneState) -> None:
    milestones.last_stage = stage
    if milestones.stage_visit_counts is None:
        milestones.stage_visit_counts = {known_stage: 0 for known_stage in MBI_STAGES}
    milestones.stage_visit_counts[stage] = milestones.stage_visit_counts.get(stage, 0) + 1
    milestones.grounding_started = milestones.grounding_started or stage == "mbi_stage_1_grounding"
    milestones.breathing_settled = milestones.breathing_settled or evidence.breathing_settled
    milestones.thought_observed = milestones.thought_observed or stage == "mbi_stage_2_decentering"
    milestones.body_sensation_named = milestones.body_sensation_named or stage == "mbi_stage_3_body_scan"
    milestones.mindful_action_selected = milestones.mindful_action_selected or stage == "mbi_stage_4_mindful_action"
    milestones.relapse_observed = milestones.relapse_observed or has_any(msg, ("quay lại", "lại", "làn căng thẳng mới"))


def _transition(previous: str, stage: str) -> str:
    if previous == stage:
        return "STAY"
    previous_index = MBI_STAGES.index(previous) if previous in MBI_STAGES else 0
    stage_index = MBI_STAGES.index(stage) if stage in MBI_STAGES else previous_index
    if stage_index > previous_index:
        return "ADVANCE"
    if stage_index < previous_index:
        return "REGRESS"
    return "STAY"


def _stage_reason(stage: str) -> str:
    return {
        "mbi_stage_1_grounding": "User needs or returns to present-moment grounding.",
        "mbi_stage_2_decentering": "User is observing thoughts as thoughts.",
        "mbi_stage_3_body_scan": "User names or tracks body sensations.",
        "mbi_stage_4_mindful_action": "User is ready for a small mindful action or closure.",
    }[stage]


def _confidence(stage: str, msg: str) -> float:
    if stage == "mbi_stage_1_grounding" and _grounding_return(msg):
        return 0.9
    if stage == "mbi_stage_2_decentering" and _decentering(msg):
        return 0.88
    if stage == "mbi_stage_3_body_scan" and _body_scan(msg):
        return 0.88
    if stage == "mbi_stage_4_mindful_action" and (_mindful_action(msg) or _closure_after_action(msg)):
        return 0.88
    return 0.78


def _grounding_return(msg: str) -> bool:
    return has_any(msg, ("quay lại hơi thở", "hơi thở ra chậm", "thở ra chậm hơn", "bàn chân", "chạm sàn"))


def _decentering(msg: str) -> bool:
    return has_any(
        msg,
        (
            "suy nghĩ vẫn chạy",
            "gọi nó là một ý nghĩ",
            "ý nghĩ đang xuất hiện",
            "không phải sự thật",
            "ý nghĩ lại quay lại",
            "bị cuốn",
            "quan sát tiếp",
        ),
    )


def _body_scan(msg: str) -> bool:
    return has_any(
        msg,
        (
            "khi để ý cơ thể",
            "thấy rõ nhất ở",
            "cảm giác ở",
            "ngực",
            "vai",
            "bụng",
            "căng lúc dịu",
            "quan sát được",
        ),
    )


def _mindful_action(msg: str) -> bool:
    return has_any(
        msg,
        (
            "dịu hơn và muốn làm gì đó nhỏ",
            "kết thúc lượt",
            "sẽ uống nước",
            "nhìn ra cửa sổ",
            "vươn vai",
            "đứng dậy",
            "làm gì đó nhỏ",
        ),
    )


def _closure_after_action(msg: str) -> bool:
    return has_any(
        msg,
        (
            "sau khi làm vậy",
            "không bị cuốn như lúc đầu",
            "ghi nhớ cách gọi",
            "khi nó quay lại",
            "dùng lại",
        ),
    )
