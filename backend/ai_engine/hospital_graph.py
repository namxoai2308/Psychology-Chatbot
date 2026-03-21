from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ai_engine.state import HospitalState
from ai_engine.agents.triage_agent import triage_node
from ai_engine.agents.cbt_dept import cbt_phase_node, cbt_therapist_node
from ai_engine.agents.mbi_dept import mbi_phase_node, mbi_therapist_node
from ai_engine.agents.ba_dept import ba_phase_node, ba_therapist_node
from ai_engine.agents.gemini_client import generate_text, FAST_MODEL
from ai_engine.runtime import _PROMPTS

def crisis_node(state: HospitalState) -> HospitalState:
    print("🚨 KHOA CẤP CỨU: Kích hoạt Protocol Cứu hộ sinh mạng...")
    txt = generate_text(
        model=FAST_MODEL, 
        contents=_PROMPTS.crisis + f"\n\nTin nhắn người dùng: {state['user_message']}\nTherapist trả lời khẩn cấp:"
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

def memory_updater_node(state: HospitalState) -> HospitalState:
    new_msg = f"User: {state['user_message']}\nBot: {state.get('final_reply', '')}\n"
    hist = state.get("chat_history", "") + new_msg
    print(f"\n=> 💬 BÁC SĨ TRẢ LỜI:\n{state.get('final_reply', '')}")
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

# Compile Graph
memory = MemorySaver()
hospital_app = builder.compile(checkpointer=memory)
