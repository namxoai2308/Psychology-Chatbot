from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import uuid
from typing import Optional

# Import đồ thị bệnh viện mới
from ai_engine.hospital_graph import hospital_app
from api.db import save_or_update_conversation, get_conversations, delete_conversation


router = APIRouter()


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=4000)
    user_name: str = ""
    thread_id: str = ""
    selected_model: str = "slm"  # Model selection: "gemini" or "slm"


class ChatResponse(BaseModel):
    reply: str
    safety: str = "SAFE"
    stage: str = "stage_1_venting"
    thread_id: str = ""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    input_state = {
        "user_message": req.user_message,
        "selected_model": req.selected_model
    }
    if req.user_name:
        input_state["user_name"] = req.user_name

    final_state = await hospital_app.ainvoke(
        input_state,
        config=config
    )
    # Save conversation metadata
    title = req.user_message[:40] + ("..." if len(req.user_message) > 40 else "")
    save_or_update_conversation(thread_id=thread_id, user_id="default_user", title=title)

    # 3. Trả về kết quả đầu ra
    return ChatResponse(
        reply=final_state.get("final_reply", "Xin lỗi, hệ thống đang bận."),
        safety=final_state.get("risk_level", "SAFE"),
        stage=final_state.get("current_phase", "stage_1_venting"),
        thread_id=thread_id
    )

@router.get("/conversations")
async def list_conversations(user_id: str = "default_user"):
    return {"conversations": get_conversations(user_id)}

@router.get("/conversations/{thread_id}/history")
async def get_chat_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    # Lấy state hiện tại từ LangGraph SqliteSaver
    state = hospital_app.get_state(config)
    if state and state.values:
        return {"chat_history": state.values.get("chat_history", "")}
    return {"chat_history": ""}

@router.delete("/conversations/{thread_id}")
async def delete_thread(thread_id: str):
    delete_conversation(thread_id)
    return {"status": "success"}
