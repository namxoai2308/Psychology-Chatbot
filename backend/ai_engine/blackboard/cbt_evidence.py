from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_contract import HOPE_PATTERNS, OVERLOAD_PATTERNS, has_any, normalize_text


class CBTEvidence(BaseModel):
    emotion_present: bool = Field(default=False)
    event_present: bool = Field(default=False)
    abc_present: bool = Field(default=False)
    automatic_thought: str = Field(default="")
    automatic_thought_present: bool = Field(default=False)
    distortion_candidates: list[str] = Field(default_factory=list)
    distortion_reflection: bool = Field(default=False)
    socratic_reasoning: bool = Field(default=False)
    insight_present: bool = Field(default=False)
    balanced_reframe: bool = Field(default=False)
    action_step: bool = Field(default=False)
    action_commitment: bool = Field(default=False)
    peer_boundary_intent: bool = Field(default=False)
    overload: bool = Field(default=False)
    hope_request: bool = Field(default=False)
    confidence: float = Field(default=0.68)
    evidence_quotes: list[str] = Field(default_factory=list)
    source: str = Field(default="heuristic")

    @property
    def has_automatic_thought(self) -> bool:
        return bool(self.automatic_thought_present or self.automatic_thought.strip() or self.distortion_candidates)


def cbt_evidence_from_mapping(data: dict[str, Any] | None, user_message: str = "") -> CBTEvidence:
    if not isinstance(data, dict):
        return extract_cbt_evidence_heuristic(user_message)
    try:
        evidence = CBTEvidence.model_validate(data)
    except Exception:
        return extract_cbt_evidence_heuristic(user_message)
    if not evidence.evidence_quotes and user_message:
        evidence.evidence_quotes = [user_message]
    return evidence


def extract_cbt_evidence_heuristic(user_message: str, chat_history: str = "") -> CBTEvidence:
    msg = normalize_text(user_message)
    quotes = [user_message] if user_message else []
    distortions = _distortion_candidates(msg)
    automatic = _automatic_thought_text(user_message, msg, distortions)
    insight = _has_insight(msg)
    reframe = _has_balanced_reframe(msg)
    action = _has_action_step(msg)
    automatic_present = bool(automatic or distortions or _has_thought_marker(msg))
    abc_present = _has_abc_signal(msg)
    distortion_reflection = _has_distortion_reflection(msg, distortions)
    socratic_reasoning = _has_socratic_reasoning(msg)
    action_commitment = _has_action_commitment(msg)
    return CBTEvidence(
        emotion_present=_has_emotion(msg),
        event_present=_has_event_context(msg),
        abc_present=abc_present,
        automatic_thought=automatic,
        automatic_thought_present=automatic_present,
        distortion_candidates=distortions,
        distortion_reflection=distortion_reflection,
        socratic_reasoning=socratic_reasoning,
        insight_present=insight,
        balanced_reframe=reframe,
        action_step=action,
        action_commitment=action_commitment,
        peer_boundary_intent=_has_peer_boundary_intent(msg),
        overload=has_any(msg, OVERLOAD_PATTERNS),
        hope_request=has_any(msg, HOPE_PATTERNS),
        confidence=_heuristic_confidence(
            msg,
            automatic,
            distortions,
            insight,
            reframe,
            action,
            abc_present,
            distortion_reflection,
            socratic_reasoning,
        ),
        evidence_quotes=quotes,
        source="heuristic",
    )


