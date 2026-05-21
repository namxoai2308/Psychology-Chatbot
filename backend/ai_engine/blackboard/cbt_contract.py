from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class CBTStageContract:
    stage_id: str
    stage_goal: str
    entry_patterns: tuple[str, ...]
    completion_patterns: tuple[str, ...]
    allowed_yalom_factors: tuple[str, ...]
    default_yalom_factors: tuple[str, ...]
    therapist_required_patterns: tuple[str, ...]
    therapist_forbidden_patterns: tuple[str, ...]
    peer_policy: dict[str, str]
    fallback_response: str


CBT_STAGES = [
    "cbt_stage_1_venting",
    "cbt_stage_2_abc_model",
    "cbt_stage_3_distortions",
    "cbt_stage_4_socratic",
    "cbt_stage_5_action",
]


CBT_CONTRACTS: dict[str, CBTStageContract] = {
    "cbt_stage_1_venting": CBTStageContract(
        stage_id="cbt_stage_1_venting",
        stage_goal="Validate emotion, invite more context, do not challenge thoughts yet.",
        entry_patterns=("mệt", "áp lực", "buồn", "tức", "không chịu nổi", "rối", "căng thẳng", "bỏ cuộc", "bi đát", "đen tối"),
        completion_patterns=("vừa", "khi", "lúc", "bị", "sau đó", "điểm thấp", "deadline", "sếp nói", "bạn nói"),
        allowed_yalom_factors=("Universality", "Catharsis", "Hope", "Interpersonal Learning"),
        default_yalom_factors=("Universality", "Catharsis"),
        therapist_required_patterns=("nghe", "hiểu", "dễ hiểu", "nặng", "áp lực", "ở đây", "cảm giác", "nỗi sợ", "cô đơn", "đè lên"),
        therapist_forbidden_patterns=("bằng chứng", "100%", "thảm họa hóa", "suy nghĩ tự động", "lỗi tư duy"),
        peer_policy={
            "peer_mirror_agent": "May contribute for Universality/Catharsis unless Hope is the primary factor.",
            "veteran_peer_agent": "May contribute only when the user explicitly asks whether recovery is possible.",
        },
        fallback_response=(
            "Nghe vậy thì việc bạn thấy nặng nề là rất dễ hiểu. "
            "Trong chuyện này, phần nào đang khiến bạn muốn bỏ cuộc hoặc thấy khó chịu nhất?"
        ),
    ),
    "cbt_stage_2_abc_model": CBTStageContract(
        stage_id="cbt_stage_2_abc_model",
        stage_goal="Separate event, automatic thought, and emotional consequence.",
        entry_patterns=("vừa", "khi", "lúc", "bị", "sau đó", "điểm thấp", "deadline", "sếp nói", "bạn nói", "không trả lời"),
        completion_patterns=("nếu", "thì", "coi như", "hỏng hết", "vô dụng", "thất bại", "ai cũng", "chắc chắn"),
        allowed_yalom_factors=("NONE", "Catharsis"),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("sự kiện", "suy nghĩ tự động", "tự nói", "khoảnh khắc", "câu bật lên", "câu đầu tiên", "trong đầu"),
        therapist_forbidden_patterns=("thảm họa hóa", "bẫy tư duy", "bằng chứng nào", "100%"),
        peer_policy={
            "peer_mirror_agent": "Usually no contribution; only short catharsis if the user is still emotionally flooded.",
            "veteran_peer_agent": "No contribution by default.",
        },
        fallback_response=(
            "Mình tách nhẹ ra một chút nhé: sự kiện là điều đã xảy ra, còn phần làm cảm xúc tăng mạnh là câu bạn tự nói với mình. "
            "Ngay khoảnh khắc đó, suy nghĩ tự động đầu tiên xuất hiện là gì?"
        ),
    ),
    "cbt_stage_3_distortions": CBTStageContract(
        stage_id="cbt_stage_3_distortions",
        stage_goal="Name one possible thinking trap gently.",
        entry_patterns=("nếu", "thì", "coi như", "hỏng hết", "vô dụng", "thất bại", "ai cũng", "chắc chắn", "mãi mãi"),
        completion_patterns=("phóng đại", "cực đoan", "không hoàn toàn đúng", "có lẽ", "hơi quá", "lo quá mức"),
        allowed_yalom_factors=("Universality", "Hope"),
        default_yalom_factors=("Universality",),
        therapist_required_patterns=("thảm họa", "trắng đen", "đọc tâm trí", "dán nhãn", "bẫy", "phóng đại", "tuyệt đối"),
        therapist_forbidden_patterns=("bằng chứng nào", "100%", "hãy kể thêm", "suy nghĩ và cảm xúc"),
        peer_policy={
            "peer_mirror_agent": "May contribute briefly for Universality when the user self-blames or feels alone.",
            "veteran_peer_agent": "May contribute only when automatic thought is hopelessness-oriented.",
        },
        fallback_response=(
            "Câu đó nghe giống một cái bẫy thảm họa hóa: não đang kéo khả năng xấu nhất thành kết luận rất tuyệt đối. "
            "Bạn thấy suy nghĩ này có đang phóng đại hậu quả lên không?"
        ),
    ),
    "cbt_stage_4_socratic": CBTStageContract(
        stage_id="cbt_stage_4_socratic",
        stage_goal="Ask one evidence-testing or double-standard Socratic question.",
        entry_patterns=("phóng đại", "cực đoan", "không hoàn toàn đúng", "có lẽ", "hơi quá", "lo quá mức"),
        completion_patterns=("không có nghĩa", "vẫn còn cơ hội", "có thể sửa", "sửa được", "cân bằng hơn", "không phải là hết", "bước nhỏ", "hôm nay"),
        allowed_yalom_factors=("NONE",),
        default_yalom_factors=("NONE",),
        therapist_required_patterns=("bằng chứng", "100%", "tuyệt đối", "bạn thân", "góc nhìn"),
        therapist_forbidden_patterns=("hãy cho tôi biết thêm", "kể thêm", "suy nghĩ và cảm xúc", "cơ hội nào để thay đổi"),
        peer_policy={
            "peer_mirror_agent": "No contribution.",
            "veteran_peer_agent": "No contribution.",
        },
        fallback_response=(
            "Bạn đã nhận ra điểm rất quan trọng: suy nghĩ ấy có thể đang phóng đại, dù cảm giác vẫn tự động bật lên. "
            "Có bằng chứng nào cho thấy kết luận đó đúng 100%, và có bằng chứng nào làm nó bớt tuyệt đối hơn?"
        ),
    ),
    "cbt_stage_5_action": CBTStageContract(
        stage_id="cbt_stage_5_action",
        stage_goal="Help user formulate balanced thought and one next step.",
        entry_patterns=("không có nghĩa", "vẫn còn cơ hội", "có thể sửa", "sửa được", "cân bằng hơn", "không phải là hết", "bước nhỏ", "hôm nay"),
        completion_patterns=("bước nhỏ", "hôm nay", "làm thử", "kế hoạch", "tiếp theo"),
        allowed_yalom_factors=("Hope", "Interpersonal Learning"),
        default_yalom_factors=("Hope", "Interpersonal Learning"),
        therapist_required_patterns=("không có nghĩa", "cơ hội", "bước nhỏ", "hôm nay", "thử", "tiếp theo"),
        therapist_forbidden_patterns=("bằng chứng nào", "100%", "hãy kể thêm", "lỗi tư duy"),
        peer_policy={
            "peer_mirror_agent": "No contribution by default.",
            "veteran_peer_agent": "May contribute with short Hope/Interpersonal Learning.",
        },
        fallback_response=(
            "Mình thử đóng gói nó thành một câu công bằng hơn: một kết quả không như ý không có nghĩa là hết cơ hội sửa. "
            "Một bước nhỏ thực tế bạn có thể làm trong hôm nay là gì?"
        ),
    ),
}


