import os
import requests
from benchmarks.core.agent import BaseTherapistAgent

class ExternalAPIAgent(BaseTherapistAgent):
    """Agent that calls external APIs (e.g., SoulChat, MindChat via Ngrok)."""
    
    def __init__(self, name: str, env_var_url: str):
        super().__init__(name)
        self.url = os.getenv(env_var_url, "").rstrip("/")

    async def get_response(self, history: str, user_msg: str) -> str:
        if not self.url:
            return f"Error: URL for {self.name} is not set in .env"
            
        prompt = f"Lịch sử:\n{history}\nUser: {user_msg}\n{self.name}:"
        
        try:
            # Using a synchronous post in an async method for simplicity, 
            # but ideally should use aiohttp
            response = requests.post(
                f"{self.url}/v1/generate", 
                json={"prompt": prompt}, 
                timeout=120
            )
            return response.json().get("text", "").strip()
        except Exception as e:
            return f"Error connecting to {self.name}: {e}"
