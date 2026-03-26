from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

# Dùng env variable cho BASE_DIR, linh hoạt hơn, không hardcode parents[2]
BASE_DIR = Path(os.getenv("BASE_DIR", Path(__file__).resolve().parents[2]))
load_dotenv(BASE_DIR / ".env")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _read(path: Path) -> str:
    # Cấu trúc Fail-fast: ném exception ngay khi thiếu prompt
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}. Cannot start AI router.")
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class PromptPack:
    triage_dispatcher: str
    phase_cbt: str
    phase_mbi: str
    phase_ba: str
    therapist_cbt: str
    therapist_mbi: str
    therapist_ba: str
    crisis: str
    analyzer_core: str
    cbt_stages: dict[str, str]
    mbi_stages: dict[str, str]
    ba_stages: dict[str, str]


@lru_cache(maxsize=1)
def load_prompts() -> PromptPack:
    return PromptPack(
        triage_dispatcher=_read(PROMPTS_DIR / "routers" / "dispatcher.txt"),
        phase_cbt=_read(PROMPTS_DIR / "routers" / "phase_cbt.txt"),
        phase_mbi=_read(PROMPTS_DIR / "routers" / "phase_mbi.txt"),
        phase_ba=_read(PROMPTS_DIR / "routers" / "phase_ba.txt"),
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


# Rời bỏ proxy, load trực tiếp tại module level để fail-fast và có ide autocomplete hỗ trợ
_PROMPTS: PromptPack = load_prompts()


# Lọc thô bằng Regex
_CRISIS_PATTERN = re.compile(
    r'\b(tự tử|muốn chết|không muốn sống|tự hại|cắt tay|nhảy lầu|uống thuốc|giết|đâm|bắn|chết quách|kết liễu|quyên sinh)\b',
    re.IGNORECASE
)


def _safety_guard(user_message: str, chat_history: str, model_type: str = "gemini") -> str:
    text = f"{chat_history}\n{user_message}"
    if _CRISIS_PATTERN.search(text):
        # AI Logic Kép: Dùng LLM kiểm tra lại tránh dương tính giả (False Positives)
        try:
            from .agents.llm_service import generate_text, FAST_MODEL
            prompt = (
                "Là một AI bảo vệ an toàn, hãy phân tích tin nhắn sau xem có chứa ý định hoặc kịch bản tự tử/tự hại nghiêm trọng không.\n"
                "Trả lời duy nhất 'CRITICAL' nếu thực sự là rủi ro (đang có ý định, kế hoạch, đâm, chém, nhảy lầu).\n"
                "Trả lời duy nhất 'SAFE' nếu đó chỉ là diễn đạt phủ định (VD: tôi không bị điên mà đi chết), bóng gió, hình ảnh ẩn dụ (vui chết đi được) hoặc kể lại sự việc/tin tức (phim có ng nhảy lầu).\n\n"
                f"Tin nhắn phân tích: {user_message}"
            )
            res = generate_text(model=FAST_MODEL, contents=prompt, model_type=model_type).strip().upper()
            if "CRITICAL" in res:
                return "CRITICAL"
            return "SAFE"
        except ImportError:
            # Fallback nếu client chưa load kịp do import vòng
            return "CRITICAL"
        except Exception as e:
            # Bất kỳ lỗi mạng nào cũng nên fallback sang CRITICAL cho an toàn sinh mạng
            print(f"[SafetyGuard] LLM AI Check failed: {e}. Defaulting to CRITICAL.")
            return "CRITICAL"
    return "SAFE"


def _guess_stage(user_message: str, model_type: str = "gemini") -> str:
    # Nâng cấp lên dùng LLM để đoán chính xác ngữ cảnh giai đoạn
    try:
        from .agents.llm_service import generate_text, FAST_MODEL
        prompt = (
            "Bạn là trợ lý AI chuyên phân loại giai đoạn trị liệu Tâm lý học nhận thức hành vi (CBT).\n"
            "Hãy đọc tin nhắn thân chủ và quyết định nó thuộc 1 trong 5 giai đoạn:\n"
            "1. stage_1_venting: Giãi bày, trút giận, than phiền vô định, nói về cảm xúc tiêu cực đơn thuần.\n"
            "2. stage_2_abc_model: Nhắc đến câu chuyện, sự kiện kích hoạt, diễn biến xảy ra chuyện, nguyên nhân.\n"
            "3. stage_3_distortions: Bày tỏ suy nghĩ cực đoan, kết luận tiêu cực về bản thân/người khác, định kiến, méo mó nhận thức.\n"
            "4. stage_4_socratic: Đang tranh luận tìm bằng chứng, xem xét khía cạnh khác, lật lại vấn đề.\n"
            "5. stage_5_action: Chủ động đề xuất làm gì đó tiếp theo, sẵn sàng lên kế hoạch, chuẩn bị hành động phản hồi.\n\n"
            "CHỈ in ra đúng tên định danh, ví dụ: 'stage_1_venting'.\n"
            f"Tin nhắn: {user_message}"
        )
        res = generate_text(model=FAST_MODEL, contents=prompt, model_type=model_type).strip().lower()
        stages = [
            "stage_1_venting", "stage_2_abc_model", "stage_3_distortions", 
            "stage_4_socratic", "stage_5_action"
        ]
        for s in stages:
            if s in res:
                return s
    except Exception:
        pass
    
    # Fallback nhẹ nhàng
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
    # File prompt LLM chứa nhiều ngoặc nhọn `{` JSON, dùng `.format()` dễ lỗi KeyError.
    # Dùng `.replace` theo chuẩn cơ bản nhưng an toàn và không yêu cầu escape ngoặc template.
    out = template
    for k, v in variables.items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out


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


def generate_reply(
    *, 
    user_message: str, 
    thread_id: str,
    chat_history: str = "", 
    user_name: str = "",
    model_choice: str = "gemini"
) -> dict:
    from .hospital_graph import hospital_app

    initial_state = {
        "chat_history": chat_history,
        "user_message": user_message,
        "user_name": user_name,
        "selected_model": model_choice,
        "risk_level": "SAFE",
        "intent": "",
        "current_phase": "stage_1_venting",
        "analyzer_data": "",
        "final_reply": "",
    }

    # Giữ luồng hội thoại đồng nhất: LangGraph sẽ nạp lịch sử đúng phiên dựa trên thread_id truyền vào.
    config = {"configurable": {"thread_id": thread_id}}
    final_state = hospital_app.invoke(initial_state, config=config)
    return {
        "reply": final_state.get("final_reply") or "",
        "safety": final_state.get("risk_level") or "SAFE",
        "stage": final_state.get("current_phase") or "stage_1_venting",
    }
