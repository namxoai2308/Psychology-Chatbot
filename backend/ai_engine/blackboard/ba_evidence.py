from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ai_engine.blackboard.cbt_contract import has_any, normalize_text


class BAEvidence(BaseModel):
    low_energy: bool = Field(default=False)
    avoidance_or_shutdown: bool = Field(default=False)
    self_blame: bool = Field(default=False)
    energy_rating: bool = Field(default=False)
    chosen_micro_action: bool = Field(default=False)
    barrier_named: bool = Field(default=False)
    schedule_named: bool = Field(default=False)
    action_completed: bool = Field(default=False)
    reward_or_mood_shift: bool = Field(default=False)
    confidence: float = Field(default=0.68)
    evidence_quotes: list[str] = Field(default_factory=list)
    source: str = Field(default="heuristic")


def extract_ba_evidence_heuristic(user_message: str, chat_history: str = "") -> BAEvidence:
    msg = normalize_text(user_message)
    quotes = [user_message] if user_message else []
    low_energy = has_any(msg, ("cạn", "kiệt sức", "hết pin", "đuối", "mệt", "không còn sức", "chẳng muốn"))
    avoidance = has_any(msg, ("nằm", "trì hoãn", "né", "không muốn làm", "chưa làm", "lướt điện thoại", "để đó"))
    self_blame = has_any(msg, ("lười", "vô dụng", "tệ", "vô kỷ luật", "chẳng ra gì"))
    energy = bool(re.search(r"\b([0-9]|10)\s*/\s*10\b", msg)) or has_any(msg, ("pin mình", "mức pin", "năng lượng khoảng", "còn khoảng"))
    action = has_any(msg, ("mình chọn", "tôi chọn", "em chọn", "sẽ uống", "sẽ mở", "thử mở", "rửa mặt", "uống nước", "vươn vai", "đứng dậy"))
    barrier = has_any(msg, ("rào cản", "khó nhất", "sợ", "ngại", "vướng", "không biết bắt đầu", "dễ quên", "trôi mất thời gian"))
    schedule = has_any(msg, ("mấy giờ", "ngay sau", "sau khi", "lúc", "bây giờ", "5 phút nữa", "tối nay", "sáng mai"))
    completed = msg in {".", "xong", "xong rồi"} or has_any(msg, ("mình làm rồi", "tôi làm rồi", "em làm rồi", "vừa uống", "làm xong", "đã làm", "mở rồi"))
    reward = has_any(msg, ("đỡ hơn", "nhẹ hơn", "tự hào", "vui hơn", "mood", "tâm trạng", "có chút động lực"))
    return BAEvidence(
        low_energy=low_energy,
        avoidance_or_shutdown=avoidance,
        self_blame=self_blame,
        energy_rating=energy,
        chosen_micro_action=action,
        barrier_named=barrier,
        schedule_named=schedule,
        action_completed=completed,
        reward_or_mood_shift=reward,
        confidence=_confidence(low_energy, avoidance, self_blame, energy, action, barrier, schedule, completed, reward),
        evidence_quotes=quotes,
    )


def _confidence(*signals: bool) -> float:
    count = sum(1 for signal in signals if signal)
    if count >= 2:
        return 0.84
    if count == 1:
        return 0.76
    return 0.68
