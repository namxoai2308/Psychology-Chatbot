from benchmarks.core.agent import BaseTherapistAgent
from ai_engine.agents.llm_service import generate_text_async

class LLMTherapistAgent(BaseTherapistAgent):
    """Simple LLM-based therapist agent."""
    
    def __init__(self, name: str, system_prompt: str = "", model: str = "gemini-2.5-flash", model_type: str = "gemini"):
        super().__init__(name)
        self.system_prompt = system_prompt
        self.model = model
        self.model_type = model_type

    async def get_response(self, history: str, user_msg: str) -> str:
        if self.system_prompt:
            prompt = f"{self.system_prompt}\n\nLịch sử:\n{history}\nUser: {user_msg}\nBác sĩ:"
        else:
            prompt = f"Lịch sử:\n{history}\nUser: {user_msg}\nAssistant:"
            
        response = await generate_text_async(
            model=self.model, 
            contents=prompt, 
            model_type=self.model_type
        )
        return response.strip()
