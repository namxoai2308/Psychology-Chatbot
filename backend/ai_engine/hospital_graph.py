from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
import sqlite3
import os

from ai_engine.state import HospitalState
from ai_engine.agents.triage_agent import triage_node
from ai_engine.agents.departments import (
    cbt_phase_node, cbt_therapist_node,
    mbi_phase_node, mbi_therapist_node,
    ba_phase_node, ba_therapist_node
)
from ai_engine.agents.llm_service import generate_text_async, FAST_MODEL
from ai_engine.runtime import _PROMPTS, _render

_HISTORY_MAX_LINES = 20  # giữ 10 lượt gần nhất (mỗi lượt = 2 dòng)

async def crisis_node(state: HospitalState) -> HospitalState:
    print("KHOA CẤP CỨU: Kích hoạt Protocol Cứu hộ sinh mạng...")
    txt = await generate_text_async(
        model=FAST_MODEL,
        contents=_render(_PROMPTS.crisis, user_message=state["user_message"]),
        model_type=state.get("selected_model", "gemini")
    )
    return {"final_reply": txt.strip()}

def route_triage(state: HospitalState) -> str:
    if state.get("risk_level") == "CRITICAL":
        return "Crisis"
    
    dept = state.get("therapy_route", "CBT")
    if dept == "MBI":
        return "MBI_Phase"
    elif dept == "BA":
        return "BA_Phase"
    else:
        return "CBT_Phase"

async def memory_updater_node(state: HospitalState) -> HospitalState:
    new_msg = f"User: {state['user_message']}\nBot: {state.get('final_reply', '')}\n"
    lines = (state.get("chat_history", "") + new_msg).splitlines(keepends=True)
    hist = "".join(lines[-_HISTORY_MAX_LINES:])
    print(f"\n=> BÁC SĨ TRẢ LỜI:\n{state.get('final_reply', '')}")
    print("="*60 + "\n")
    return {"chat_history": hist}

builder = StateGraph(HospitalState)

# 1. Triage Department
builder.add_node("TriageDispatcher", triage_node)

# 2. CBT Department
builder.add_node("CBT_Phase", cbt_phase_node)
builder.add_node("CBT_Therapist", cbt_therapist_node)

# 3. MBI Department
builder.add_node("MBI_Phase", mbi_phase_node)
builder.add_node("MBI_Therapist", mbi_therapist_node)

# 4. BA Department
builder.add_node("BA_Phase", ba_phase_node)
builder.add_node("BA_Therapist", ba_therapist_node)

# 5. Crisis & Memory
builder.add_node("Crisis", crisis_node)
builder.add_node("MemoryUpdater", memory_updater_node)

# Routing Logic
builder.set_entry_point("TriageDispatcher")

builder.add_conditional_edges("TriageDispatcher", route_triage)

builder.add_edge("CBT_Phase", "CBT_Therapist")
builder.add_edge("CBT_Therapist", "MemoryUpdater")

builder.add_edge("MBI_Phase", "MBI_Therapist")
builder.add_edge("MBI_Therapist", "MemoryUpdater")

builder.add_edge("BA_Phase", "BA_Therapist")
builder.add_edge("BA_Therapist", "MemoryUpdater")

builder.add_edge("Crisis", "MemoryUpdater")
builder.add_edge("MemoryUpdater", END)

# Compile Graph with Persistent SQLite
db_path = os.path.join(os.path.dirname(__file__), "..", "database")
os.makedirs(db_path, exist_ok=True)
sqlite_conn = sqlite3.connect(os.path.join(db_path, "checkpoints.sqlite"), check_same_thread=False)

memory = SqliteSaver(sqlite_conn)
# memory.setup() has been removed in newer versions, it auto-creates tables on write.
hospital_app = builder.compile(checkpointer=memory)
