from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


class RemoteChatbotUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RemoteChatbotConfig:
    system_name: str
    env_var: str
    prompt_label: str
    timeout_seconds: int = 120


REMOTE_CHATBOTS = {
    "mindchat": RemoteChatbotConfig(
        system_name="mindchat",
        env_var="MINDCHAT_NGROK_URL",
        prompt_label="MindChat",
    ),
    "soulchat": RemoteChatbotConfig(
        system_name="soulchat",
        env_var="SOULCHAT_NGROK_URL",
        prompt_label="SoulChat",
    ),
    "seallm": RemoteChatbotConfig(
        system_name="seallm",
        env_var="SEALLM_NGROK_URL",
        prompt_label="SeaLLM",
        timeout_seconds=180,
    ),
    "camel_cbt": RemoteChatbotConfig(
        system_name="camel_cbt",
        env_var="CAMEL_NGROK_URL",
        prompt_label="CAMEL",
        timeout_seconds=180,
    ),
    "camel": RemoteChatbotConfig(
        system_name="camel",
        env_var="CAMEL_NGROK_URL",
        prompt_label="CAMEL",
        timeout_seconds=180,
    ),
}


def build_remote_prompt(history: str, user_msg: str, prompt_label: str) -> str:
    return f"Lịch sử:\n{history}\nUser: {user_msg}\n{prompt_label}:"


def call_remote_chatbot(system_name: str, history: str, user_msg: str, **generation_kwargs: Any) -> str:
    if system_name not in REMOTE_CHATBOTS:
        raise ValueError(f"Unsupported remote chatbot: {system_name}")

    config = REMOTE_CHATBOTS[system_name]
    base_url = os.getenv(config.env_var, "").strip().rstrip("/")
    if not base_url:
        raise RemoteChatbotUnavailable(
            f"{config.env_var} is not set. Start the Kaggle notebook for {config.prompt_label} and copy its ngrok URL into .env."
        )

    payload = {
        "prompt": build_remote_prompt(history, user_msg, config.prompt_label),
        **generation_kwargs,
    }
    response = requests.post(
        f"{base_url}/v1/generate",
        json=payload,
        timeout=config.timeout_seconds,
        headers={"ngrok-skip-browser-warning": "1"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RemoteChatbotUnavailable(f"{config.prompt_label} returned error: {data['error']}")
    return str(data.get("text") or data.get("response") or "").strip()


def healthcheck_remote_chatbot(system_name: str) -> dict[str, Any]:
    if system_name not in REMOTE_CHATBOTS:
        raise ValueError(f"Unsupported remote chatbot: {system_name}")
    config = REMOTE_CHATBOTS[system_name]
    base_url = os.getenv(config.env_var, "").strip().rstrip("/")
    if not base_url:
        return {"ok": False, "system": system_name, "error": f"{config.env_var} is not set"}
    try:
        response = requests.get(
            f"{base_url}/health",
            timeout=20,
            headers={"ngrok-skip-browser-warning": "1"},
        )
        response.raise_for_status()
        data = response.json()
        data["system"] = system_name
        return data
    except Exception as exc:
        return {"ok": False, "system": system_name, "error": str(exc)}
