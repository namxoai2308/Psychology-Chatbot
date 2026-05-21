from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_contract import has_any, normalize_text


class MBIEvidence(BaseModel):
    panic_or_overload: bool = Field(default=False)
    breathing_settled: bool = Field(default=False)
    thought_observed: bool = Field(default=False)
    body_sensation: bool = Field(default=False)
    present_moment_contact: bool = Field(default=False)
    mindful_action_ready: bool = Field(default=False)
    confidence: float = Field(default=0.68)
    evidence_quotes: list[str] = Field(default_factory=list)
    source: str = Field(default="heuristic")


def extract_mbi_evidence_heuristic(user_message: str, chat_history: str = "") -> MBIEvidence:
    msg = normalize_text(user_message)
    quotes = [user_message] if user_message else []
    settled = has_any(msg, ("đỡ", "dịu", "bình tĩnh", "thở chậm", "nhẹ hơn", "ổn hơn", "bớt hoảng"))
    panic = has_any(msg, ("không thở", "khó thở", "tim đập", "hoảng", "run", "quay cuồng", "ngộp", "choáng")) and not settled
    thought = has_any(msg, ("suy nghĩ", "ý nghĩ", "cứ xuất hiện", "bị cuốn", "vòng lặp", "nghĩ nhiều", "mình đang có suy nghĩ"))
    body = has_any(msg, ("nặng ngực", "căng vai", "nghẹn", "đau bụng", "mỏi", "cổ họng", "vai gáy", "bụng", "ngực", "vai"))
    present = has_any(msg, ("nhìn thấy", "nghe thấy", "bàn chân", "chạm sàn", "hiện tại", "xung quanh"))
    action = has_any(msg, ("uống nước", "vươn vai", "đứng dậy", "nhìn ra", "đi chậm", "rửa mặt", "làm gì đó nhỏ", "kết thúc", "ghi nhớ", "dùng lại")) or bool(
        re.search(r"\b(30|60)\s*giây\b", msg)
    )
    return MBIEvidence(
        panic_or_overload=panic,
        breathing_settled=settled,
        thought_observed=thought,
        body_sensation=body,
        present_moment_contact=present,
        mindful_action_ready=action or (settled and present),
        confidence=_confidence(panic, settled, thought, body, present, action),
        evidence_quotes=quotes,
    )


def _confidence(*signals: bool) -> float:
    count = sum(1 for signal in signals if signal)
    if count >= 2:
        return 0.84
    if count == 1:
        return 0.76
    return 0.68
