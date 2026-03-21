import json
from ai_engine.state import HospitalState
from ai_engine.agents.gemini_client import generate_text, FAST_MODEL, SMART_MODEL
from ai_engine.runtime import _PROMPTS

def mbi_phase_node(state: HospitalState) -> HospitalState:
    print("📋 KHOA MBI: Đang kiểm tra mức độ căng cơ/căng thẳng (Phase Detector)...")
    
    prompt = f"""Bạn là máy chuyển Giai đoạn của khoa Chánh niệm (MBI).
Các giai đoạn:
1. stage_1_grounding (Bệnh nhân đang hoảng loạn, overthinking, cần kéo về thực tại 5 giác quan)
2. stage_2_decentering (Bệnh nhân bị cuốn theo suy nghĩ, cần tách bóc khỏi dòng suy nghĩ)
3. stage_3_body_scan (Bệnh nhân căng cứng cơ bắp, cần buông xả căng thẳng vật lý)
4. stage_4_mindful_action (Bệnh nhân đã ổn, cần hướng dẫn 1 hành động có ý thức)

Lịch sử: {state.get('chat_history', '')}
Tin nhắn hiện tại: {state['user_message']}

Xác định xem bệnh nhân cần làm gì tiếp theo.
Trả về định dạng JSON:
{{
    "current_phase": "stage_1_grounding" 
}}"""
    
    res = generate_text(model=FAST_MODEL, contents=prompt, config={"response_mime_type": "application/json"})
    try:
        data = json.loads(res)
        phase = data.get("current_phase", "stage_1_grounding")
    except Exception:
        phase = "stage_1_grounding"
        
    return {"current_phase": phase}

def mbi_therapist_node(state: HospitalState) -> HospitalState:
    phase = state.get("current_phase", "stage_1_grounding")
    print(f"🧘 BÁC SĨ MBI: Đang xoa dịu bằng -> {phase}")
    
    sys_prompt = _PROMPTS.therapist_mbi
    stage_prompt = _PROMPTS.mbi_stages.get(phase, _PROMPTS.mbi_stages["stage_1_grounding"])
    
    full_prompt = f"{sys_prompt}\n\n[GIAI ĐOẠN HIỆN TẠI]\n{stage_prompt}\n\nLịch sử chat:\n{state.get('chat_history', '')}\n\nTin nhắn người dùng: {state['user_message']}\nBác sĩ MBI trả lời:"
    
    txt = generate_text(model=SMART_MODEL, contents=full_prompt)
    return {"final_reply": txt.strip()}
