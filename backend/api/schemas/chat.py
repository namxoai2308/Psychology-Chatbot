from __future__ import annotations

from pydantic import BaseModel, Field

from ai_engine.graph.variants import SystemVariant


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=4000)
    user_name: str = ""
    user_id: str = "default_user"
    thread_id: str = ""
    selected_model: str = "slm"
    system_variant: SystemVariant = SystemVariant.OURS_FULL


class ChatResponse(BaseModel):
    reply: str
    messages: list = Field(default_factory=list)
    safety: str = "SAFE"
    stage: str = "stage_1_venting"
    thread_id: str = ""
    ui_action: str = "NONE"
    system_variant: str = SystemVariant.OURS_FULL.value
    route: str | None = None
    peer_used: bool | None = None
    fallback_used: bool | None = None
    latency_ms: float | None = None
