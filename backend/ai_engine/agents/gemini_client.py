import os
from typing import Any

from google import genai

_CLIENT: genai.Client | None = None

# Cấu hình Model tập trung cho toàn bộ Agent
FAST_MODEL = "gemini-3.1-flash-lite-preview"  
SMART_MODEL = "gemini-3.1-flash-lite-preview"       

def _get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def generate_text(model: str, contents: str, **kwargs) -> str:
    response = _get_client().models.generate_content(model=model, contents=contents, **kwargs)
    text = getattr(response, "text", None)
    if text:
        return text

    parts: list[str] = []
    candidates: Any = getattr(response, "candidates", None) or []
    for c in candidates:
        content = getattr(c, "content", None)
        for p in getattr(content, "parts", None) or []:
            t = getattr(p, "text", None)
            if t:
                parts.append(t)
    return "".join(parts)

