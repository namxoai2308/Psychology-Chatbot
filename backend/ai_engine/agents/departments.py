import json
from pydantic import BaseModel, ValidationError
from ai_engine.state import HospitalState
from ai_engine.agents.llm_service import generate_text_async, FAST_MODEL, SMART_MODEL
from ai_engine.runtime import _render, _PROMPTS
from ai_engine.rag_service import rag_service

class PhaseOutput(BaseModel):
    current_phase: str
    analyzer_data: str = ""

class CognitiveOutput(BaseModel):
    clinical_analysis: str
    reply_strategy: str

async def phase_node(state: HospitalState) -> HospitalState:
    dept = state.get("therapy_route", "CBT").lower()
    print(f"📋 KHOA {dept.upper()}: Đang kiểm tra giai đoạn (Phase Detector)...")
    
    prompt = _render(
        getattr(_PROMPTS, f"phase_{dept}"),
        chat_history=state.get('chat_history', ''),
        user_message=state['user_message']
    )
    
    res = await generate_text_async(
        model=FAST_MODEL, contents=prompt, model_type=state.get("selected_model", "gemini"), 
        config={"response_mime_type": "application/json", "response_schema": PhaseOutput}
    )
    
    try:
        data = PhaseOutput.model_validate_json(res)
        phase, analyzer = data.current_phase, data.analyzer_data
    except Exception as e:
        print(f"Lỗi Parse JSON Pydantic Phase: {e}")
        phase, analyzer = ("stage_1_venting" if dept == "cbt" else "stage_1_grounding" if dept == "mbi" else "stage_1_energy_check"), ""
        
    return {"current_phase": phase, "analyzer_data": analyzer}

async def cognitive_node(state: HospitalState) -> HospitalState:
    dept = state.get("therapy_route", "CBT").lower()
    phase = state.get("current_phase", "stage_1_venting")
    print(f"🕵️ BÁC SĨ {dept.upper()} (Cognitive): Phân tích chiến lược ({phase})...")
    
    prompt = f"Bạn là Bác sĩ phân tích lâm sàng (Clinical Formulator) của Khoa {dept.upper()}.\n[LỊCH SỬ]: {state.get('chat_history', '')}\n[NGƯỜI DÙNG HIỆN TẠI]: {state['user_message']}\n[DỮ LIỆU PHA TRƯỚC]: {state.get('analyzer_data', '')}\nNhiệm vụ: Đề ra chiến lược trả lời DƯỚI DẠNG JSON."
    
    res = await generate_text_async(
        model=FAST_MODEL, contents=prompt, model_type=state.get("selected_model", "gemini"),
        config={"response_mime_type": "application/json", "response_schema": CognitiveOutput}
    )
    
    try:
        data = CognitiveOutput.model_validate_json(res)
        strategy = f"Phân tích: {data.clinical_analysis}\nChiến lược trả lời: {data.reply_strategy}"
    except:
        strategy = "Tập trung lắng nghe tích cực và thấu cảm."
        
    return {"analyzer_data": state.get("analyzer_data", "") + f"\n[SOTA STRATEGY PLAN]: {strategy}"}

async def generator_node(state: HospitalState) -> HospitalState:
    dept = state.get("therapy_route", "CBT").lower()
    phase = state.get("current_phase", "stage_1_venting")
    print(f"BÁC SĨ {dept.upper()} (Generator): Đang sinh lời thấu cảm...")
    
    guideline = rag_service.retrieve_guideline(state['user_message'])
    
    core_prompt = _render(getattr(_PROMPTS, f"therapist_{dept}"), user_name=state.get("user_name", ""), chat_history=state.get("chat_history", ""), user_message=state["user_message"])
    stage_prompt = _render(getattr(_PROMPTS, phase), user_name=state.get("user_name", ""), chat_history=state.get("chat_history", ""), user_message=state["user_message"], cognitive_distortion=state.get("analyzer_data", ""))
    
    full_prompt = f"{core_prompt}\n\n[NHIỆM VỤ GIAI ĐOẠN HIỆN TẠI]\n{stage_prompt}\n\n[RAG CLINICAL GUIDELINE]: {guideline}\n\n[CHIẾN LƯỢC BẮT BUỘC TỪ KHOA PHÂN TÍCH]:\n{state.get('analyzer_data', '')}"
    
    txt = await generate_text_async(model=SMART_MODEL, contents=full_prompt, model_type=state.get("selected_model", "gemini"))
    return {"final_reply": txt.strip()}

async def safety_node(state: HospitalState) -> HospitalState:
    print("\n🛡️ SAFETY FILTER: Đang rà soát Output của AI...")
    prompt = f"Đánh giá Đạo đức & Y tế cho câu trả lời sau của Chatbot:\n[CÂU TRẢ LỜI]: {state.get('final_reply', '')}\nNếu câu trả lời xúi giục tự sát, gây hại, kê đơn thuốc sai thẩm quyền, hãy xuất 'UNSAFE'. Nếu an toàn, xuất 'SAFE'."
    res = await generate_text_async(model=FAST_MODEL, contents=prompt, model_type=state.get("selected_model", "gemini"))
    if "UNSAFE" in res.upper():
        print("  -> [CẢNH BÁO]: AI sinh nội dung độc hại/sai thẩm quyền. Đã chặn!")
        return {"final_reply": "Xin lỗi, hệ thống phát hiện cấu trúc nội dung vừa sinh vi phạm tiêu chuẩn an toàn y tế lâm sàng. Nếu bạn đang gặp tình trạng khẩn cấp, xin gọi ngay 111 hoặc 1900599930."}
    print("  -> ✅ Output Đạt chuẩn An Toàn (SAFE).")
    return {}
