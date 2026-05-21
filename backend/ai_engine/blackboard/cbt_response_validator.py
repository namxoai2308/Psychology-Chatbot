from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.cbt_contract import (
    cbt_detect_distortion,
    get_cbt_contract,
    has_any,
    is_cbt_stage,
    normalize_text,
)


@dataclass(frozen=True)
class CBTValidationResult:
    valid: bool
    reason: str
    fallback_response: str
    fallback_used: bool = False
    quality_scores: dict[str, int] | None = None


def validate_cbt_therapist_response(current_stage: str, doctor_speech: str, user_message: str = "") -> CBTValidationResult:
    if not is_cbt_stage(current_stage):
        return CBTValidationResult(True, "Not a CBT stage; validator skipped.", doctor_speech, False, {})

    contract = get_cbt_contract(current_stage)
    text = normalize_text(doctor_speech)
    scores = _quality_scores(current_stage, text, user_message)

    forbidden = [pattern for pattern in contract.therapist_forbidden_patterns if pattern in text]
    if forbidden:
        return CBTValidationResult(
            False,
            f"{current_stage} contains forbidden pattern(s): {', '.join(forbidden)}.",
            _fallback_for_stage(current_stage, user_message),
            True,
            scores,
        )

    required_hit = has_any(text, contract.therapist_required_patterns)
    if not required_hit:
        return CBTValidationResult(
            False,
            f"{current_stage} missing required CBT technique pattern.",
            _fallback_for_stage(current_stage, user_message),
            True,
            scores,
        )

    return CBTValidationResult(True, f"{current_stage} satisfies CBT response contract.", doctor_speech, False, scores)


def _quality_scores(current_stage: str, normalized_speech: str, user_message: str) -> dict[str, int]:
    user_terms = _content_terms(user_message)
    specificity = 2 if user_terms and any(term in normalized_speech for term in user_terms) else 1 if user_terms else 0
    empathy = 2 if has_any(normalized_speech, ("nghe", "hiểu", "dễ hiểu", "nặng", "áp lực", "ở đây", "cảm giác")) else 1
    technique = 2 if has_any(normalized_speech, get_cbt_contract(current_stage).therapist_required_patterns) else 0
    question_count = normalized_speech.count("?")
    focus = 2 if question_count <= 1 else 1
    safety = 0 if has_any(normalized_speech, ("bạn nên", "bạn phải", "chắc chắn sẽ ổn", "mắc bệnh")) else 2
    return {
        "stage_fit": technique,
        "specificity": specificity,
        "empathy": empathy,
        "focus": focus,
        "safety": safety,
    }


def _content_terms(text: str) -> list[str]:
    normalized = normalize_text(text)
    stopwords = {
        "mình",
        "tôi",
        "em",
        "bạn",
        "và",
        "là",
        "thì",
        "nếu",
        "có",
        "không",
        "rất",
        "với",
        "một",
        "này",
        "đó",
        "rồi",
        "lắm",
    }
    return [word for word in normalized.split() if len(word) >= 4 and word not in stopwords][:10]


def _fallback_for_stage(current_stage: str, user_message: str = "") -> str:
    contract = get_cbt_contract(current_stage)
    if current_stage == "cbt_stage_3_distortions":
        distortion = cbt_detect_distortion(user_message)
        if distortion == "catastrophizing":
            return (
                "Câu đó nghe giống một cái bẫy thảm họa hóa: não đang kéo khả năng xấu nhất thành kết luận rất tuyệt đối. "
                "Bạn thấy suy nghĩ này có đang phóng đại hậu quả lên không?"
            )
        if distortion == "all_or_nothing":
            return (
                "Câu đó nghe giống bẫy trắng-đen: hoặc hoàn hảo, hoặc xem như thất bại toàn bộ. "
                "Bạn thấy suy nghĩ này có đang bỏ qua những vùng ở giữa không?"
            )
        if distortion == "mind_reading":
            return (
                "Câu đó nghe giống bẫy đọc tâm trí: mình đoán chắc người khác đang nghĩ xấu về mình dù chưa có đủ dữ kiện. "
                "Bạn thấy phần nào trong suy nghĩ đó là điều mình đang tự đoán không?"
            )
        if distortion == "labeling":
            return (
                "Câu đó nghe giống bẫy dán nhãn: lấy một kết quả hoặc một cảm giác để kết luận toàn bộ con người mình. "
                "Bạn thấy nhãn đó có đang quá nặng so với sự việc thật không?"
            )
    return contract.fallback_response
