import json
from pydantic import BaseModel, ValidationError
from ai_engine.state import HospitalState
from ai_engine.agents.llm_service import generate_text_async, FAST_MODEL, SMART_MODEL
from ai_engine.runtime import _render, _PROMPTS

class PhaseOutput(BaseModel):
    current_phase: str
    analyzer_data: str = ""

class BaseTherapyDepartment:
    def __init__(self, name: str, emoji: str, detector_prompt: str, therapist_system_prompt: str, stages_dict: dict, default_phase: str):
        self.name = name
        self.emoji = emoji
        self.detector_prompt = detector_prompt
        self.therapist_system_prompt = therapist_system_prompt
        self.stages_dict = stages_dict
        self.default_phase = default_phase

    async def phase_node(self, state: HospitalState) -> HospitalState:
        print(f"📋 KHOA {self.name}: Đang kiểm tra giai đoạn (Phase Detector)...")
        prompt = _render(
            self.detector_prompt,
            chat_history=state.get('chat_history', ''),
            user_message=state['user_message']
        )
        
        # Dùng Pydantic bảo vệ dữ liệu JSON
        res = await generate_text_async(
            model=FAST_MODEL, 
            contents=prompt, 
            model_type=state.get("selected_model", "gemini"), 
            config={
                "response_mime_type": "application/json",
                "response_schema": PhaseOutput
            }
        )
        
        try:
            data = PhaseOutput.model_validate_json(res)
            phase = data.current_phase
            analyzer = data.analyzer_data
        except ValidationError as e:
            print(f"{self.name} Lỗi Parse JSON Pydantic: {e} -> Raw text: {res}")
            phase = self.default_phase
            analyzer = ""
            
        return {"current_phase": phase, "analyzer_data": analyzer}

    async def therapist_node(self, state: HospitalState) -> HospitalState:
        phase = state.get("current_phase", self.default_phase)
        print(f"{self.emoji} BÁC SĨ {self.name}: Đang áp dụng phác đồ -> {phase}")
        
        core_prompt = _render(
            self.therapist_system_prompt,
            user_name=state.get("user_name", ""),
            chat_history=state.get("chat_history", ""),
            user_message=state["user_message"],
        )
        
        stage_prompt = _render(
            self.stages_dict.get(phase, self.stages_dict[self.default_phase]),
            user_name=state.get("user_name", ""),
            chat_history=state.get("chat_history", ""),
            user_message=state["user_message"],
            cognitive_distortion=state.get("analyzer_data", ""),
        )
        
        # Kết hợp system prompt và stage context
        full_prompt = f"{core_prompt}\n\n[NHIỆM VỤ GIAI ĐOẠN HIỆN TẠI]\n{stage_prompt}"
        
        txt = await generate_text_async(model=SMART_MODEL, contents=full_prompt, model_type=state.get("selected_model", "gemini"))
        return {"final_reply": txt.strip()}

# =====================================================================
# KHỞI TẠO CÁC KHOA (DEPARTMENTS)
# =====================================================================

cbt_dept = BaseTherapyDepartment(
    name="CBT",
    emoji="🧠",
    detector_prompt=_PROMPTS.phase_cbt,
    therapist_system_prompt=_PROMPTS.therapist_cbt,
    stages_dict=_PROMPTS.cbt_stages,
    default_phase="stage_1_venting"
)
cbt_phase_node = cbt_dept.phase_node
cbt_therapist_node = cbt_dept.therapist_node

mbi_dept = BaseTherapyDepartment(
    name="MBI",
    emoji="🧘",
    detector_prompt=_PROMPTS.phase_mbi,
    therapist_system_prompt=_PROMPTS.therapist_mbi,
    stages_dict=_PROMPTS.mbi_stages,
    default_phase="stage_1_grounding"
)
mbi_phase_node = mbi_dept.phase_node
mbi_therapist_node = mbi_dept.therapist_node

ba_dept = BaseTherapyDepartment(
    name="BA",
    emoji="🏃",
    detector_prompt=_PROMPTS.phase_ba,
    therapist_system_prompt=_PROMPTS.therapist_ba,
    stages_dict=_PROMPTS.ba_stages,
    default_phase="stage_1_energy_check"
)
ba_phase_node = ba_dept.phase_node
ba_therapist_node = ba_dept.therapist_node
