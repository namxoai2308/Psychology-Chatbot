from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class PromptPack:
    triage_dispatcher: str
    therapist_cbt: str
    therapist_mbi: str
    therapist_ba: str
    crisis: str
    analyzer_core: str
    cbt_stages: dict[str, str]
    mbi_stages: dict[str, str]
    ba_stages: dict[str, str]

def load_prompts() -> PromptPack:
    return PromptPack(
        triage_dispatcher=_read(PROMPTS_DIR / "routers" / "dispatcher.txt"),
        therapist_cbt=_read(PROMPTS_DIR / "system_personas" / "therapist_cbt.txt"),
        therapist_mbi=_read(PROMPTS_DIR / "system_personas" / "therapist_mbi.txt"),
        therapist_ba=_read(PROMPTS_DIR / "system_personas" / "therapist_ba.txt"),
        analyzer_core=_read(PROMPTS_DIR / "system_personas" / "analyzer_core.txt"),
        crisis=_read(PROMPTS_DIR / "safety_protocols" / "crisis_intervention.txt"),
        cbt_stages={
            "stage_1_venting": _read(PROMPTS_DIR / "cbt_stages" / "stage_1_venting.txt"),
            "stage_2_abc_model": _read(PROMPTS_DIR / "cbt_stages" / "stage_2_abc_model.txt"),
            "stage_3_distortions": _read(PROMPTS_DIR / "cbt_stages" / "stage_3_distortions.txt"),
            "stage_4_socratic": _read(PROMPTS_DIR / "cbt_stages" / "stage_4_socratic.txt"),
            "stage_5_action": _read(PROMPTS_DIR / "cbt_stages" / "stage_5_action.txt"),
        },
        mbi_stages={
            "stage_1_grounding": _read(PROMPTS_DIR / "mbi_stages" / "stage_1_grounding.txt"),
            "stage_2_decentering": _read(PROMPTS_DIR / "mbi_stages" / "stage_2_decentering.txt"),
            "stage_3_body_scan": _read(PROMPTS_DIR / "mbi_stages" / "stage_3_body_scan.txt"),
            "stage_4_mindful_action": _read(PROMPTS_DIR / "mbi_stages" / "stage_4_mindful_action.txt"),
        },
        ba_stages={
            "stage_1_energy_check": _read(PROMPTS_DIR / "ba_stages" / "stage_1_energy_check.txt"),
            "stage_2_micro_action": _read(PROMPTS_DIR / "ba_stages" / "stage_2_micro_action.txt"),
            "stage_3_barrier_schedule": _read(PROMPTS_DIR / "ba_stages" / "stage_3_barrier_schedule.txt"),
            "stage_4_momentum_reward": _read(PROMPTS_DIR / "ba_stages" / "stage_4_momentum_reward.txt"),
        }
    )



_PROMPTS = load_prompts()

_ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT_DIR / ".env")


_CRISIS_KEYWORDS = (
    "tự tử",
    "muốn chết",
    "không muốn sống",
    "tự hại",
    "cắt tay",
    "nhảy lầu",
    "uống thuốc",
    "giết",
    "đâm",
    "bắn",
)


def _safety_guard(user_message: str, chat_history: str) -> str:
    text = (chat_history + "\n" + user_message).lower()
    return "CRITICAL" if any(k in text for k in _CRISIS_KEYWORDS) else "SAFE"


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


def _render(template: str, **vars: str) -> str:
    out = template
    for k, v in vars.items():
        out = out.replace("{" + k + "}", v)
    return out


def _fallback_reply(user_message: str, chat_history: str, user_name: str, stage: str) -> str:
    # Minimal, effective: mirror + validate + open question (stage-driven).
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
    # Import inside the function to avoid circular import:
    # runtime -> cbt_graph -> runtime (for _PROMPTS/_render).
    from .cbt_graph import cbt_app

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

    final_state = cbt_app.invoke(initial_state)
    return {
        "reply": final_state.get("final_reply") or final_state.get("draft_reply") or "",
        "safety": final_state.get("risk_level") or "SAFE",
        "stage": final_state.get("current_phase") or "stage_1_venting",
    }

