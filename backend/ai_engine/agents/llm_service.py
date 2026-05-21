import os
import logging
import httpx
import requests
from typing import Any
import asyncio
import time
try:
    from google import genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None
from groq import AsyncGroq, Groq

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self._gemini_client = None
        self._groq_async_client = None
        self._groq_sync_client = None
        self._last_groq_call_time = 0.0
        self._slm_semaphore = asyncio.Semaphore(1)
        self.fast_model = os.getenv("FAST_MODEL", "gemini-2.5-flash")
        self.smart_model = os.getenv("SMART_MODEL", "gemini-2.5-flash")

    def _get_gemini_client(self) -> genai.Client:
        if self._gemini_client is None:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    def _new_gemini_client(self) -> genai.Client:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        return genai.Client(api_key=api_key)

    def _sanitize_gemini_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(kwargs)
        config = cleaned.get("config")
        if isinstance(config, dict):
            config = dict(config)
            config.pop("response_schema", None)
            cleaned["config"] = config
        return cleaned

    async def generate_text_async(self, model: str, contents: str, model_type: str = "gemini", **kwargs) -> str:
        if model_type == "groq":
            if not self._groq_async_client:
                self._groq_async_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))
            
            # Rate limiting 20 RPM = 3 seconds between requests
            now = time.time()
            elapsed = now - self._last_groq_call_time
            if elapsed < 3.0:
                await asyncio.sleep(3.0 - elapsed)
            self._last_groq_call_time = time.time()
            
            # Auto-inject JSON instruction if JSON mode is requested
            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."
                
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": contents}
            ]
            response_format = {"type": "json_object"} if is_json else {"type": "text"}
            
            try:
                res = await self._groq_async_client.chat.completions.create(
                    model="llama-3.3-70b-versatile" if model_type == "groq" and model in ["gemini-2.5-flash", ""] else model,
                    messages=messages,
                    response_format=response_format,
                    temperature=kwargs.get("config", {}).get("temperature", 0.7)
                )
                return res.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq async call failed: %s", e)
                return "{}" if is_json else f"LỖI GROQ: {e}"

        if model_type == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                return "System Error: DEEPSEEK_API_KEY not set."
            
            # Rate limiting / Sleep to avoid limit if necessary (Optional, deepseek is usually fast)
            now = time.time()
            elapsed = now - self._last_groq_call_time
            if elapsed < 2.0:
                await asyncio.sleep(2.0 - elapsed)
            self._last_groq_call_time = time.time()
            
            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."
                
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": contents}
            ]
            
            # DeepSeek uses 'response_format' in their API compatible with OpenAI
            payload = {
                "model": model if model not in ["gemini-2.5-flash", ""] else "deepseek-chat",
                "messages": messages,
                "temperature": kwargs.get("config", {}).get("temperature", 0.7)
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    res = await client.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers)
                    res.raise_for_status()
                    return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                logger.warning("DeepSeek async call failed: %s", e)
                return "{}" if is_json else f"LỖI DEEPSEEK: {e}"

        if model_type in {"openai", "gpt"}:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return "System Error: OPENAI_API_KEY not set."

            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."

            payload = {
                "model": model if model not in ["gemini-2.5-flash", ""] else os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": contents},
                ],
                "temperature": kwargs.get("config", {}).get("temperature", 0.7),
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    res = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                    res.raise_for_status()
                    return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                logger.warning("OpenAI async call failed: %s", e)
                return "{}" if is_json else f"LỖI OPENAI: {e}"

        if model_type == "slm":
            slm_url = os.getenv("SLM_NGROK_URL")
            if not slm_url:
                return "System Error: SLM_NGROK_URL not set."
            payload = {"prompt": contents}
            if kwargs.get("config", {}).get("response_mime_type") == "application/json":
                payload["format"] = "json"
            headers = {"ngrok-skip-browser-warning": "1"}
            async with self._slm_semaphore:
                for attempt in range(3):
                    try:
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            res = await client.post(f"{slm_url.rstrip('/')}/v1/generate", json=payload, headers=headers)
                            res.raise_for_status()
                            data = res.json()
                            return data.get("text", "") or data.get("response", "") or str(data)
                    except Exception as e:
                        logger.warning("SLM async call failed on attempt %s/3: %s", attempt + 1, e)
                        if attempt < 2:
                            await asyncio.sleep(5 * (attempt + 1))
            return "LỖI SLM: Hết lần thử lại."

        response = await self._new_gemini_client().aio.models.generate_content(
            model=model,
            contents=contents,
            **self._sanitize_gemini_kwargs(kwargs),
        )
        return self._extract_text(response)

    def generate_text(self, model: str, contents: str, model_type: str = "gemini", **kwargs) -> str:
        if model_type == "groq":
            if not self._groq_sync_client:
                self._groq_sync_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
                
            now = time.time()
            elapsed = now - self._last_groq_call_time
            if elapsed < 3.0:
                time.sleep(3.0 - elapsed)
            self._last_groq_call_time = time.time()
            
            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."
                
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": contents}
            ]
            response_format = {"type": "json_object"} if is_json else {"type": "text"}
            
            try:
                res = self._groq_sync_client.chat.completions.create(
                    model="llama-3.3-70b-versatile" if model_type == "groq" and model in ["gemini-2.5-flash", ""] else model,
                    messages=messages,
                    response_format=response_format,
                    temperature=kwargs.get("config", {}).get("temperature", 0.7)
                )
                return res.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq sync call failed: %s", e)
                return "{}" if is_json else f"LỖI GROQ: {e}"

        if model_type == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                return "System Error: DEEPSEEK_API_KEY not set."
                
            now = time.time()
            elapsed = now - self._last_groq_call_time
            if elapsed < 2.0:
                time.sleep(2.0 - elapsed)
            self._last_groq_call_time = time.time()
            
            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."
                
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": contents}
            ]
            
            payload = {
                "model": model if model not in ["gemini-2.5-flash", ""] else "deepseek-chat",
                "messages": messages,
                "temperature": kwargs.get("config", {}).get("temperature", 0.7)
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                res = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=120.0)
                res.raise_for_status()
                return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                logger.warning("DeepSeek sync call failed: %s", e)
                return "{}" if is_json else f"LỖI DEEPSEEK: {e}"

        if model_type in {"openai", "gpt"}:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return "System Error: OPENAI_API_KEY not set."

            system_msg = "You are a helpful assistant."
            is_json = kwargs.get("config", {}).get("response_mime_type") == "application/json"
            if is_json:
                system_msg = "You are a specialized JSON AI. You must ALWAYS reply with a valid JSON object. Do not output markdown code blocks, just raw JSON."

            payload = {
                "model": model if model not in ["gemini-2.5-flash", ""] else os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": contents},
                ],
                "temperature": kwargs.get("config", {}).get("temperature", 0.7),
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

            try:
                res = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120.0)
                res.raise_for_status()
                return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                logger.warning("OpenAI sync call failed: %s", e)
                return "{}" if is_json else f"LỖI OPENAI: {e}"

        if model_type == "slm":
            slm_url = os.getenv("SLM_NGROK_URL")
            if not slm_url:
                return "System Error: SLM_NGROK_URL not set."
            try:
                payload = {"prompt": contents}
                if kwargs.get("config", {}).get("response_mime_type") == "application/json":
                    payload["format"] = "json"
                headers = {"ngrok-skip-browser-warning": "1"}
                res = requests.post(f"{slm_url.rstrip('/')}/v1/generate", json=payload, headers=headers, timeout=120.0)
                res.raise_for_status()
                data = res.json()
                return data.get("text", "") or data.get("response", "") or str(data)
            except Exception as e:
                logger.warning("SLM sync call failed: %s", e)
                return f"LỖI SLM: {e}"

        response = self._get_gemini_client().models.generate_content(
            model=model,
            contents=contents,
            **self._sanitize_gemini_kwargs(kwargs),
        )
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