def sanitize_llm_cbt_evidence(evidence: CBTEvidence, user_message: str) -> CBTEvidence:
    """Remove inferred CBT labels when the user did not actually state a thought."""
    msg = normalize_text(user_message)
    automatic = (evidence.automatic_thought or "").strip()
    thought_marked = _has_thought_marker(msg)
    quoted_thought = bool(automatic and _has_thought_marker(normalize_text(automatic)))
    if evidence.hope_request and not evidence.insight_present and not evidence.balanced_reframe:
        evidence.automatic_thought = ""
        evidence.automatic_thought_present = False
        evidence.distortion_candidates = []
        evidence.distortion_reflection = False
    elif evidence.distortion_candidates and not (thought_marked or quoted_thought):
        evidence.distortion_candidates = []
    if evidence.automatic_thought and not (thought_marked or quoted_thought or evidence.distortion_candidates):
        evidence.automatic_thought = ""
    evidence.automatic_thought_present = bool(
        evidence.automatic_thought_present
        or evidence.automatic_thought.strip()
        or evidence.distortion_candidates
        or _has_thought_marker(msg)
    )
    evidence.abc_present = bool(evidence.abc_present or _has_abc_signal(msg))
    evidence.distortion_reflection = bool(evidence.distortion_reflection or _has_distortion_reflection(msg, evidence.distortion_candidates))
    evidence.socratic_reasoning = bool(evidence.socratic_reasoning or _has_socratic_reasoning(msg))
    evidence.action_commitment = bool(evidence.action_commitment or _has_action_commitment(msg))
    evidence.peer_boundary_intent = bool(evidence.peer_boundary_intent or _has_peer_boundary_intent(msg))
    return evidence


def _has_emotion(text: str) -> bool:
    return has_any(
        text,
        (
            "mệt",
            "áp lực",
            "buồn",
            "tức",
            "không chịu nổi",
            "rối",
            "căng thẳng",
            "bỏ cuộc",
            "đen tối",
            "xấu hổ",
            "trống rỗng",
            "hồi hộp",
            "hụt hẫng",
            "nặng nề",
            "bồn chồn",
            "ngợp",
            "chán",
            "có lỗi",
            "tội lỗi",
            "quê",
            "bị bỏ rơi",
            "mất ngủ",
            "căng",
            "nghĩ lại mãi",
            "lo",
            "sợ",
            "hoảng",
            "đau",
            "nghẹn",
            "kiệt sức",
            "nản",
            "đuối",
        ),
    )


def _has_event_context(text: str) -> bool:
    return has_any(
        text,
        (
            "hôm qua",
            "tối qua",
            "hôm nay",
            "mai",
            "vừa",
            "từ lúc",
            "khi",
            "lúc",
            "bị",
            "sau đó",
            "điểm",
            "deadline",
            "phỏng vấn",
            "cuộc họp",
            "sếp nhắc",
            "trả lời",
            "nói sai",
            "lam khong tot",
            "làm không tốt",
            "bài nhóm",
            "học bổng",
            "thực tập",
            "thuyết trình",
            "luận văn",
            "bố mẹ",
            "cãi nhau",
            "không trả lời",
            "chia tay",
            "tin nhắn",
            "đau đầu",
            "dọn phòng",
            "nhóm làm bài",
        ),
    )


def _has_abc_signal(text: str) -> bool:
    abc_terms = (
        "sự kiện",
        "su kien",
        "tình huống",
        "tinh huong",
        "cảm xúc",
        "cam xuc",
        "suy nghĩ",
        "suy nghi",
        "câu bật lên",
        "cau bat len",
        "trong đầu",
        "trong dau",
        "tự nói",
        "tu noi",
        "kết luận",
        "ket luan",
    )
    if has_any(text, abc_terms):
        return True
    return (
        _has_event_context(text)
        and (_has_emotion(text) or _has_thought_marker(text))
        and not _venting_continuation(text)
    )


def _venting_continuation(text: str) -> bool:
    return has_any(
        text,
        (
            "đang rất căng thẳng vì",
            "dang rat cang thang vi",
            "nó làm mình thấy",
            "no lam minh thay",
            "điều đó làm mình",
            "dieu do lam minh",
            "chuyện đó làm mình",
            "chuyen do lam minh",
            "muốn tránh mọi thứ",
            "muon tranh moi thu",
        ),
    )


def _automatic_thought_text(original: str, normalized: str, distortions: list[str]) -> str:
    if not distortions and not _has_thought_marker(normalized):
        return ""
    return original.strip()


def _has_thought_marker(text: str) -> bool:
    return (
        has_any(
            text,
            (
                "mình nghĩ chắc",
                "mình nghĩ là",
                "mình nghĩ nếu",
                "tôi nghĩ chắc",
                "tôi nghĩ là",
                "tôi nghĩ nếu",
                "em nghĩ chắc",
                "em nghĩ là",
                "em nghĩ nếu",
                "cứ nghĩ chắc",
                "cứ nghĩ nếu",
                "tự nói",
                "chắc",
                "chắc chắn",
                "coi như",
            ),
        )
        or bool(re.search(r"\bnếu\b.+\bthì\b", text))
    )


