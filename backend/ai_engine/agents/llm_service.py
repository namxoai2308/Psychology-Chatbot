import os
import httpx
import requests
from typing import Any
from google import genai

class LLMService:
    def __init__(self):
        self._gemini_client = None
        self.fast_model = os.getenv("FAST_MODEL", "gemini-3.1-flash-lite-preview")
        self.smart_model = os.getenv("SMART_MODEL", "gemini-3.1-flash-lite-preview")

    def _get_gemini_client(self) -> genai.Client:
        if self._gemini_client is None:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    async def generate_text_async(self, model: str, contents: str, model_type: str = "gemini", **kwargs) -> str:
        if model_type == "slm":
            slm_url = os.getenv("SLM_NGROK_URL")
            if not slm_url:
                return "System Error: SLM_NGROK_URL not set."
            
            try:
                payload = {"prompt": contents}
                if kwargs.get("config", {}).get("response_mime_type") == "application/json":
                    payload["format"] = "json"
                async with httpx.AsyncClient(timeout=45.0) as client:
                    res = await client.post(f"{slm_url.rstrip('/')}/v1/generate", json=payload)
                    res.raise_for_status()
                    data = res.json()
                    return data.get("text", "") or data.get("response", "") or str(data)
            except Exception as e:
                print(f"Lỗi khi gọi SLM qua Ngrok (Async): {e}")
                return f"LỖI SLM: {e}"

        response = await self._get_gemini_client().aio.models.generate_content(model=model, contents=contents, **kwargs)
        return self._extract_text(response)

    def generate_text(self, model: str, contents: str, model_type: str = "gemini", **kwargs) -> str:
        if model_type == "slm":
            slm_url = os.getenv("SLM_NGROK_URL")
            if not slm_url:
                return "System Error: SLM_NGROK_URL not set."
            try:
                payload = {"prompt": contents}
                if kwargs.get("config", {}).get("response_mime_type") == "application/json":
                    payload["format"] = "json"
                res = requests.post(f"{slm_url.rstrip('/')}/v1/generate", json=payload, timeout=45.0)
                res.raise_for_status()
                data = res.json()
                return data.get("text", "") or data.get("response", "") or str(data)
            except Exception as e:
                print(f"Lỗi khi gọi SLM qua Ngrok (Sync): {e}")
                return f"LỖI SLM: {e}"

        response = self._get_gemini_client().models.generate_content(model=model, contents=contents, **kwargs)
        return self._extract_text(response)

    def _extract_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if text: return text
        parts = []
        for c in getattr(response, "candidates", None) or []:
            for p in getattr(getattr(c, "content", None), "parts", None) or []:
                if getattr(p, "text", None):
                    parts.append(p.text)
        return "".join(parts)

llm_service = LLMService()

# Backward compatibility aliases
generate_text_async = llm_service.generate_text_async
generate_text = llm_service.generate_text
FAST_MODEL = llm_service.fast_model
SMART_MODEL = llm_service.smart_model
