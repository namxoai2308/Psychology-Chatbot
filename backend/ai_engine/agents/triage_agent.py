import json
from ai_engine.state import HospitalState
from ai_engine.agents.gemini_client import generate_text, FAST_MODEL
from ai_engine.runtime import _PROMPTS, _render

def triage_node(state: HospitalState) -> HospitalState:
    """Bác sĩ phân luồng: Đọc triệu chứng và xếp khoa"""
    print("\n" + "="*60)
    print("🏥 TRIAGE DISPATCHER: Đang khám phân luồng ban đầu...")
    
    prompt = f"{_PROMPTS.triage_dispatcher}\n\nLịch sử chat:\n{state.get('chat_history', '')}\nTin nhắn mới nhất của Patient: {state['user_message']}"
    
    response = generate_text(
        model=FAST_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    
    try:
        data = json.loads(response)
        risk = data.get("risk_level", "SAFE")
        intent = data.get("intent", "GREETING")
        dept = data.get("therapy_route", "CBT")
        reasoning = data.get("reasoning", "")
    except Exception as e:
        print(f"⚠️ Triage Lỗi Parse JSON: {e}")
        risk, intent, dept, reasoning = "SAFE", "GREETING", "CBT", "Error parsing"
        
    print(f"  -> 🚨 Mức độ rủi ro: {risk} | 🩺 Chuyển Khoa: {dept} | 💡 Lý do: {reasoning}")
    return {"risk_level": risk, "intent": intent, "therapy_route": dept}
