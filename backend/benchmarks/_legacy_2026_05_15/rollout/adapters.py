"""Baselines: one LLM/HTTP reply per user turn. Ours: LangGraph + DASS bootstrap."""
from __future__ import annotations

import os
import uuid
from typing import Any

import requests
from langgraph.checkpoint.memory import MemorySaver

from ai_engine.services.llm_service import generate_text
from ai_engine.hospital_graph import builder

from benchmarks.rollout.schema_cases import BenchmarkCase


def _chat_model(model_type: str) -> str:
    if model_type == "deepseek":
        return os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    return os.getenv("FAST_MODEL", "gemini-2.5-flash")


def _history_append(history: str, user: str, assistant: str) -> str:
    return f"{history}\nUser: {user}\nAssistant: {assistant}\n".strip()


def baseline_base(history: str, user_msg: str, *, model_type: str) -> str:
    prompt = f"Lịch sử:\n{history}\nUser: {user_msg}\nAssistant:"
    return generate_text(model=_chat_model(model_type), contents=prompt, model_type=model_type).strip()


def baseline_prompt_1_1(history: str, user_msg: str, route_hint: str, *, model_type: str) -> str:
    prompt = f"""Bạn là nhà trị liệu 1-1 (AI). Ngữ cảnh: định hướng điều trị chính là {route_hint} theo sàng lọc.
Thấu cảm, không phán xét, không khuyên gây hại, không kê đơn.
Lịch sử:\n{history}\nUser: {user_msg}\nTrị liệu viên:"""
    return generate_text(model=_chat_model(model_type), contents=prompt, model_type=model_type).strip()


def _remote_generate(url: str, label: str, history: str, user_msg: str) -> str:
    if not url:
        return f"{label}: URL not set (MINDCHAT_NGROK_URL / SOULCHAT_NGROK_URL)"
    prompt = f"Lịch sử:\n{history}\nUser: {user_msg}\n{label}:"
    try:
        r = requests.post(
            f"{url.rstrip('/')}/v1/generate",
            json={"prompt": prompt},
            timeout=120,
            headers={"ngrok-skip-browser-warning": "1"},
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("text") or data.get("response") or "").strip()
    except Exception as e:
        return f"{label} error: {e}"


def baseline_mindchat(history: str, user_msg: str, *, model_type: str) -> str:
    if model_type == "deepseek":
        prompt = f"""[MindChat — chatbot hỗ trợ sức khỏe tâm thần, tiếng Việt, câu ngắn, ấm áp.]
Lịch sử:\n{history}\nUser: {user_msg}\nMindChat:"""
        return generate_text(model=_chat_model(model_type), contents=prompt, model_type=model_type).strip()
    return _remote_generate(os.getenv("MINDCHAT_NGROK_URL", ""), "MindChat", history, user_msg)


def baseline_soulchat(history: str, user_msg: str, *, model_type: str) -> str:
    if model_type == "deepseek":
        prompt = f"""[SoulChat — chatbot đồng cảm, tiếng Việt, tập trung lắng nghe, không phán xét.]
Lịch sử:\n{history}\nUser: {user_msg}\nSoulChat:"""
        return generate_text(model=_chat_model(model_type), contents=prompt, model_type=model_type).strip()
    return _remote_generate(os.getenv("SOULCHAT_NGROK_URL", ""), "SoulChat", history, user_msg)


def run_baseline_trajectory(
    system: str,
    case_route_hint: str,
    user_turns: list[str],
    *,
    model_type: str,
) -> dict[str, Any]:
    history = f"[Ngữ cảnh: định hướng điều trị {case_route_hint} theo DASS-21.]\n"
    turns_out: list[dict[str, Any]] = []
    for i, um in enumerate(user_turns, start=1):
        if system == "base_llm":
            reply = baseline_base(history, um, model_type=model_type)
        elif system == "prompt_1_1":
            reply = baseline_prompt_1_1(history, um, case_route_hint, model_type=model_type)
        elif system == "mindchat":
            reply = baseline_mindchat(history, um, model_type=model_type)
        elif system == "soulchat":
            reply = baseline_soulchat(history, um, model_type=model_type)
        else:
            raise ValueError(system)
        turns_out.append({"turn_id": i, "user_msg": um, "assistant_msg": reply})
        history = _history_append(history, um, reply)
    return {"predicted_route": None, "turns": turns_out, "transcript": history}


async def run_ours_trajectory(case: BenchmarkCase, *, model_type: str, thread_id: str | None = None) -> dict[str, Any]:
    memory = MemorySaver()
    app = builder.compile(checkpointer=memory)
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}

    turns_out: list[dict[str, Any]] = []
    tid_line = 0
    pred_route = "UNKNOWN"

    async def invoke(msg: str) -> dict[str, Any]:
        nonlocal tid_line, pred_route
        tid_line += 1
        st = await app.ainvoke(
            {
                "user_message": msg,
                "selected_model": model_type,
                "peer_drafts": None,
                "peer_contribution_decisions": None,
            },
            config=config,
        )
        msgs = st.get("final_output") or []
        if msgs:
            text = "\n".join(f"[{m.get('sender')}]: {m.get('text')}" for m in msgs)
        else:
            text = (st.get("final_reply") or "").strip()
        risk = st.get("risk_level", "SAFE")
        route = st.get("therapy_route")
        if isinstance(route, str) and route.upper() in ("CBT", "MBI", "BA"):
            pred_route = route.upper()
        turns_out.append(
            {
                "turn_id": tid_line,
                "user_msg": msg if len(msg) <= 240 else msg[:240] + "...",
                "assistant_msg": text,
                "risk_pred": risk,
                "therapy_route": route,
                "peer_contribution_decisions": st.get("peer_contribution_decisions", []),
            }
        )
        return st

    await invoke(".")
    dass_line = f"[DASS21_SUBMIT]: {','.join(str(x) for x in case.dass21_answers)}"
    await invoke(dass_line)

    for um in case.user_turns:
        await invoke(um)

    lines = [f"User: {t['user_msg']}\nAssistant: {t['assistant_msg']}" for t in turns_out]
    transcript = "\n\n".join(lines)
    return {"predicted_route": pred_route, "turns": turns_out, "transcript": transcript, "thread_id": tid}
