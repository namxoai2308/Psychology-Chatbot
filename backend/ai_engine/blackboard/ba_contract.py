from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import has_any, normalize_text


@dataclass(frozen=True)
class BAStageContract:
    stage_id: str
    stage_goal: str
    allowed_yalom_factors: tuple[str, ...]
    default_yalom_factors: tuple[str, ...]
    therapist_required_patterns: tuple[str, ...]
    therapist_forbidden_patterns: tuple[str, ...]
    peer_policy: dict[str, str]
    fallback_response: str


BA_STAGES = [
    "ba_stage_1_energy_check",
    "ba_stage_2_micro_action",
    "ba_stage_3_barrier_schedule",
    "ba_stage_4_momentum_reward",
]


BA_CONTRACTS: dict[str, BAStageContract] = {
    "ba_stage_1_energy_check": BAStageContract(
        stage_id="ba_stage_1_energy_check",
        stage_goal="Validate depletion and get an energy rating.",
        allowed_yalom_factors=("Universality", "Catharsis"),
        default_yalom_factors=("Universality", "Catharsis"),
        therapist_required_patterns=("năng lượng", "pin", "/10", "mức", "cạn", "kiệt"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa", "phân tích"),
        peer_policy={
            "peer_mirror_agent": "May contribute Universality/Catharsis for shame and depletion.",
            "veteran_peer_agent": "No contribution by default.",
        },
        fallback_response=(
            "Nghe giống bạn đang rất cạn năng lượng, không phải đơn giản là lười. "
            "Nếu chấm mức pin hiện tại từ 0 đến 10, bạn đang khoảng mấy phần?"
        ),
    ),
    "ba_stage_2_micro_action": BAStageContract(
        stage_id="ba_stage_2_micro_action",
        stage_goal="Select one tiny action matched to current energy.",
        allowed_yalom_factors=("NONE", "Hope"),
        default_yalom_factors=("Hope",),
        therapist_required_patterns=(
            "hành động nhỏ",
            "rất nhỏ",
            "bước nhỏ",
            "uống nước",
            "ngụm nước",
            "rửa mặt",
            "mở",
            "2 phút",
            "5 phút",
        ),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa", "đào sâu"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "May contribute short realistic hope about starting small.",
        },
        fallback_response=(
            "Với mức năng lượng đó, mình không chọn việc lớn. Chỉ chọn một hành động rất nhỏ: uống nước, rửa mặt, "
            "hoặc mở tài liệu trong 2 phút. Việc nào ít kháng cự nhất?"
        ),
    ),
    "ba_stage_3_barrier_schedule": BAStageContract(
        stage_id="ba_stage_3_barrier_schedule",
        stage_goal="Name the barrier and schedule the micro-action.",
        allowed_yalom_factors=("NONE", "Universality", "Interpersonal Learning"),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("rào cản", "khi nào", "mấy giờ", "ngay sau", "đặt", "lịch", "bắt đầu"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa", "cố lên"),
        peer_policy={
            "peer_mirror_agent": "May contribute Universality when the barrier is shame or fear of failing again.",
            "veteran_peer_agent": "May contribute short learned tactic if Interpersonal Learning is required.",
        },
        fallback_response=(
            "Tốt, mình làm cho nó dễ xảy ra hơn: rào cản lớn nhất là gì, và bạn sẽ bắt đầu việc nhỏ đó vào lúc nào cụ thể?"
        ),
    ),
    "ba_stage_4_momentum_reward": BAStageContract(
        stage_id="ba_stage_4_momentum_reward",
        stage_goal="Reinforce completion, track mood shift, choose rest or continue.",
        allowed_yalom_factors=("NONE", "Hope", "Interpersonal Learning"),
        default_yalom_factors=("Hope",),
        therapist_required_patterns=("đã làm", "xong", "ghi nhận", "mood", "tâm trạng", "nghỉ", "tiếp tục"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa", "chưa đủ"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "May contribute short hope after completion.",
        },
        fallback_response=(
            "Mình ghi nhận việc bạn đã làm xong bước nhỏ đó. Tâm trạng hoặc mức pin thay đổi chút nào không, "
            "và bây giờ bạn muốn nghỉ hay làm thêm một bước rất nhỏ?"
        ),
    ),
}


def get_ba_contract(stage_id: str) -> BAStageContract:
    return BA_CONTRACTS.get(stage_id, BA_CONTRACTS["ba_stage_1_energy_check"])


def is_ba_stage(stage_id: str | None) -> bool:
    return bool(stage_id and stage_id in BA_CONTRACTS)


def ba_stage_goal(stage_id: str) -> str:
    return get_ba_contract(stage_id).stage_goal


def ba_allowed_yalom(stage_id: str) -> set[str]:
    return set(get_ba_contract(stage_id).allowed_yalom_factors)


def ba_default_yalom(stage_id: str, user_message: str = "") -> list[str]:
    msg = normalize_text(user_message)
    if stage_id == "ba_stage_1_energy_check":
        return ["Universality", "Catharsis"]
    if stage_id == "ba_stage_2_micro_action" and has_any(
        msg,
        (
            "không nổi",
            "khó",
            "chắc không",
            "nản",
            "quá sức",
            "quá nhỏ",
            "buồn cười",
            "không đáng",
            "vô nghĩa",
        ),
    ):
        return ["Hope"]
    if stage_id == "ba_stage_3_barrier_schedule" and has_any(
        msg,
        ("học được", "mẹo", "cách làm", "từng thử", "kinh nghiệm"),
    ):
        return ["Interpersonal Learning"]
    if stage_id == "ba_stage_3_barrier_schedule" and has_any(
        msg,
        ("sợ", "thất bại", "xấu hổ", "tệ hơn", "không làm được", "không nổi", "ngại"),
    ):
        return ["Universality"]
    if stage_id == "ba_stage_4_momentum_reward" and has_any(
        msg,
        ("chưa tăng nhiều", "bớt kẹt", "dừng", "không quá sức", "mai thử lại", "nghỉ"),
    ):
        return ["NONE"]
    return list(get_ba_contract(stage_id).default_yalom_factors)
