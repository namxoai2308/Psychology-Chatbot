import json
from ai_engine.state import HospitalState
from ai_engine.agents.gemini_client import generate_text, FAST_MODEL, SMART_MODEL
from ai_engine.runtime import _PROMPTS, _render

def cbt_phase_node(state: HospitalState) -> HospitalState:
    print("📋 KHOA CBT: Đang theo dõi tiến trình (Phase Detector)...")
    
    prompt = f"""Bạn là máy dò Giai đoạn Trị liệu Nhận thức (CBT).
Danh sách các giai đoạn:
1. stage_1_venting
2. stage_2_abc_model
3. stage_3_distortions
4. stage_4_socratic
5. stage_5_action

Lịch sử: {state.get('chat_history', '')}
Tin nhắn hiện tại: {state['user_message']}

Phân tích lịch sử và tin nhắn này. Đưa ra Giai đoạn tiếp theo nên áp dụng.
Và nếu thấy LỖI TƯ DUY (Cognitive Distortion), hãy ghi chú lại ngắn gọn.

Trích xuất JSON y hệt mẫu sau:
{{
    "current_phase": "stage_1_venting",
    "analyzer_data": "Ghi chú lỗi tư duy nếu có, hoặc để trống."
}}"""
    
    res = generate_text(model=FAST_MODEL, contents=prompt, config={"response_mime_type": "application/json"})
    try:
        data = json.loads(res)
        phase = data.get("current_phase", "stage_1_venting")
        analyzer = data.get("analyzer_data", "")
    except Exception:
        phase = "stage_1_venting"
        analyzer = ""
        
    return {"current_phase": phase, "analyzer_data": analyzer}

def cbt_therapist_node(state: HospitalState) -> HospitalState:
    phase = state.get("current_phase", "stage_1_venting")
    print(f"🧠 BÁC SĨ CBT: Đang áp dụng phác đồ -> {phase}")
    
    core_prompt = _render(
        _PROMPTS.therapist_cbt,
        user_name=state.get("user_name", ""),
        chat_history=state.get("chat_history", ""),
        user_message=state["user_message"],
    )
    
    stage_prompt = _render(
        _PROMPTS.cbt_stages.get(phase, _PROMPTS.cbt_stages["stage_1_venting"]),
        user_name=state.get("user_name", ""),
        chat_history=state.get("chat_history", ""),
        user_message=state["user_message"],
        cognitive_distortion=state.get("analyzer_data", ""),
    )
    
    full_prompt = f"{core_prompt}\n\n[NHIỆM VỤ GIAI ĐOẠN HIỆN TẠI]\n{stage_prompt}"
    
    txt = generate_text(model=SMART_MODEL, contents=full_prompt)
    return {"final_reply": txt.strip()}
