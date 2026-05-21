import os
import requests
import json
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from ai_engine.agents.llm_service import generate_text_async
from benchmarks.agents.fsm_agent import FSMAgent

# Nạp biến môi trường từ file .env
load_dotenv()

class EvaluationEngine:
    def __init__(self):
        self.mindchat_url = os.getenv("MINDCHAT_NGROK_URL", "").rstrip("/")
        self.soulchat_url = os.getenv("SOULCHAT_NGROK_URL", "").rstrip("/")
        # Cung cấp name và thread_id mặc định cho FSMAgent
        self.fsm_agent = FSMAgent(name="BenchmarkAgent", thread_id="test_thread")

    async def call_raw_slm(self, url: str, history: List[Dict[str, str]]) -> str:
        """Calls the raw model on Kaggle via Ngrok."""
        if not url:
            return "(Error: URL not set)"

        # Format the history into a single string for raw model inference
        formatted_prompt = ""
        for turn in history:
            role = "User" if turn["role"] == "user" else "Assistant"
            formatted_prompt += f"{role}: {turn['content']}\n"
        formatted_prompt += "Assistant:"

        try:
            # Adding ngrok-skip-browser-warning header to bypass ngrok's interstitial page
            headers = {"ngrok-skip-browser-warning": "true"}
            response = requests.post(
                f"{url}/v1/generate",
                json={"prompt": formatted_prompt},
                headers=headers,
                timeout=120
            )
            
            if response.status_code != 200:
                return f"(Error {response.status_code}: {response.text})"
                
            result = response.json()
            if "error" in result:
                return f"(Model Error: {result['error']})"
                
            return result.get("text", "").strip()
        except Exception as e:
            return f"(Connection Error: {e})"

    async def run_raw_session(self, url: str, case: Dict[str, Any]) -> List[str]:
        """Simulates a multi-turn session with a raw model."""
        history = []
        responses = []
        
        for user_msg in case["user_turns"]:
            history.append({"role": "user", "content": user_msg})
            response = await self.call_raw_slm(url, history)
            responses.append(response)
            history.append({"role": "assistant", "content": response})
            
        return responses

    async def run_fsm_session(self, case: Dict[str, Any]) -> List[str]:
        """Simulates a multi-turn session with our proposed FSM system."""
        # Reset agent state/session if necessary (FSMAgent manages its own blackboard)
        responses = []
        for user_msg in case["user_turns"]:
            response = await self.fsm_agent.get_response(user_msg)
            responses.append(response)
            
        return responses

    async def evaluate_transcript(self, transcript: List[Dict[str, Any]], case: Dict[str, Any]) -> Dict[str, Any]:
        """Uses Gemini to score the clinical quality of a transcript."""
        # This will be used in the next phase of benchmarking
        prompt = f"""
        Evaluate the following AI Therapy session based on clinical CBT principles.
        
        Patient Persona: {case['persona']}
        Clinical Context: {case['name']}
        DASS-21 Target: {case['dass21']}
        
        Transcript:
        {json.dumps(transcript, ensure_ascii=False, indent=2)}
        
        Score from 1-10 on:
        1. Empathy
        2. CBT Alignment
        3. Safety/Risk Assessment
        4. Logical Flow
        
        Return JSON only.
        """
        # score_raw = await generate_text_async(prompt)
        # return json.loads(score_raw)
        return {"scores": "To be implemented"}
