import asyncio
from typing import Dict, Any, List, Optional
from ai_engine.agents.llm_service import generate_text_async

class PatientSimulator:
    """Simulates a patient's responses based on a persona and initial context."""
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model

    async def get_response(self, persona: str, initial_msg: str, history: str, bot_msg: str) -> str:
        prompt = f"""Bạn là một người dùng đang sử dụng Chatbot Tâm lý.
Tính cách: {persona}
Hoàn cảnh ban đầu: {initial_msg}

Nhiệm vụ: Trả lời lại bot trong 1-2 câu ngắn gọn, tự nhiên, chân thật theo hoàn cảnh.
Lịch sử hiện tại: {history}
Nút thắt/Tin nhắn từ Bot: "{bot_msg}"
Bạn:"""
        response = await generate_text_async(
            model=self.model, 
            contents=prompt, 
            model_type="gemini"
        )
        return response.strip()

class SimulationEngine:
    """Handles the interaction between a PatientSimulator and a TherapistAgent."""
    
    def __init__(self, patient_sim: PatientSimulator):
        self.patient_sim = patient_sim

    async def run_session(
        self, 
        agent: Any, 
        test_case: Dict[str, Any], 
        num_turns: int = 3
    ) -> Dict[str, Any]:
        """Runs a conversation session for a single agent and test case."""
        
        uid = test_case["id"]
        persona = test_case.get("persona_prompt") or test_case.get("persona", "")
        initial_msg = test_case.get("initial_message") or test_case.get("core_issue", "Tôi cảm thấy mệt mỏi.")
        
        transcript = f"USER: {initial_msg}\n"
        history = ""
        user_msg = initial_msg
        
        # Some agents might need specialized state (like FSM)
        # We handle that inside the agent's get_response or via reset if needed
        
        for turn in range(num_turns):
            # 1. Get Therapist Response
            bot_reply = await agent.get_response(history, user_msg)
            bot_reply = bot_reply.strip()
            transcript += f"{agent.name}: {bot_reply}\n"
            
            # Update history for the therapist (simple text history)
            history += f"User: {user_msg}\nAssistant: {bot_reply}\n"
            
            # 2. Get Patient Response (unless it's the last turn)
            if turn < num_turns - 1:
                # Handle specialized patient inputs (like DASS21) if the agent requests it
                # For now, we'll check if the bot_reply contains a request for DASS21
                # or if the agent class has a way to signal UI actions.
                # To keep it simple, we check if the agent is FSMAgent and has ui_action
                
                ui_action = getattr(agent, "last_ui_action", "NONE")
                if ui_action == "SHOW_DASS21":
                    user_msg = self._generate_dass21_array(test_case.get("dass21", {}))
                else:
                    user_msg = await self.patient_sim.get_response(persona, initial_msg, history, bot_reply)
                
                transcript += f"USER: {user_msg}\n"
        
        return {
            "agent_name": agent.name,
            "transcript": transcript,
            "final_state": getattr(agent, "last_state", {})
        }

    def _generate_dass21_array(self, dass21_scores: Dict[str, int]) -> str:
        ans = [0]*21
        def spread(total, count):
            res = [0]*count
            for i in range(total):
                res[i%count] += 1
                if res[i%count] > 3: res[i%count] = 3
            return res
            
        s_sum = max(0, dass21_scores.get("stress", 0) // 2)
        a_sum = max(0, dass21_scores.get("anxiety", 0) // 2)
        d_sum = max(0, dass21_scores.get("depression", 0) // 2)
        
        s_vals = spread(s_sum, 7)
        a_vals = spread(a_sum, 7)
        d_vals = spread(d_sum, 7)
        
        for i, idx in enumerate([0, 5, 7, 10, 11, 13, 17]): ans[idx] = s_vals[i]
        for i, idx in enumerate([1, 3, 6, 8, 14, 18, 19]): ans[idx] = a_vals[i]
        for i, idx in enumerate([2, 4, 9, 12, 15, 16, 20]): ans[idx] = d_vals[i]
            
        return "[DASS21_SUBMIT]: " + ",".join(map(str, ans))
