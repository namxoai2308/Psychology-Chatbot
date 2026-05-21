from __future__ import annotations

from ai_engine.blackboard.ba_contract import get_ba_contract, is_ba_stage
from ai_engine.blackboard.cbt_contract import has_any, normalize_text
from ai_engine.blackboard.cbt_response_validator import CBTValidationResult, validate_cbt_therapist_response
from ai_engine.blackboard.mbi_contract import get_mbi_contract, is_mbi_stage


def validate_therapist_response(current_stage: str, doctor_speech: str, user_message: str = "") -> CBTValidationResult:
    if is_mbi_stage(current_stage):
        return _validate_contract_stage(current_stage, doctor_speech, user_message, get_mbi_contract(current_stage))
    if is_ba_stage(current_stage):
        return _validate_contract_stage(current_stage, doctor_speech, user_message, get_ba_contract(current_stage))
    return validate_cbt_therapist_response(current_stage, doctor_speech, user_message)


def _validate_contract_stage(current_stage: str, doctor_speech: str, user_message: str, contract) -> CBTValidationResult:
    text = normalize_text(doctor_speech)
    scores = _quality_scores(current_stage, text, user_message, contract.therapist_required_patterns)
    forbidden = [pattern for pattern in contract.therapist_forbidden_patterns if pattern in text]
    if forbidden:
        return CBTValidationResult(
            False,
            f"{current_stage} contains forbidden pattern(s): {', '.join(forbidden)}.",
            contract.fallback_response,
            True,
            scores,
        )
    if not _has_required_route_pattern(current_stage, text, contract.therapist_required_patterns):
        return CBTValidationResult(
            False,
            f"{current_stage} missing required route technique pattern.",
            contract.fallback_response,
            True,
            scores,
        )
    return CBTValidationResult(True, f"{current_stage} satisfies route response contract.", doctor_speech, False, scores)


def _has_required_route_pattern(current_stage: str, text: str, required_patterns: tuple[str, ...]) -> bool:
    if current_stage == "mbi_stage_1_grounding":
        return has_any(text, ("thở", "thở ra", "bàn chân", "chạm sàn", "xuống sàn", "nhìn thấy", "đang nhìn", "nghe thấy", "hiện tại", "cảm nhận"))
    if current_stage == "mbi_stage_2_decentering":
        return has_any(text, ("mình đang có suy nghĩ", "quan sát", "ý nghĩ", "đi qua", "bị cuốn", "gọi tên"))
    if current_stage == "ba_stage_1_energy_check":
        return has_any(text, ("năng lượng", "pin", "/10", "0 đến 10", "mức", "cạn", "kiệt", "mấy phần"))
    return has_any(text, required_patterns)


def _quality_scores(current_stage: str, normalized_speech: str, user_message: str, required_patterns: tuple[str, ...]) -> dict[str, int]:
    user_terms = [term for term in normalize_text(user_message).split() if len(term) >= 4][:8]
    return {
        "stage_fit": 2 if _has_required_route_pattern(current_stage, normalized_speech, required_patterns) else 0,
        "specificity": 2 if user_terms and any(term in normalized_speech for term in user_terms) else 1 if user_terms else 0,
        "empathy": 2 if has_any(normalized_speech, ("nghe", "hiểu", "cảm giác", "mình", "bạn")) else 1,
        "focus": 2 if normalized_speech.count("?") <= 1 else 1,
        "safety": 0 if has_any(normalized_speech, ("bạn phải", "chắc chắn sẽ ổn", "cố lên là được")) else 2,
    }
