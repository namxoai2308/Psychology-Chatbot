import json
import logging

from ai_engine.state import GroupTherapyState
from ai_engine.dass_triage import calculate_dass21, assign_department
from ai_engine.services.protocol_loader import load_protocol
from ai_engine.services.safety import is_crisis_input

logger = logging.getLogger(__name__)

async def onboarding_node(state: GroupTherapyState) -> GroupTherapyState:
    if is_crisis_input(state.get("user_message", ""), state.get("chat_history", "")):
        return {"risk_level": "CRITICAL", "intent": "CRISIS", "therapy_route": "NONE", "ui_action": "NONE"}
        
    logger.info("Checking DASS-21 onboarding state.")
    
    status = state.get("onboarding_status", "not_started")
    user_message = state.get("user_message", "").strip()
    user_name = state.get("user_name", "bạn")

    if status == "not_started" or status == "waiting_for_dass_consent":
        logger.info("Showing DASS-21 form.")
        return {
            "onboarding_status": "dass21_asking",
            "ui_action": "SHOW_DASS21",
            "final_reply": "Cảm ơn bạn. Mời bạn làm bài khảo sát ngay lập tức nhé. Đừng dành quá nhiều thời gian suy nghĩ, hãy chọn đáp án đúng với bạn nhất trong MỘT TUẦN QUA."
        }
    
    if status == "dass21_asking":
        logger.info("Parsing DASS-21 payload.")
        try:
            answers = []
            if user_message.startswith("{") and "DASS21" in user_message:
                data = json.loads(user_message)
                answers = data.get("DASS21", [])
            elif user_message.startswith("[DASS21_SUBMIT]"):
                parts = user_message.split(":")
                ans_str = parts[1].strip()
                answers = [int(x) for x in ans_str.split(",")]
            else:
                answers = json.loads(user_message)
            
            if isinstance(answers, list) and len(answers) == 21:
                dass_result = calculate_dass21(answers)
                triage_decision = assign_department(dass_result)
                
                logger.info(
                    "DASS-21 parsed. route=%s mode=%s",
                    triage_decision["assigned_dept"],
                    triage_decision["persona_mode"],
                )
                
                return {
                    "onboarding_status": "completed",
                    "ui_action": "NONE",
                    "assessment": dass_result["scores"],
                    "therapy_route": triage_decision["assigned_dept"],
                    "active_protocol": load_protocol(triage_decision["assigned_dept"]),
                    "user_message": "Tôi đã làm xong bài kiểm tra.",
                    "peer_drafts": "CLEAR",
                    "peer_contribution_decisions": "CLEAR",
                }
            else:
                logger.warning("Invalid DASS-21 payload length.")
                return {
                    "ui_action": "SHOW_DASS21",
                    "final_reply": "Lỗi: Form DASS-21 cần 21 lựa chọn hợp lệ. Vui lòng thử lại."
                }
        except Exception as e:
            logger.warning("Failed to parse DASS-21 payload: %s", e)
            return {
                "ui_action": "SHOW_DASS21",
                "final_reply": "Mình không thu thập được kết quả, hãy thử điền lại nhé."
            }

    return {}
