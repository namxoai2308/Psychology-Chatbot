from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.db import delete_conversation, get_conversations
from api.schemas.chat import ChatRequest, ChatResponse
from api.services.chat_service import chat_service
from api.services.sse import encode_sse, graph_update_payload

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    thread_id, final_state = await chat_service.invoke(req)
    return chat_service.to_response(thread_id=thread_id, final_state=final_state)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        async for thread_id, update in chat_service.stream_updates(req):
            payload = graph_update_payload(update)
            if payload.get("done"):
                payload["thread_id"] = thread_id
            yield encode_sse(payload)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(user_id: str = "default_user"):
    return {"conversations": get_conversations(user_id)}


@router.get("/conversations/{thread_id}/history")
async def get_chat_history(thread_id: str):
    state = await chat_service.get_state(thread_id)
    return {"chat_history": state.get("chat_history", "")}


@router.delete("/conversations/{thread_id}")
async def delete_thread(thread_id: str):
    delete_conversation(thread_id)
    return {"status": "success"}
