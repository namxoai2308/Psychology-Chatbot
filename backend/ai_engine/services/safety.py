from __future__ import annotations

import re


CRISIS_PATTERN = re.compile(
    r"\b(tự tử|muốn chết|không muốn sống|tự hại|cắt tay|nhảy lầu|uống thuốc|giết|đâm|bắn)\b",
    re.IGNORECASE,
)

UNSAFE_OUTPUT_PATTERNS = [
    r"\b(tự tử đi|chết đi|tự hại|cắt tay|uống thuốc quá liều)\b",
    r"\b(chẩn đoán|kết luận bạn bị|bạn mắc bệnh)\b",
    r"\b(kê đơn|uống thuốc|tăng liều|giảm liều)\b",
    r"\b(prompt|system|AI model|mô hình ngôn ngữ)\b",
]


def is_crisis_input(user_message: str, chat_history: str = "") -> bool:
    return bool(CRISIS_PATTERN.search(f"{chat_history}\n{user_message}"))


def is_unsafe_output(text: str) -> bool:
    lower_text = text.lower()
    return any(re.search(pattern, lower_text, re.IGNORECASE) for pattern in UNSAFE_OUTPUT_PATTERNS)


def clean_toxic_advice(text: str) -> str:
    replacements = {
        "bạn nên": "bạn nghĩ sao nếu",
        "Bạn nên": "Bạn nghĩ sao nếu",
        "em nên": "em nghĩ sao nếu",
        "cậu nên": "cậu nghĩ sao nếu",
        "hãy làm": "thử cân nhắc",
        "Hãy làm": "Thử cân nhắc",
        "cần phải": "có thể cân nhắc",
        "Tôi khuyên": "Mình tự nhủ rằng",
        "tôi khuyên": "mình tự nhủ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
