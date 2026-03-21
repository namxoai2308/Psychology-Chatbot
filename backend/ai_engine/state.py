from typing import TypedDict


class HospitalState(TypedDict):
    chat_history: str
    user_message: str
    user_name: str
    
    # 1. Routing Data (Từ Triage Dispatcher)
    risk_level: str           # "SAFE" hoặc "CRITICAL"
    intent: str               # "GREETING", "VENTING", "SEEKING_ADVICE", "CRISIS"
    therapy_route: str        # "CBT", "MBI", "BA", "NONE"
    
    # 2. Phase Data (Từ các Khoa)
    current_phase: str        # e.g., "stage_1_venting", "1_grounding", "1_activity_mapping"
    analyzer_data: str        # Báo cáo nội bộ của từng khoa (lỗi nhận thức, nhịp thở...)
    
    # 3. Output
    final_reply: str
