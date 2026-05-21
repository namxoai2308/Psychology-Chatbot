from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.ba_contract import BA_STAGES, ba_stage_goal
from ai_engine.blackboard.ba_evidence import BAEvidence
from ai_engine.blackboard.cbt_contract import has_any, normalize_text
from ai_engine.blackboard.stage_detector import StageDecision


@dataclass
class BAMilestoneState:
    energy_checked: bool = False
    micro_action_selected: bool = False
    barrier_scheduled: bool = False
    action_completed: bool = False
    reward_reflected: bool = False
    next_action_loop_started: bool = False
    last_stage: str = "ba_stage_1_energy_check"
    stage_visit_counts: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.stage_visit_counts is None:
            self.stage_visit_counts = {stage: 0 for stage in BA_STAGES}

    def as_dict(self) -> dict[str, object]:
        return {
            "energy_checked": self.energy_checked,
            "micro_action_selected": self.micro_action_selected,
            "barrier_scheduled": self.barrier_scheduled,
            "action_completed": self.action_completed,
            "reward_reflected": self.reward_reflected,
            "next_action_loop_started": self.next_action_loop_started,
            "last_stage": self.last_stage,
            "stage_visit_counts": dict(self.stage_visit_counts or {}),
        }


def detect_ba_stage_with_milestones(
    previous_stage: str | None,
    user_message: str,
    evidence: BAEvidence,
    milestones: BAMilestoneState,
) -> StageDecision:
    previous = previous_stage if previous_stage in BA_STAGES else milestones.last_stage
    msg = normalize_text(user_message)
    stage = _stage_from_message(msg, evidence)
    _update_milestones(stage, msg, evidence, milestones)
    transition = _transition(previous, stage)
    evidence_lines = [
        _stage_reason(stage),
        "BA milestones: "
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
        stage_completion_status="completed" if stage == "ba_stage_4_momentum_reward" else "in_progress",
        stage_confidence=max(evidence.confidence or 0.68, _confidence(stage, msg)),
        stage_evidence=evidence_lines,
        stage_transition_reason=f"{transition}: {evidence_lines[0]}",
        stage_goal=ba_stage_goal(stage),
    )


def ba_yalom_for_milestone_stage(stage: str, user_message: str) -> list[str]:
    msg = normalize_text(user_message)
    if stage == "ba_stage_1_energy_check":
        return ["Universality", "Catharsis"]
    if stage == "ba_stage_2_micro_action":
        return ["Hope"]
    if stage == "ba_stage_3_barrier_schedule" and _fear_failure_barrier(msg):
        return ["Universality"]
    if stage == "ba_stage_4_momentum_reward":
        if has_any(msg, ("mood chưa tăng nhiều", "bớt kẹt", "dừng ở đây", "không quá sức", "mai thử lại")):
            return ["NONE"]
        if _completion_with_surprise(msg):
            return ["Interpersonal Learning"]
        if _fresh_completion(msg):
            return ["Hope"]
        return ["NONE"]
    return ["NONE"]


def ba_peer_for_milestone_stage(stage: str, factors: list[str], user_message: str) -> str:
    if not factors or "NONE" in factors:
        return "NONE"
    if stage == "ba_stage_1_energy_check" and {"Universality", "Catharsis"} & set(factors):
        return "peer_mirror_agent"
    if stage == "ba_stage_3_barrier_schedule" and "Universality" in factors:
        return "peer_mirror_agent"
    if stage in {"ba_stage_2_micro_action", "ba_stage_4_momentum_reward"} and (
        {"Hope", "Interpersonal Learning"} & set(factors)
    ):
        return "veteran_peer_agent"
    return "NONE"


def _stage_from_message(msg: str, evidence: BAEvidence) -> str:
    if _completion(msg) or evidence.action_completed or evidence.reward_or_mood_shift:
        return "ba_stage_4_momentum_reward"
    if _next_micro_action(msg):
        return "ba_stage_2_micro_action"
    if (evidence.low_energy or evidence.self_blame) and has_any(msg, ("chẳng muốn làm gì", "bản thân tệ", "hết pin", "cạn")):
        return "ba_stage_1_energy_check"
    if _barrier_or_schedule(msg) or evidence.barrier_named or evidence.schedule_named:
        return "ba_stage_3_barrier_schedule"
    if _micro_action_candidate(msg) or evidence.chosen_micro_action or evidence.energy_rating:
        return "ba_stage_2_micro_action"
    if evidence.low_energy or evidence.avoidance_or_shutdown or evidence.self_blame:
        return "ba_stage_1_energy_check"
    return "ba_stage_1_energy_check"


