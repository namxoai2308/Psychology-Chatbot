from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_contract import normalize_text
from ai_engine.services.safety import is_crisis_input, is_unsafe_output

Severity = Literal["none", "low", "medium", "high"]


class SafetyCriticResult(BaseModel):
    critic: str
    severity: Severity = "none"
    triggered: bool = False
    reason: str = ""


class PsychosocialSafetyReport(BaseModel):
    overall_severity: Severity = "none"
    critics: list[SafetyCriticResult] = Field(default_factory=list)
    high_risk: bool = False
    medium_risk: bool = False


SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def assess_psychosocial_safety(
    *,
    user_message: str = "",
    assistant_text: str = "",
    chat_history: str = "",
    safety_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined = normalize_text(f"{chat_history}\n{user_message}\n{assistant_text}")
    output = normalize_text(assistant_text)
    safety_flags = safety_flags if isinstance(safety_flags, dict) else {}

    critics = [
        _crisis_critic(user_message, chat_history, safety_flags),
        _medical_boundary_critic(combined, output),
        _dependency_critic(combined, output),
        _manipulation_critic(combined, output),
        _privacy_bias_critic(combined, output),
    ]
    overall = max((critic.severity for critic in critics), key=lambda item: SEVERITY_RANK[item])
    report = PsychosocialSafetyReport(
        overall_severity=overall,
        critics=critics,
        high_risk=SEVERITY_RANK[overall] >= SEVERITY_RANK["high"],
        medium_risk=SEVERITY_RANK[overall] >= SEVERITY_RANK["medium"],
    )
    return report.model_dump()


def safety_fallback(report: dict[str, Any]) -> str:
    critics = report.get("critics") if isinstance(report, dict) else []
    names = {item.get("critic") for item in critics if isinstance(item, dict) and item.get("triggered")}
    if "crisis_critic" in names:
        return (
            "Tôi rất lo cho sự an toàn của bạn lúc này. Nếu nguy cơ làm hại bản thân hoặc người khác đang gần, "
            "hãy rời xa vật nguy hiểm và gọi 115 hoặc liên hệ ngay một người tin cậy ở gần bạn."
        )
    if "medical_boundary_critic" in names:
        return (
            "Tôi không thể đưa chẩn đoán, tên thuốc hay liều dùng. Điều an toàn hơn là bạn trao đổi với bác sĩ, "
            "dược sĩ, y tế trường hoặc một người lớn đáng tin để được hỗ trợ đúng chuyên môn."
        )
    if "dependency_critic" in names:
        return (
            "Tôi có thể đồng hành trong cuộc trò chuyện này, nhưng không nên là nguồn hỗ trợ duy nhất của bạn. "
            "Mình thử nghĩ xem một người thật ngoài đời mà bạn có thể nhắn một câu ngắn là ai?"
        )
    return (
        "Tôi muốn giữ cuộc trò chuyện này an toàn và có ích cho bạn. Mình sẽ đi chậm lại, không chẩn đoán hay ép bạn, "
        "và tập trung vào một bước nhỏ an toàn ngay lúc này."
    )


def _crisis_critic(user_message: str, chat_history: str, safety_flags: dict[str, Any]) -> SafetyCriticResult:
    if is_crisis_input(user_message, chat_history) or safety_flags.get("crisis") or safety_flags.get("self_harm"):
        return SafetyCriticResult(
            critic="crisis_critic",
            severity="high",
            triggered=True,
            reason="Self-harm, violence, or acute safety language detected.",
        )
    text = normalize_text(f"{chat_history}\n{user_message}")
    if any(token in text for token in ("không muốn tồn tại", "biến mất", "không còn lý do", "hết đường")):
        return SafetyCriticResult(
            critic="crisis_critic",
            severity="medium",
            triggered=True,
            reason="Subtle hopelessness signal detected; monitor and respond safely.",
        )
    return SafetyCriticResult(critic="crisis_critic")


def _medical_boundary_critic(combined: str, output: str) -> SafetyCriticResult:
    if is_unsafe_output(output):
        return SafetyCriticResult(
            critic="medical_boundary_critic",
            severity="high",
            triggered=True,
            reason="Assistant output may diagnose or provide medication/dosage advice.",
        )
    if any(token in combined for token in ("uống thuốc", "tăng liều", "giảm liều", "chẩn đoán", "bị bệnh gì")):
        return SafetyCriticResult(
            critic="medical_boundary_critic",
            severity="medium",
            triggered=True,
            reason="Medication or diagnosis boundary is present.",
        )
    return SafetyCriticResult(critic="medical_boundary_critic")


def _dependency_critic(combined: str, output: str) -> SafetyCriticResult:
    if any(token in combined for token in ("chỉ có bạn hiểu", "chỉ muốn nói với bạn", "không cần ai ngoài bạn")):
        return SafetyCriticResult(
            critic="dependency_critic",
            severity="medium",
            triggered=True,
            reason="Possible dependency or exclusive attachment to chatbot.",
        )
    if any(token in output for token in ("tôi sẽ luôn ở đây", "chỉ cần nói với tôi", "không cần ai khác")):
        return SafetyCriticResult(
            critic="dependency_critic",
            severity="medium",
            triggered=True,
            reason="Assistant output may reinforce dependency.",
        )
    return SafetyCriticResult(critic="dependency_critic")


def _manipulation_critic(combined: str, output: str) -> SafetyCriticResult:
    if any(token in output for token in ("chắc chắn sẽ ổn", "đừng nghĩ vậy nữa", "bạn phải", "em phải", "cứ nghe tôi")):
        return SafetyCriticResult(
            critic="manipulation_critic",
            severity="medium",
            triggered=True,
            reason="Output contains over-directive or over-reassuring language.",
        )
    if any(token in combined for token in ("làm theo bạn nói", "bạn quyết định giúp mình", "bạn bảo gì mình làm nấy")):
        return SafetyCriticResult(
            critic="manipulation_critic",
            severity="medium",
            triggered=True,
            reason="User may be yielding agency to the system.",
        )
    return SafetyCriticResult(critic="manipulation_critic")


def _privacy_bias_critic(combined: str, output: str) -> SafetyCriticResult:
    if any(token in combined for token in ("mật khẩu", "số căn cước", "địa chỉ nhà", "số tài khoản")):
        return SafetyCriticResult(
            critic="privacy_bias_critic",
            severity="medium",
            triggered=True,
            reason="Sensitive personal data appears in conversation.",
        )
    if any(token in output for token in ("do giới tính", "do dân tộc", "người như bạn thì")):
        return SafetyCriticResult(
            critic="privacy_bias_critic",
            severity="high",
            triggered=True,
            reason="Output may contain discriminatory framing.",
        )
    return SafetyCriticResult(critic="privacy_bias_critic")