def _distortion_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    if has_any(text, ("hỏng hết", "phá hỏng", "pha hong", "sụp đổ", "không bao giờ", "chắc chắn", "bệnh gì đó rất nặng", "đóng lại", "mắc kẹt mãi")):
        candidates.append("catastrophizing")
    if has_any(text, ("hoàn toàn", "tất cả", "một lần", "hết cả", "thất bại hoàn toàn", "môn nào", "ai thân rồi cũng", "mãi mãi", "mãi ở đây")):
        candidates.append("all_or_nothing")
    if has_any(text, ("ai cũng", "cả lớp thấy", "mọi người nghĩ", "mọi người sẽ nghĩ", "mọi người sẽ đánh giá", "chắc họ nghĩ", "người ta nghĩ", "người ta thấy", "bạn ấy ghét", "họ ghét", "không muốn chơi", "đang né", "cố tình loại")):
        candidates.append("mind_reading")
    if (
        bool(re.search(r"\b(mình|tôi|em)\s+là\b", text))
        or has_any(text, ("đúng là", "vô dụng", "kém cỏi", "vô kỷ luật", "chẳng ra gì", "ngu", "lười", "học dốt", "thiếu năng lực"))
    ):
        candidates.append("labeling")
    if has_any(text, ("tại mình", "do mình", "vì mình mà", "mình gây ra")) or (
        "lỗi của mình" in text and not has_any(text, ("nhắc lỗi của mình", "sửa lỗi của mình"))
    ):
        candidates.append("personalization")
    if re.search(r"\bnếu\b.+\bthì\b", text) and not candidates:
        candidates.append("conditional_catastrophizing")
    return candidates


def _has_distortion_reflection(text: str, distortions: list[str]) -> bool:
    reflection_terms = (
        "cực đoan",
        "cuc doan",
        "tuyệt đối",
        "tuyet doi",
        "phóng đại",
        "phong dai",
        "quá mức",
        "qua muc",
        "nặng hơn thực tế",
        "nang hon thuc te",
        "bẫy tư duy",
        "bay tu duy",
        "lỗi tư duy",
        "loi tu duy",
        "mẫu suy nghĩ",
        "mau suy nghi",
        "kiểu nghĩ",
        "kieu nghi",
        "thảm họa",
        "tham hoa",
        "đọc tâm trí",
        "doc tam tri",
        "dán nhãn",
        "dan nhan",
        "trắng đen",
        "trang den",
        "khái quát",
        "khai quat",
    )
    if has_any(text, reflection_terms):
        return True
    return bool(distortions and has_any(text, ("nghĩ", "nghi", "kết luận", "ket luan", "tự nói", "tu noi")))


def _has_insight(text: str) -> bool:
    return has_any(
        text,
        (
            "phóng đại",
            "cực đoan",
            "hơi quá",
            "lo quá mức",
            "không hoàn toàn đúng",
            "quá tuyệt đối",
            "tuyệt đối",
            "nhảy quá xa",
            "không thể chắc",
            "không chắc",
            "không có bằng chứng chắc chắn",
            "chưa có bằng chứng chắc chắn",
            "chưa có bằng chứng",
            "chưa chắc",
            "đang đoán",
            "suy diễn",
            "không công bằng",
            "không có bằng chứng",
            "không phải tất cả",
            "vơ đũa cả nắm",
            "không đồng nghĩa",
            "không chứng minh",
            "không nói hết",
            "không phải toàn bộ",
            "không phải là thảm họa",
            "không phải thảm họa",
            "nặng hơn thực tế",
            "có thể còn lý do khác",
        ),
    )


