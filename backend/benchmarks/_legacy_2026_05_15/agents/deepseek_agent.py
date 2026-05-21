import os
import requests
from benchmarks.core.agent import BaseTherapistAgent

class DeepSeekAgent(BaseTherapistAgent):
    """Agent that calls DeepSeek API directly."""
    
    def __init__(self, name: str = "DeepSeek"):
        super().__init__(name)
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")

    async def get_response(self, history: str, user_msg: str) -> str:
        if not self.api_key:
            return "DEEPSEEK_API_KEY is not set in .env"
            
        prompt = f"Lịch sử trò chuyện:\n{history}\nUser: {user_msg}\nBạn là chuyên gia tư vấn tâm lý {self.name}. Hãy trả lời:"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Bạn là chuyên gia tư vấn tâm lý. Hãy lắng nghe và chia sẻ với người dùng."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            response_data = response.json()
            return response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"Error connecting to DeepSeek: {e}"
