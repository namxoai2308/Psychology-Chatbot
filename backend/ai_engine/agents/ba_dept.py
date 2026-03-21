import json
from ai_engine.state import HospitalState
from ai_engine.agents.gemini_client import generate_text, FAST_MODEL, SMART_MODEL
from ai_engine.runtime import _PROMPTS

def ba_phase_node(state: HospitalState) -> HospitalState:
    print("📋 KHOA BA: Đang đánh giá mức độ trì trệ (Phase Detector)...")
    
    prompt = f"""Bạn là máy dò Giai đoạn Kích hoạt Hành vi (BA).
Các giai đoạn:
1. stage_1_energy_check (Hỏi han thấu cảm, đo mức năng lượng và pin của người dùng)
2. stage_2_micro_action (Suggest hành động siêu bé 2 phút, xin phép họ làm)
3. stage_3_barrier_schedule (Phá tan rào cản từ chối phút chót, chốt thời gian bắt đầu)
4. stage_4_momentum_reward (Khen ngợi nức nở vì đã làm/đã đồng ý làm, kích hoạt phần thưởng và đà)

Lịch sử: {state.get('chat_history', '')}
Tin nhắn hiện tại: {state['user_message']}

Xác định xem tiến tới giai đoạn nào là phù hợp nhất.
Trả về định dạng JSON:
{{
    "current_phase": "stage_1_energy_check" 
}}"""
    
    res = generate_text(model=FAST_MODEL, contents=prompt, config={"response_mime_type": "application/json"})
    try:
        data = json.loads(res)
        phase = data.get("current_phase", "stage_1_energy_check")
    except Exception:
        phase = "stage_1_energy_check"
        
    return {"current_phase": phase}

def ba_therapist_node(state: HospitalState) -> HospitalState:
    phase = state.get("current_phase", "stage_1_energy_check")
    print(f"🏃 BÁC SĨ BA: Đang thúc đẩy hành động -> {phase}")
    
    sys_prompt = _PROMPTS.therapist_ba
    stage_prompt = _PROMPTS.ba_stages.get(phase, _PROMPTS.ba_stages["stage_1_energy_check"])
    
    full_prompt = f"{sys_prompt}\n\n[GIAI ĐOẠN HIỆN TẠI]\n{stage_prompt}\n\nLịch sử chat:\n{state.get('chat_history', '')}\n\nTin nhắn người dùng: {state['user_message']}\nBác sĩ BA trả lời (dứt khoát, hướng tới hành động):"
    
    txt = generate_text(model=SMART_MODEL, contents=full_prompt)
    return {"final_reply": txt.strip()}