HOPE_PATTERNS = (
    "muốn bỏ cuộc",
    "bỏ cuộc",
    "vực dậy",
    "có ai từng",
    "không biết có ai",
    "đen tối",
    "bi đát",
    "không còn hy vọng",
    "hết hy vọng",
    "khá lên",
    "không bao giờ khá",
)


OVERLOAD_PATTERNS = ("không thở", "khó thở", "tim đập", "hoảng", "run", "quay cuồng")


def normalize_text(text: str) -> str:
    text = re.sub(r"[^\w\s/]", " ", text.lower(), flags=re.UNICODE)
    return " ".join(text.strip().split())


def has_any(text: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def has_regex(text: str, pattern: str | Pattern[str]) -> bool:
    return bool(re.search(pattern, text))


def get_cbt_contract(stage_id: str) -> CBTStageContract:
    return CBT_CONTRACTS.get(stage_id, CBT_CONTRACTS["cbt_stage_1_venting"])


def cbt_stage_goal(stage_id: str) -> str:
    return get_cbt_contract(stage_id).stage_goal


def is_cbt_stage(stage_id: str | None) -> bool:
    return bool(stage_id and stage_id in CBT_CONTRACTS)


def cbt_default_yalom(stage_id: str, user_message: str = "") -> list[str]:
    msg = normalize_text(user_message)
    if stage_id == "cbt_stage_1_venting" and has_any(
        msg,
        (
            "phóng đại",
            "phong dai",
            "bị kéo theo",
            "bi keo theo",
            "suy nghĩ đó hơi",
            "suy nghi do hoi",
            "suy nghĩ đó có lẽ",
            "suy nghi do co le",
            "nghe ai đó",
            "nghe ai do",
            "từng trải qua chuyện tương tự",
            "tung trai qua chuyen tuong tu",
            "một phần mình muốn được nghe",
            "mot phan minh muon duoc nghe",
            "nhà trị liệu giúp",
            "nha tri lieu giup",
            "nhìn rõ bước tiếp theo",
            "nhin ro buoc tiep theo",
        ),
    ):
        return ["NONE"]
    if stage_id == "cbt_stage_1_venting" and has_any(
        msg,
        (
            "ban cung phong",
            "ban cung phòng",
            "khong biet noi sao",
            "không biết nói sao",
            "lam moi thu te hon",
            "làm mọi thứ tệ hơn",
            "giao tiep",
            "giao tiếp",
            "moi quan he",
            "mối quan hệ",
        ),
    ):
        return ["Interpersonal Learning"]
    if stage_id == "cbt_stage_1_venting" and has_any(msg, HOPE_PATTERNS):
        return ["Hope"]
    if stage_id == "cbt_stage_3_distortions" and has_any(msg, HOPE_PATTERNS):
        return ["Hope"]
    return list(get_cbt_contract(stage_id).default_yalom_factors)


def cbt_allowed_yalom(stage_id: str) -> set[str]:
    return set(get_cbt_contract(stage_id).allowed_yalom_factors)


def cbt_peer_allowed(stage_id: str, sender: str, factors: list[str]) -> bool:
    if not factors or "NONE" in factors:
        return False
    if sender == "peer_mirror_agent":
        return bool({"Universality", "Catharsis"} & set(factors))
    if sender == "veteran_peer_agent":
        return bool({"Hope", "Interpersonal Learning"} & set(factors))
    return False


def cbt_detect_distortion(user_message: str) -> str:
    msg = normalize_text(user_message)
    if has_any(msg, ("hỏng hết", "đời mình hỏng", "sụp đổ", "đen tối", "không bao giờ")):
        return "catastrophizing"
    if has_any(msg, ("một lần", "đều thất bại", "không có năng lực", "hoàn toàn", "tất cả")):
        return "all_or_nothing"
    if has_any(msg, ("ai cũng", "mọi người sẽ nghĩ", "chắc họ nghĩ", "người ta nghĩ")):
        return "mind_reading"
    if has_any(msg, ("mình là", "tôi là", "vô dụng", "kém cỏi", "thất bại")):
        return "labeling"
    return "generic_distortion"
