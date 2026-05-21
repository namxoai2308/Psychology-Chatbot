import logging

from ai_engine.state import GroupTherapyState
from ai_engine.blackboard.psychosocial_safety import assess_psychosocial_safety, safety_fallback
from ai_engine.services.safety import clean_toxic_advice, is_unsafe_output

logger = logging.getLogger(__name__)
LEGACY_LINH_LABEL = "Chị" + " Linh"

def guardrails_node(state: GroupTherapyState) -> GroupTherapyState:
    logger.info("Guardrails packaging final output.")
    processed_output = []
    final_output = state.get("final_output") or []
    safety_critic_enabled = bool(state.get("safety_critic_enabled", True))
    
    persona_names = {
        "peer_mirror_agent": "Nam",
        "veteran_peer_agent": "Linh",
        "therapist_coordinator_agent": "Nhà trị liệu",
    }
    
    for msg in final_output:
        sender_id = msg.get("sender")
        if sender_id in persona_names:
            cleaned = clean_toxic_advice(msg.get("text", ""))
            if is_unsafe_output(cleaned):
                logger.warning("Blocked unsafe output from %s", sender_id)
                continue
            processed_output.append({
                "sender": persona_names.get(sender_id, sender_id), 
                "text": cleaned,
                "typing_time_ms": msg.get("typing_time_ms", 3000)
            })

    combined_text = "\n".join(f"[{msg['sender']}]: {msg['text']}" for msg in processed_output)
    if safety_critic_enabled:
        safety_report = assess_psychosocial_safety(
            user_message=state.get("user_message", ""),
            assistant_text=combined_text,
            chat_history=state.get("chat_history", ""),
            safety_flags=state.get("safety_flags", {}),
        )
        if safety_report.get("high_risk"):
            logger.warning("Guardrails replaced output after psychosocial safety critic high-risk flag.")
            processed_output = [{
                "sender": "Nhà trị liệu",
                "text": safety_fallback(safety_report),
                "typing_time_ms": 3000,
            }]
    else:
        safety_report = {
            "overall_severity": "disabled",
            "critics": [],
            "high_risk": False,
            "medium_risk": False,
        }

    if not processed_output:
        processed_output = [{
            "sender": "Nhà trị liệu",
            "text": "Tôi muốn giữ cuộc trò chuyện này an toàn cho bạn. Nếu bạn đang thấy mình có nguy cơ làm hại bản thân hoặc người khác, hãy liên hệ ngay với người thân tin cậy hoặc dịch vụ khẩn cấp tại nơi bạn sống.",
            "typing_time_ms": 3000,
        }]
        
    # Build text thuần cho CLI mode
    cli_reply = ""
    for msg in processed_output:
        cli_reply += f"[{msg['sender']}]: {msg['text']}\n"
    peer_state = _next_peer_state(state, processed_output)
        
    return {
        "final_output": processed_output,
        "final_reply": cli_reply.strip(),
        "psychosocial_safety": safety_report,
        "system_variant": state.get("system_variant", "ours_full"),
        "variant": state.get("variant", state.get("system_variant", "ours_full")),
        "therapy_route": state.get("therapy_route"),
        "current_stage": state.get("current_stage", state.get("current_phase")),
        "peer_used": any(msg.get("sender") in {"Nam", "Linh", LEGACY_LINH_LABEL} for msg in processed_output),
        **peer_state,
        "validator_enabled": bool(state.get("validator_enabled", True)),
        "safety_critic_enabled": safety_critic_enabled,
        "fallback_used": bool(state.get("fallback_used", False)),
    }


def _next_peer_state(state: GroupTherapyState, processed_output: list[dict]) -> dict:
    peer_senders = [
        _peer_sender_id(str(msg.get("sender") or ""))
        for msg in processed_output
        if _peer_sender_id(str(msg.get("sender") or ""))
    ]
    previous_sender = state.get("last_peer_sender")
    previous_count = int(state.get("consecutive_peer_turns") or 0)
    previous_cooldown = int(state.get("peer_silence_cooldown") or 0)
    current_sender = peer_senders[-1] if peer_senders else None
    if not current_sender:
        return {
            "last_peer_sender": previous_sender,
            "consecutive_peer_turns": 0,
            "peer_silence_cooldown": max(0, previous_cooldown - 1),
        }
    consecutive = previous_count + 1 if current_sender == previous_sender else 1
    return {
        "last_peer_sender": current_sender,
        "consecutive_peer_turns": consecutive,
        "peer_silence_cooldown": 1 if current_sender == "veteran_peer_agent" else 0,
    }


def _peer_sender_id(sender: str) -> str | None:
    if sender == "Nam":
        return "peer_mirror_agent"
    if sender in {"Linh", LEGACY_LINH_LABEL}:
        return "veteran_peer_agent"
    return None
