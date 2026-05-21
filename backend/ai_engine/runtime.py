from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from ai_engine.services.prompt_renderer import render_template
from ai_engine.services.prompts import PromptBundleProxy, load_prompts
from ai_engine.services.safety import is_crisis_input

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT_DIR / ".env")


_PROMPTS = PromptBundleProxy()


def _safety_guard(user_message: str, chat_history: str) -> str:
    if is_crisis_input(user_message, chat_history):
        return "CRITICAL"
    return "SAFE"


def _guess_stage(user_message: str) -> str:
    t = user_message.lower()
    if any(x in t for x in ("tôi nghĩ", "mình nghĩ", "trong đầu", "ý nghĩ", "suy nghĩ")):
        return "stage_3_distortions"
    if any(x in t for x in ("bằng chứng", "chắc chắn", "100%", "có thể nào khác")):
        return "stage_4_socratic"
    if any(x in t for x in ("kế hoạch", "thử", "hành động", "bước nhỏ", "làm gì tiếp")):
        return "stage_5_action"
    if any(x in t for x in ("khi", "lúc", "xảy ra", "chuyện", "sự việc")):
        return "stage_2_abc_model"
    return "stage_1_venting"


def _render(template: str, **variables: str) -> str:
    return render_template(template, **variables)


def _fallback_reply(user_message: str, chat_history: str, user_name: str, stage: str) -> str:
    name = (user_name or "").strip()
    prefix = f"{name}, " if name else ""
    if stage == "stage_2_abc_model":
        q = "Lúc chuyện đó xảy ra, trong đầu bạn đã lóe lên suy nghĩ gì khiến bạn thấy như vậy?"
    elif stage == "stage_3_distortions":
        q = "Khi bạn tin suy nghĩ đó, cảm xúc của bạn tăng lên như thế nào? Có khả năng nào khác cho tình huống này không?"
    elif stage == "stage_4_socratic":
        q = "Bạn có bằng chứng cụ thể nào cho thấy suy nghĩ đó đúng 100% không? Có bằng chứng nào ngược lại không?"
    elif stage == "stage_5_action":
        q = "Nếu viết lại suy nghĩ đó theo hướng cân bằng hơn, bạn muốn câu mới như thế nào? Bạn sẵn sàng thử một bước nhỏ nào trong 1–2 ngày tới không?"
    else:
        q = "Điều gì làm bạn thấy nặng nhất trong chuyện này?"

    return (
        f"{prefix}mình nghe bạn đang trải qua một điều khá nặng nề.\n"
        f"Nghe vậy thì việc bạn thấy căng thẳng/đau lòng là rất dễ hiểu.\n"
        f"{q}"
    )


def generate_reply(*, user_message: str, chat_history: str = "", user_name: str = "") -> dict:
    # Sửa lỗi Import bị sai để không import file cbt_graph không tồn tại
    from .hospital_graph import hospital_app

    initial_state = {
        "chat_history": chat_history,
        "user_message": user_message,
        "user_name": user_name,
        "risk_level": "SAFE",
        "intent": "",
        "current_phase": "stage_1_venting",
        "analyzer_data": "",
        "draft_reply": "",
        "final_reply": "",
    }

    final_state = hospital_app.invoke(initial_state)
    return {
        "reply": final_state.get("final_reply") or final_state.get("draft_reply") or "",
        "safety": final_state.get("risk_level") or "SAFE",
        "stage": final_state.get("current_phase") or "stage_1_venting",
    }
