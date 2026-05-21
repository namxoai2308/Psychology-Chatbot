from __future__ import annotations

import uuid
import time
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_engine.graph.builder import build_graph
from ai_engine.graph.variants import normalize_system_variant, variant_flags
from ai_engine.services.config import get_settings
from api.db import save_or_update_conversation
from api.schemas.chat import ChatRequest, ChatResponse


@lru_cache(maxsize=8)
def _graph_builder(system_variant: str):
    return build_graph(system_variant)


class ChatService:
    def __init__(self) -> None:
        self._db_path = get_settings().checkpoint_db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def make_thread_id(self, thread_id: str | None = None) -> str:
        return thread_id or str(uuid.uuid4())

    def build_input_state(self, req: ChatRequest) -> dict[str, Any]:
        variant = normalize_system_variant(req.system_variant)
        state: dict[str, Any] = {
            "user_message": req.user_message,
            "user_id": req.user_id or "default_user",
            "selected_model": req.selected_model,
            "peer_drafts": None,
            "peer_contribution_decisions": None,
            **variant_flags(variant),
        }
        if req.user_name:
            state["user_name"] = req.user_name
        return state

    def save_metadata(self, *, thread_id: str, user_id: str, user_message: str) -> None:
        title = user_message[:40] + ("..." if len(user_message) > 40 else "")
        save_or_update_conversation(thread_id=thread_id, user_id=user_id or "default_user", title=title)

    async def invoke(self, req: ChatRequest) -> tuple[str, dict[str, Any]]:
        thread_id = self.make_thread_id(req.thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        variant = normalize_system_variant(req.system_variant)
        start = time.perf_counter()
        async with AsyncSqliteSaver.from_conn_string(str(self._db_path)) as memory:
            app = _graph_builder(variant.value).compile(checkpointer=memory)
            final_state = await app.ainvoke(self.build_input_state(req), config=config)
        final_state["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        self.save_metadata(thread_id=thread_id, user_id=req.user_id, user_message=req.user_message)
        return thread_id, final_state

    async def get_state(self, thread_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": thread_id}}
        async with AsyncSqliteSaver.from_conn_string(str(self._db_path)) as memory:
            app = _graph_builder("ours_full").compile(checkpointer=memory)
            state = await app.aget_state(config)
            if state and state.values:
                return dict(state.values)
        return {}

    def to_response(self, *, thread_id: str, final_state: dict[str, Any]) -> ChatResponse:
        return ChatResponse(
            reply=final_state.get("final_reply", "Xin lỗi, hệ thống đang bận."),
            messages=final_state.get("final_output", []),
            safety=final_state.get("risk_level", "SAFE"),
            stage=final_state.get("current_stage", final_state.get("current_phase", "stage_1_venting")),
            thread_id=thread_id,
            ui_action=final_state.get("ui_action", "NONE"),
            system_variant=final_state.get("system_variant", final_state.get("variant", "ours_full")),
            route=final_state.get("therapy_route"),
            peer_used=final_state.get("peer_used"),
            fallback_used=final_state.get("fallback_used"),
            latency_ms=final_state.get("latency_ms"),
        )

    async def stream_updates(self, req: ChatRequest):
        thread_id = self.make_thread_id(req.thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        input_state = self.build_input_state(req)
        variant = normalize_system_variant(req.system_variant)
        start = time.perf_counter()
        final_state: dict[str, Any] = {}
        async with AsyncSqliteSaver.from_conn_string(str(self._db_path)) as memory:
            app = _graph_builder(variant.value).compile(checkpointer=memory)
            async for update in app.astream(input_state, config=config, stream_mode="updates"):
                yield thread_id, update
            state = await app.aget_state(config)
            if state and state.values:
                final_state = dict(state.values)
        final_state["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        self.save_metadata(thread_id=thread_id, user_id=req.user_id, user_message=req.user_message)
        yield thread_id, {"__done__": True, "__metadata__": self.metadata_payload(final_state)}

    def metadata_payload(self, final_state: dict[str, Any]) -> dict[str, Any]:
        return {
            "system_variant": final_state.get("system_variant", final_state.get("variant", "ours_full")),
            "route": final_state.get("therapy_route"),
            "stage": final_state.get("current_stage", final_state.get("current_phase")),
            "peer_used": final_state.get("peer_used"),
            "validator_enabled": final_state.get("validator_enabled"),
            "safety_critic_enabled": final_state.get("safety_critic_enabled"),
            "fallback_used": final_state.get("fallback_used"),
            "latency_ms": final_state.get("latency_ms"),
        }


chat_service = ChatService()
