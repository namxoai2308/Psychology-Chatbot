from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import uuid
from typing import Optional

# Import đồ thị bệnh viện mới
from ai_engine.hospital_graph import hospital_app


router = APIRouter()


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=4000)
    user_name: str = ""
    thread_id: str = ""


class ChatResponse(BaseModel):
    reply: str
    safety: str = "SAFE"
    stage: str = "stage_1_venting"
    thread_id: str = ""


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    input_state = {"user_message": req.user_message}
    if req.user_name:
        input_state["user_name"] = req.user_name

    final_state = hospital_app.invoke(
        input_state,
        config=config
    )
    # 3. Trả về kết quả đầu ra
    return ChatResponse(
        reply=final_state.get("final_reply", "Xin lỗi, hệ thống đang bận."),
        safety=final_state.get("risk_level", "SAFE"),
        stage=final_state.get("current_phase", "stage_1_venting"),
        thread_id=thread_id
    )
