import json
from ai_engine.state import HospitalState
from ai_engine.agents.llm_service import generate_text_async, FAST_MODEL
from ai_engine.runtime import _PROMPTS, _render, _safety_guard
from pydantic import BaseModel, ValidationError

class TriageOutput(BaseModel):
    risk_level: str
    intent: str
    therapy_route: str
    reasoning: str

async def triage_node(state: HospitalState) -> HospitalState:
    """Bác sĩ phân luồng: Đọc triệu chứng và xếp khoa"""
    print("\n" + "="*60)
    print("TRIAGE DISPATCHER: Đang khám phân luồng ban đầu...")

    # Regex pre-check: phát hiện khủng hoảng ngay, không cần gọi LLM
    if _safety_guard(state["user_message"], state.get("chat_history", ""), state.get("selected_model", "gemini")) == "CRITICAL":
        print("  -> [SAFETY GUARD] Phát hiện khủng hoảng qua regex. Chuyển Crisis ngay.")
        return {"risk_level": "CRITICAL", "intent": "CRISIS", "therapy_route": "NONE"}

    prompt = _render(
        _PROMPTS.triage_dispatcher,
        chat_history=state.get("chat_history", ""),
        user_message=state["user_message"],
    )

    # Sử dụng Pydantic Config schema cho Gemini
    response = await generate_text_async(
        model=FAST_MODEL,
        contents=prompt,
        model_type=state.get("selected_model", "gemini"),
        config={
            "response_mime_type": "application/json",
            "response_schema": TriageOutput
        }
    )

    try:
        data = TriageOutput.model_validate_json(response)
        risk = data.risk_level
        intent = data.intent
        dept = data.therapy_route
        reasoning = data.reasoning
    except ValidationError as e:
        print(f"Triage Lỗi Parse JSON: {e} -> Raw text: {response}")
        risk, intent, dept, reasoning = "SAFE", "GREETING", "CBT", "Error parsing"

    print(f"  -> Mức độ rủi ro: {risk} | Chuyển Khoa: {dept} | Lý do: {reasoning}")
    return {"risk_level": risk, "intent": intent, "therapy_route": dept}
