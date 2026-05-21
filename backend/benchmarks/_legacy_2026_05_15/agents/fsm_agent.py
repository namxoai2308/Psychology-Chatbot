from benchmarks.core.agent import BaseTherapistAgent
from ai_engine.hospital_graph import hospital_app
from typing import Dict, Any

class FSMAgent(BaseTherapistAgent):
    """Agent that wraps the Hospital FSM Graph system."""
    
    def __init__(self, name: str, thread_id: str, model_provider: str = "groq"):
        super().__init__(name)
        self.thread_id = thread_id
        self.model_provider = model_provider
        self.config = {"configurable": {"thread_id": f"benchmark_{thread_id}"}}
        self.last_state = {}
        self.last_ui_action = "NONE"
        self.turn_count = 0

    async def get_response(self, history: str, user_msg: str) -> str:
        state_update = {
            "user_message": user_msg,
            "selected_model": self.model_provider
        }
        
        # For the first turn, we might need to initialize more state if required
        if self.turn_count == 0:
            state_update["user_name"] = "TestUser"
            
        try:
            res = await hospital_app.ainvoke(state_update, config=self.config)
            self.last_state = res
            self.last_ui_action = res.get("ui_action", "NONE")
            self.turn_count += 1
            return res.get("final_reply", "(No reply)")
        except Exception as e:
            self.last_ui_action = "NONE"
            return f"(SYSTEM ERROR: {e})"