def _has_socratic_reasoning(text: str) -> bool:
    return has_any(
        text,
        (
            "bằng chứng",
            "bang chung",
            "dữ kiện",
            "du kien",
            "có chắc",
            "co chac",
            "chưa chắc",
            "chua chac",
            "không chắc",
            "khong chac",
            "khả năng khác",
            "kha nang khac",
            "góc nhìn khác",
            "goc nhin khac",
            "mặt khác",
            "mat khac",
            "nếu là bạn",
            "neu la ban",
            "người bạn",
            "nguoi ban",
            "mình sẽ nói",
            "minh se noi",
            "kết luận này có đúng",
            "ket luan nay co dung",
        ),
    )


def _has_balanced_reframe(text: str) -> bool:
    return has_any(
        text,
        (
            "không có nghĩa",
            "vẫn còn cơ hội",
            "có thể sửa",
            "sửa được",
            "cân bằng hơn",
            "câu cân bằng",
            "cau can bang",
            "không phải là hết",
            "không đồng nghĩa",
            "không chứng minh",
            "không nói hết",
            "không phải toàn bộ",
            "không phải là thảm họa",
            "không phải thảm họa",
            "không phải chứng minh tất cả",
            "một lỗi nhỏ không có nghĩa",
        ),
    )


def _has_action_step(text: str) -> bool:
    return has_any(
        text,
        (
            "một bước nhỏ",
            "học 15 phút",
            "làm thử",
            "tiếp theo",
            "sẽ thử",
            "sẽ học",
            "sẽ làm",
            "luyện lại",
            "giữ câu cân bằng",
            "giu cau can bang",
            "dùng lại",
            "dung lai",
            "thử",
        ),
    ) or bool(re.search(r"\b(5|10|15|20|30|45|60)\s*phút\b", text))


def _has_action_commitment(text: str) -> bool:
    if not _has_action_step(text):
        return False
    commitment_markers = (
        "mình sẽ",
        "minh se",
        "tôi sẽ",
        "toi se",
        "em sẽ",
        "em se",
        "mình có thể",
        "minh co the",
        "tôi có thể",
        "toi co the",
        "em có thể",
        "em co the",
        "mình thử",
        "minh thu",
        "tôi thử",
        "toi thu",
        "em thử",
        "em thu",
        "mình muốn giữ",
        "minh muon giu",
        "hôm nay",
        "hom nay",
        "tối nay",
        "toi nay",
    )
    return has_any(text, commitment_markers) or bool(re.search(r"\b(5|10|15|20|30|45|60)\s*phút\b", text))


def _has_peer_boundary_intent(text: str) -> bool:
    peer_terms = (
        "peer",
        "bạn đồng hành",
        "ban dong hanh",
        "người khác chia sẻ",
        "nguoi khac chia se",
        "nhóm",
        "nhom",
        "nam",
        "linh",
    )
    boundary_terms = (
        "nói quá nhiều",
        "noi qua nhieu",
        "quá nhiều",
        "qua nhieu",
        "bị loãng",
        "bi loang",
        "loãng",
        "loang",
        "dừng lại",
        "dung lai",
        "ít lại",
        "it lai",
        "tập trung",
        "tap trung",
        "vấn đề chính",
        "van de chinh",
        "quay lại",
        "quay lai",
        "nhà trị liệu",
        "nha tri lieu",
        "quyết định cuối",
        "quyet dinh cuoi",
        "không phụ thuộc",
        "khong phu thuoc",
    )
    return has_any(text, boundary_terms) and (
        has_any(text, peer_terms)
        or has_any(text, ("nhà trị liệu", "nha tri lieu", "vấn đề chính", "van de chinh", "quyết định cuối", "quyet dinh cuoi"))
    )


def _heuristic_confidence(
    text: str,
    automatic: str,
    distortions: list[str],
    insight: bool,
    reframe: bool,
    action: bool,
    abc_present: bool = False,
    distortion_reflection: bool = False,
    socratic_reasoning: bool = False,
) -> float:
    score = 0.66
    if abc_present:
        score += 0.05
    if automatic or distortions:
        score += 0.12
    if distortion_reflection:
        score += 0.08
    if socratic_reasoning:
        score += 0.08
    if insight:
        score += 0.1
    if reframe:
        score += 0.1
    if action:
        score += 0.04
    if _has_emotion(text) or _has_event_context(text):
        score += 0.04
    return min(score, 0.92)