def _update_milestones(stage: str, msg: str, evidence: BAEvidence, milestones: BAMilestoneState) -> None:
    milestones.last_stage = stage
    if milestones.stage_visit_counts is None:
        milestones.stage_visit_counts = {known_stage: 0 for known_stage in BA_STAGES}
    milestones.stage_visit_counts[stage] = milestones.stage_visit_counts.get(stage, 0) + 1
    milestones.energy_checked = milestones.energy_checked or evidence.energy_rating
    milestones.micro_action_selected = milestones.micro_action_selected or stage == "ba_stage_2_micro_action"
    milestones.barrier_scheduled = milestones.barrier_scheduled or stage == "ba_stage_3_barrier_schedule"
    milestones.action_completed = milestones.action_completed or stage == "ba_stage_4_momentum_reward"
    milestones.reward_reflected = milestones.reward_reflected or evidence.reward_or_mood_shift or has_any(msg, ("bớt kẹt", "bất ngờ", "nhẹ hơn"))
    milestones.next_action_loop_started = milestones.next_action_loop_started or _next_micro_action(msg)


def _transition(previous: str, stage: str) -> str:
    if previous == stage:
        return "STAY"
    previous_index = BA_STAGES.index(previous) if previous in BA_STAGES else 0
    stage_index = BA_STAGES.index(stage) if stage in BA_STAGES else previous_index
    if stage_index > previous_index:
        return "ADVANCE"
    if stage_index < previous_index:
        return "REGRESS"
    return "STAY"


def _stage_reason(stage: str) -> str:
    return {
        "ba_stage_1_energy_check": "User is depleted or self-blaming; check energy.",
        "ba_stage_2_micro_action": "User is choosing a tiny next action.",
        "ba_stage_3_barrier_schedule": "User is naming a barrier or scheduling the action.",
        "ba_stage_4_momentum_reward": "User completed or reflected on a small action.",
    }[stage]


def _confidence(stage: str, msg: str) -> float:
    if stage == "ba_stage_4_momentum_reward" and _completion(msg):
        return 0.9
    if stage == "ba_stage_3_barrier_schedule" and _barrier_or_schedule(msg):
        return 0.88
    if stage == "ba_stage_2_micro_action" and _micro_action_candidate(msg):
        return 0.86
    return 0.78


def _completion(msg: str) -> bool:
    return has_any(
        msg,
        (
            "vừa thử",
            "được một chút",
            "làm được thêm",
            "xong rồi",
            "mình làm rồi",
            "đã làm",
            "bớt kẹt",
            "bất ngờ",
            "dừng ở đây",
            "mai thử lại",
        ),
    )


def _completion_with_surprise(msg: str) -> bool:
    return has_any(msg, ("làm được thêm", "hơi bất ngờ", "bất ngờ"))


def _fresh_completion(msg: str) -> bool:
    return has_any(msg, ("vừa thử", "được một chút", "xong rồi", "mình làm rồi", "đã làm"))


def _next_micro_action(msg: str) -> bool:
    return has_any(msg, ("nếu làm tiếp", "chọn thêm một việc rất nhỏ", "làm thêm một bước", "thử lại một bước nhỏ"))


def _barrier_or_schedule(msg: str) -> bool:
    return has_any(
        msg,
        (
            "rào cản",
            "sau khi",
            "làm ngay trong 2 phút",
            "sợ mình không làm được",
            "đặt sách lên bàn",
            "chưa cần học ngay",
        ),
    )


def _micro_action_candidate(msg: str) -> bool:
    return has_any(
        msg,
        (
            "pin",
            "/10",
            "có thể thử",
            "quá nhỏ",
            "rất nhỏ",
            "uống nước",
            "mở slide",
            "nhặt 3 món",
            "mở file",
            "nhắn một câu",
            "đặt sách",
        ),
    )


def _fear_failure_barrier(msg: str) -> bool:
    return has_any(msg, ("sợ mình không làm được", "thất bại hơn", "sợ làm không được"))
