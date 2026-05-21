from __future__ import annotations

import logging

from ai_engine.blackboard.state import GroupTherapyState
from ai_engine.blackboard.psychosocial_safety import assess_psychosocial_safety
from ai_engine.services.llm_service import FAST_MODEL, generate_text_async
from ai_engine.services.config import get_settings

logger = logging.getLogger(__name__)


async def crisis_node(state: GroupTherapyState) -> GroupTherapyState:
    logger.warning("Crisis protocol activated; peer observers bypassed.")
    text = (
        "Nếu bạn đang gặp nguy hiểm hoặc có thể làm hại bản thân, hãy gọi dịch vụ khẩn cấp "
        "tại nơi bạn sống hoặc liên hệ ngay với một người thân tin cậy ở cạnh bạn. Tôi sẽ "
        "giữ phản hồi thật trực tiếp và tập trung vào an toàn của bạn trong lượt này."
    )
    return {
        "risk_level": "CRITICAL",
        "therapy_route": "CRISIS",
        "current_stage": "crisis_response",
        "current_phase": "crisis_response",
        "system_variant": state.get("system_variant", "ours_full"),
        "variant": state.get("variant", state.get("system_variant", "ours_full")),
        "stage_goal": "Immediate safety response and real-world support.",
        "required_yalom_factors": ["NONE"],
        "psychosocial_safety": assess_psychosocial_safety(
            user_message=state.get("user_message", ""),
            chat_history=state.get("chat_history", ""),
            safety_flags={"crisis": True},
        ),
        "peer_drafts": "CLEAR",
        "peer_contribution_decisions": "CLEAR",
        "peer_used": False,
        "validator_enabled": bool(state.get("validator_enabled", True)),
        "safety_critic_enabled": bool(state.get("safety_critic_enabled", True)),
        "fallback_used": False,
        "crisis_protocol_used": True,
        "final_output": [{"sender": "therapist_coordinator_agent", "text": text, "typing_time_ms": 1000}],
        "final_reply": f"[Nhà trị liệu]: {text}",
    }


async def single_agent_plain_node(state: GroupTherapyState) -> GroupTherapyState:
    msg = state.get("user_message", "")
    if not msg:
        return {}
    prompt = (
        "Bạn là một chatbot hỗ trợ tâm lý sinh viên bằng tiếng Việt. "
        "Không chẩn đoán, không kê đơn, không thay thế chuyên gia. "
        "Hãy trả lời ngắn gọn, ấm áp, hỏi tối đa một câu tiếp theo.\n\n"
        f"Lịch sử:\n{state.get('chat_history', '')}\n\n"
        f"Người dùng: {msg}"
    )
    text = await _generate_single_agent_text(state, prompt)
    return _single_agent_update(state, text, current_stage=None)


async def single_agent_stage_prompt_node(state: GroupTherapyState) -> GroupTherapyState:
    msg = state.get("user_message", "")
    if not msg:
        return {}
    route = state.get("therapy_route", "CBT")
    stage = state.get("current_stage", state.get("current_phase", "unknown"))
    stage_goal = state.get("stage_goal", "")
    prompt = (
        "Bạn là một chatbot hỗ trợ tâm lý sinh viên bằng tiếng Việt. "
        "Bạn nhận route/stage từ hệ thống nhưng không dùng peer agents hay blackboard planning. "
        "Không chẩn đoán, không kê đơn, không thay thế chuyên gia. "
        "Hãy dùng đúng một kỹ thuật phù hợp stage và hỏi tối đa một câu.\n\n"
        f"Route: {route}\nStage: {stage}\nStage goal: {stage_goal}\n\n"
        f"Lịch sử:\n{state.get('chat_history', '')}\n\n"
        f"Người dùng: {msg}"
    )
    text = await _generate_single_agent_text(state, prompt)
    return _single_agent_update(state, text, current_stage=str(stage))


async def _generate_single_agent_text(state: GroupTherapyState, prompt: str) -> str:
    try:
        text = await generate_text_async(
            model=FAST_MODEL,
            contents=prompt,
            model_type=state.get("selected_model", "gemini"),
        )
    except Exception as exc:
        logger.warning("Single-agent variant fallback after generation error: %s", exc)
        text = ""
    return text.strip() or (
        "Mình đang lắng nghe bạn. Điều an toàn và quan trọng nhất lúc này là mình đi chậm lại: "
        "phần nào trong chuyện này đang làm bạn thấy nặng nhất?"
    )


def _single_agent_update(state: GroupTherapyState, text: str, current_stage: str | None) -> GroupTherapyState:
    return {
        "therapy_route": state.get("therapy_route"),
        "current_stage": current_stage,
        "current_phase": current_stage,
        "system_variant": state.get("system_variant", "ours_full"),
        "variant": state.get("variant", state.get("system_variant", "ours_full")),
        "required_yalom_factors": ["NONE"],
        "peer_drafts": "CLEAR",
        "peer_contribution_decisions": "CLEAR",
        "peer_used": False,
        "validator_enabled": bool(state.get("validator_enabled", False)),
        "safety_critic_enabled": bool(state.get("safety_critic_enabled", True)),
        "fallback_used": False,
        "final_output": [{"sender": "therapist_coordinator_agent", "text": text, "typing_time_ms": 1000}],
    }


async def memory_updater_node(state: GroupTherapyState) -> GroupTherapyState:
    new_msg = f"User: {state['user_message']}\nBot: {state.get('final_reply', '')}\n"
    current_hist = state.get("chat_history", "") + new_msg
    parts = [part for part in current_hist.split("User: ") if part.strip()]
    recent_parts = parts[-get_settings().history_max_turns :]
    hist = "User: " + "User: ".join(recent_parts) if recent_parts else ""
    return {"chat_history": hist}


def route_onboarding(state: GroupTherapyState) -> str:
    if state.get("risk_level") == "CRITICAL":
        return "Crisis"
    if state.get("onboarding_status") == "completed":
        return "Clinical_Assessor"
    return "MemoryUpdater"


def make_onboarding_router(next_node: str):
    def _route(state: GroupTherapyState) -> str:
        if state.get("risk_level") == "CRITICAL":
            return "Crisis"
        if state.get("onboarding_status") == "completed":
            return next_node
        return "MemoryUpdater"

    return _route
