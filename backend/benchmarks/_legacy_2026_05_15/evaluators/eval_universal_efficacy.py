import json
import re
from ai_engine.agents.llm_service import generate_text

# ==========================================
# TRỤC 1: ĐÁNH GIÁ NĂNG LỰC LÂM SÀNG (UNIVERSAL EFFICACY)
# ==========================================

UNIVERSAL_RATER_PROMPT = """Bạn là Hội đồng chuyên gia Đánh giá Tâm lý học Lâm sàng. Nhiệm vụ của bạn là đánh giá năng lực của Therapist dựa trên Thang điểm chung Universal (1-7 điểm).
Hệ thống này hỗ trợ 3 liệu pháp: CBT (Nhận thức hành vi), MBI (Chánh niệm), BA (Kích hoạt hành vi).

Liệu pháp được hệ thống routing/phác đồ áp dụng: {therapy_route}

Lịch sử hội thoại:
{transcript}

[RUBRIC ĐÁNH GIÁ: THANG ĐIỂM 1-7]
1 = Kém, không có kỹ năng.
2 = Yếu.
3 = Trung bình yếu.
4 = Trung bình (Đạt chuẩn tối thiểu).
5 = Khá tốt.
6 = Rất tốt.
7 = Xuất sắc.

[CÁC TIÊU CHÍ UNIVERSAL]
1. Thấu cảm (Empathy): Thấu hiểu cảm xúc, validate cảm xúc thay vì bác bỏ.
2. Khám phá (Guided Discovery): Khơi gợi giúp bệnh nhân tự nhận ra vấn đề thay vì rao giảng.
3. Chiến lược (Strategy): Có định hướng mục tiêu chữa trị rõ ràng qua các lượt chat không?
4. Tuân thủ phác đồ (Adherence_To_Route): 
  - Nếu Route = CBT: Therapist có tập trung vào vòng lặp Suy nghĩ - Cảm xúc - Hành vi và dùng Socratic Question không?
  - Nếu Route = MBI: Therapist có hướng dẫn quan sát cảm xúc không phán xét, grounding, hoặc hít thở không?
  - Nếu Route = BA: Therapist có tập trung vào phá vỡ vòng lặp trì hoãn, thiết lập mục tiêu hành động nhỏ không?
  (Chấm điểm cao nếu áp dụng đúng kỹ thuật căn bản của liệu pháp {therapy_route}).

[YÊU CẦU OUTPUT]
Bạn bắt buộc phải trả về ĐÚNG 1 ĐỊNH DẠNG JSON duy nhất (không markdown).
Định dạng:
{{
  "Empathy": <int 1-7>,
  "Guided_Discovery": <int 1-7>,
  "Strategy": <int 1-7>,
  "Adherence": <int 1-7>,
  "Reasoning": "Lý do ngắn gọn chứng minh điểm số adherence với {therapy_route}"
}}
"""

def evaluate_universal_efficacy(transcript: str, therapy_route: str) -> dict:
    if not therapy_route or therapy_route == "UNKNOWN":
        therapy_route = "CBT (Mặc định)"
        
    prompt = UNIVERSAL_RATER_PROMPT.format(transcript=transcript, therapy_route=therapy_route)
    res = generate_text(model="llama-3.3-70b-versatile", contents=prompt, model_type="groq", config={"response_mime_type": "application/json"})
    
    try:
        cleaned = re.sub(r"```(?:json)?|```", "", res).strip()
        data = json.loads(cleaned)
        
        # Calculate Overall Average
        scores = [data.get("Empathy", 1), data.get("Guided_Discovery", 1), data.get("Strategy", 1), data.get("Adherence", 1)]
        data["Overall"] = round(sum(scores) / 4, 2)
        return data
    except Exception as e:
        return {
            "Empathy": 1, "Guided_Discovery": 1, "Strategy": 1, "Adherence": 1, "Overall": 1,
            "Reasoning": f"Error parsing eval: {str(e)}", "Raw": res
        }
