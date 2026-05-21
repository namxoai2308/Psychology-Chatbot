from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_contract import normalize_text


class CaseFormulation(BaseModel):
    presenting_problem: str = ""
    core_beliefs: list[str] = Field(default_factory=list)
    automatic_thoughts: list[str] = Field(default_factory=list)
    cognitive_distortions: list[str] = Field(default_factory=list)
    maintaining_factors: list[str] = Field(default_factory=list)
    protective_factors: list[str] = Field(default_factory=list)
    avoidance_patterns: list[str] = Field(default_factory=list)
    relapse_signals: list[str] = Field(default_factory=list)
    therapy_hypothesis: str = ""
    next_intervention_rationale: str = ""


def build_case_formulation(
    *,
    route: str,
    current_stage: str,
    user_message: str,
    chat_history: str = "",
    previous: dict[str, Any] | None = None,
    evidence_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous_formulation = _coerce_previous(previous)
    text = normalize_text(f"{chat_history}\n{user_message}")
    latest = normalize_text(user_message)
    evidence_details = evidence_details or {}

    formulation = previous_formulation.model_copy(deep=True)
    formulation.presenting_problem = _first_non_empty(
        formulation.presenting_problem,
        _presenting_problem(latest),
        "Chưa đủ dữ liệu; tiếp tục lắng nghe vấn đề chính của user.",
    )

    if route.upper() == "CBT":
        _update_cbt_formulation(formulation, latest, evidence_details)
    elif route.upper() == "MBI":
        _update_mbi_formulation(formulation, latest, text)
    elif route.upper() == "BA":
        _update_ba_formulation(formulation, latest, text)

    if any(token in text for token in ("bạn bè", "gia đình", "thầy cô", "người yêu", "phòng", "ký túc")):
        _append_unique(formulation.maintaining_factors, "interpersonal_or_context_pressure")
    if any(token in text for token in ("mình thử", "có lẽ", "nhận ra", "muốn", "đã làm", "xong rồi")):
        _append_unique(formulation.protective_factors, "reflection_or_willingness")
    if any(token in text for token in ("né", "tránh", "nằm lì", "lướt", "không dám", "trì hoãn")):
        _append_unique(formulation.avoidance_patterns, "avoidance_or_shutdown")
    if any(token in latest for token in ("lại", "vẫn", "quay lại", "không kiểm soát", "tái")):
        _append_unique(formulation.relapse_signals, "recurring_distress_or_automatic_pattern")

    formulation.therapy_hypothesis = _therapy_hypothesis(route, current_stage, formulation)
    formulation.next_intervention_rationale = _next_intervention_rationale(route, current_stage, formulation)
    return formulation.model_dump()


def format_case_formulation(formulation: dict[str, Any] | None) -> str:
    if not formulation:
        return "No case formulation available yet."
    data = CaseFormulation.model_validate(formulation)
    lines = [
        f"- presenting_problem: {data.presenting_problem or 'unknown'}",
        f"- automatic_thoughts: {_join(data.automatic_thoughts)}",
        f"- cognitive_distortions: {_join(data.cognitive_distortions)}",
        f"- maintaining_factors: {_join(data.maintaining_factors)}",
        f"- protective_factors: {_join(data.protective_factors)}",
        f"- avoidance_patterns: {_join(data.avoidance_patterns)}",
        f"- relapse_signals: {_join(data.relapse_signals)}",
        f"- therapy_hypothesis: {data.therapy_hypothesis or 'unknown'}",
        f"- next_intervention_rationale: {data.next_intervention_rationale or 'unknown'}",
    ]
    if data.core_beliefs:
        lines.insert(2, f"- core_beliefs: {_join(data.core_beliefs)}")
    return "\n".join(lines)


def _coerce_previous(previous: dict[str, Any] | None) -> CaseFormulation:
    if isinstance(previous, dict):
        try:
            return CaseFormulation.model_validate(previous)
        except Exception:
            return CaseFormulation()
    return CaseFormulation()


def _update_cbt_formulation(formulation: CaseFormulation, latest: str, evidence: dict[str, Any]) -> None:
    automatic_thought = str(evidence.get("automatic_thought") or "").strip()
    if automatic_thought:
        _append_unique(formulation.automatic_thoughts, automatic_thought)
    for distortion in evidence.get("distortion_candidates") or evidence.get("distortions") or []:
        _append_unique(formulation.cognitive_distortions, str(distortion))
    if any(token in latest for token in ("vô dụng", "kém cỏi", "thất bại", "yếu đuối", "không đủ tốt")):
        _append_unique(formulation.core_beliefs, "negative_self_label_or_inadequacy")
    if any(token in latest for token in ("hỏng hết", "sụp đổ", "không còn", "xong đời", "bỏ cuộc")):
        _append_unique(formulation.cognitive_distortions, "catastrophizing")
    if any(token in latest for token in ("ai cũng nghĩ", "họ sẽ nghĩ", "chắc họ", "người khác sẽ")):
        _append_unique(formulation.cognitive_distortions, "mind_reading")


def _update_mbi_formulation(formulation: CaseFormulation, latest: str, text: str) -> None:
    if any(token in latest for token in ("tim", "thở", "run", "ngực", "khó thở", "hoảng")):
        _append_unique(formulation.maintaining_factors, "physiological_arousal")
    if any(token in text for token in ("suy nghĩ cứ chạy", "nghĩ mãi", "lặp", "quay vòng")):
        _append_unique(formulation.maintaining_factors, "rumination_loop")
    if any(token in latest for token in ("đỡ hơn", "bình tĩnh hơn", "dịu")):
        _append_unique(formulation.protective_factors, "can_notice_state_shift")


def _update_ba_formulation(formulation: CaseFormulation, latest: str, text: str) -> None:
    if any(token in text for token in ("nằm lì", "không muốn", "không ra khỏi", "bỏ học", "trì hoãn")):
        _append_unique(formulation.maintaining_factors, "low_activity_low_mood_cycle")
    if any(token in latest for token in ("2/10", "3/10", "pin", "năng lượng")):
        _append_unique(formulation.protective_factors, "can_rate_energy")
    if any(token in latest for token in ("uống nước", "rửa mặt", "mở", "nhặt", "xong", "làm rồi")):
        _append_unique(formulation.protective_factors, "micro_action_available")


def _presenting_problem(latest: str) -> str:
    if any(token in latest for token in ("thi", "môn", "học kỳ", "điểm")):
        return "Academic pressure and fear of failure."
    if any(token in latest for token in ("deadline", "đồ án", "luận văn", "bài tập")):
        return "Deadline overload and avoidance."
    if any(token in latest for token in ("bạn bè", "người yêu", "gia đình", "cô đơn")):
        return "Interpersonal distress and loneliness."
    if any(token in latest for token in ("tim", "thở", "hoảng", "ngực")):
        return "Acute anxiety or body-based distress."
    if any(token in latest for token in ("nằm lì", "không muốn", "lười", "năng lượng")):
        return "Low energy and behavioral shutdown."
    return ""


def _therapy_hypothesis(route: str, stage: str, formulation: CaseFormulation) -> str:
    if route.upper() == "CBT":
        if formulation.cognitive_distortions:
            return "Distress is being amplified by identifiable automatic thoughts and thinking traps."
        return "User needs enough emotional and situational detail before cognitive work."
    if route.upper() == "MBI":
        return "User benefits from changing relationship to sensations/thoughts before analyzing content."
    if route.upper() == "BA":
        return "Mood and avoidance may improve through very small, scheduled actions matched to energy."
    return "Supportive response should prioritize safety, context, and one next step."


def _next_intervention_rationale(route: str, stage: str, formulation: CaseFormulation) -> str:
    if "stage_1" in stage:
        return "Stabilize and validate before asking for deeper analysis."
    if "stage_2" in stage:
        return "Clarify the key mechanism without overloading the user."
    if "stage_3" in stage:
        return "Name the pattern gently and check whether it fits the user's experience."
    if "stage_4" in stage:
        return "Use one precise question to test the thought or observe the experience."
    if "stage_5" in stage:
        return "Consolidate a balanced frame and choose a realistic next action."
    return "Use the least intrusive intervention that matches current risk and readiness."


def _append_unique(items: list[str], value: str) -> None:
    value = value.strip()
    if value and value not in items:
        items.append(value)


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _join(items: list[str]) -> str:
    return ", ".join(items) if items else "none"
