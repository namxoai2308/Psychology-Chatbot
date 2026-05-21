from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import has_any, normalize_text


@dataclass(frozen=True)
class MBIStageContract:
    stage_id: str
    stage_goal: str
    allowed_yalom_factors: tuple[str, ...]
    default_yalom_factors: tuple[str, ...]
    therapist_required_patterns: tuple[str, ...]
    therapist_forbidden_patterns: tuple[str, ...]
    peer_policy: dict[str, str]
    fallback_response: str


MBI_STAGES = [
    "mbi_stage_1_grounding",
    "mbi_stage_2_decentering",
    "mbi_stage_3_body_scan",
    "mbi_stage_4_mindful_action",
]


MBI_CONTRACTS: dict[str, MBIStageContract] = {
    "mbi_stage_1_grounding": MBIStageContract(
        stage_id="mbi_stage_1_grounding",
        stage_goal="Anchor attention to breathing, feet, and present senses; no analysis.",
        allowed_yalom_factors=("NONE", "Catharsis"),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("thở", "bàn chân", "chạm", "nhìn", "nghe", "hiện tại", "cảm nhận"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa"),
        peer_policy={
            "peer_mirror_agent": "Usually no contribution; optional very short catharsis if required.",
            "veteran_peer_agent": "No contribution.",
        },
        fallback_response=(
            "Mình tạm chưa phân tích nội dung suy nghĩ nhé. Bạn thử đặt hai bàn chân xuống sàn, thở ra chậm hơn một chút, "
            "rồi nói với tôi một thứ bạn đang nhìn thấy ngay lúc này."
        ),
    ),
    "mbi_stage_2_decentering": MBIStageContract(
        stage_id="mbi_stage_2_decentering",
        stage_goal="Help user notice thoughts as mental events without debating them.",
        allowed_yalom_factors=("NONE",),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("mình đang có suy nghĩ", "quan sát", "ý nghĩ", "đi qua", "bị cuốn", "gọi tên"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "đúng hay sai", "thảm họa hóa", "lỗi tư duy"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "No contribution.",
        },
        fallback_response=(
            "Thay vì tranh luận với suy nghĩ đó, mình thử đổi cách đứng nhìn nó: "
            "\"mình đang có suy nghĩ rằng...\". Bạn có thể đặt câu đó vào sau cụm này không?"
        ),
    ),
    "mbi_stage_3_body_scan": MBIStageContract(
        stage_id="mbi_stage_3_body_scan",
        stage_goal="Locate body sensation and observe it gently.",
        allowed_yalom_factors=("NONE",),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("cơ thể", "ngực", "vai", "bụng", "cổ", "cảm giác", "quét", "vùng"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "No contribution.",
        },
        fallback_response=(
            "Mình đưa sự chú ý về cơ thể một chút nhé. Cảm giác rõ nhất đang nằm ở vùng nào: ngực, vai, cổ, bụng, hay chỗ khác?"
        ),
    ),
    "mbi_stage_4_mindful_action": MBIStageContract(
        stage_id="mbi_stage_4_mindful_action",
        stage_goal="Close with one small mindful physical action.",
        allowed_yalom_factors=("NONE", "Hope"),
        default_yalom_factors=("Hope",),
        therapist_required_patterns=("bước nhỏ", "uống nước", "vươn vai", "đứng dậy", "nhìn ra", "một việc"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "lỗi tư duy", "thảm họa hóa", "phân tích thêm"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "May contribute short realistic hope if Hope is required.",
        },
        fallback_response=(
            "Nếu cơ thể đã dịu hơn một chút, mình khép lại bằng một bước nhỏ có chánh niệm: uống vài ngụm nước, "
            "vươn vai chậm, hoặc nhìn ra xa 30 giây. Bạn chọn việc nào vừa sức nhất?"
        ),
    ),
}


def get_mbi_contract(stage_id: str) -> MBIStageContract:
    return MBI_CONTRACTS.get(stage_id, MBI_CONTRACTS["mbi_stage_1_grounding"])


def is_mbi_stage(stage_id: str | None) -> bool:
    return bool(stage_id and stage_id in MBI_CONTRACTS)


def mbi_stage_goal(stage_id: str) -> str:
    return get_mbi_contract(stage_id).stage_goal


def mbi_allowed_yalom(stage_id: str) -> set[str]:
    return set(get_mbi_contract(stage_id).allowed_yalom_factors)


def mbi_default_yalom(stage_id: str, user_message: str = "") -> list[str]:
    msg = normalize_text(user_message)
    if stage_id == "mbi_stage_4_mindful_action" and has_any(msg, ("đỡ", "dịu", "nhẹ", "ổn", "bình tĩnh")):
        return ["Hope"]
    return list(get_mbi_contract(stage_id).default_yalom_factors)
