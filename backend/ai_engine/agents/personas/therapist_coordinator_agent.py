import asyncio
import random
from ai_engine.state import GroupTherapyState
from ai_engine.agents.llm_service import generate_text_async, FAST_MODEL
from ai_engine.runtime import _PROMPTS, _render

async def therapist_coordinator_agent(state: GroupTherapyState) -> GroupTherapyState:
    print("[FRONTSTAGE] Therapist Coordinator đang chốt lại...")
    
    drafts_list = state.get('drafts') or []
    draft_peer = "\n".join(m["text"] for m in drafts_list if m.get("sender") == "peer_mirror_agent")
    draft_veteran = "\n".join(m["text"] for m in drafts_list if m.get("sender") == "veteran_peer_agent")

    prompt = _render(
        _PROMPTS.therapist_coordinator,
        active_protocol=state.get("active_protocol"),
        user_message=state.get('user_message', ''),
        draft_peer=draft_peer,
        draft_veteran=draft_veteran,
        assessment=state.get('assessment', {}),
        cognitive_distortion=state.get('cognitive_distortion', 'None'),
        moderator_reason=state.get('moderator_reason', ''),
        doctor_action=state.get('doctor_action', 'SILENT'),
        chat_history=state.get('chat_history', '')
    )
    
    txt = await generate_text_async(model=FAST_MODEL, contents=prompt, model_type=state.get("selected_model", "gemini"))
    return {"drafts": [{"sender": "therapist_coordinator_agent", "text": txt.strip(), "typing_time_ms": int(random.uniform(3000, 6000))}]}
