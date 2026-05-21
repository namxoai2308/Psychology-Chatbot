import json
import re
from ai_engine.agents.llm_service import generate_text

# ==========================================
# TRỤC 2: ĐỘNG LỰC HỌC NHÓM (Yalom Factors)
# ==========================================

YALOM_RATER_PROMPT = """Bạn là Hội đồng chuyên gia Đánh giá Trị liệu Nhóm (Group Therapy).
Nhiệm vụ của bạn là đánh giá "Động lực học Nhóm" (Group Dynamics) dựa trên các Yếu tố Yalom (Yalom's Therapeutic Factors).
Bạn sẽ được cung cấp lịch sử hội thoại, và cần đánh giá trên thang điểm Likert từ 1 đến 5 sao.

Lịch sử hội thoại:
{transcript}

[RUBRIC ĐÁNH GIÁ: THANG ĐIỂM 1-5 SAO]
1 = Rất không đồng ý (Rất yếu, hầu như không có)
2 = Không đồng ý (Yếu)
3 = Bình thường/Phân vân
4 = Đồng ý 
5 = Rất đồng ý (Thể hiện cực kỳ rõ rệt, sinh động và hiệu quả)

[CÁC TIÊU CHÍ YALOM (Yalom Factors)]
1. Tính phổ quát (Universality): Bệnh nhân có được truyền đạt cảm giác rằng "Mình không cô đơn, người khác cũng từng trải qua chuyện này" không?
2. Gieo hy vọng (Altruism/Hope): Bệnh nhân có được truyền cảm hứng, hy vọng từ việc thấy người khác tiến bộ hoặc được gieo niềm tin vào quá trình không?
3. Sự gắn kết nhóm (Cohesion): Cảm giác an toàn, thuộc về nhóm và sự kết nối giữa các thành viên (User và các Agent) có mạch lạc, hỗ trợ nhau không?
4. Mức độ giảm phòng thủ (Reduced Defense): Không khí và sự chia sẻ có đủ an toàn để bệnh nhân hạ rào cản tâm lý, mở lòng nhanh hơn không?

[YÊU CẦU OUTPUT]
Bạn bắt buộc phải trả về ĐÚNG 1 ĐỊNH DẠNG JSON duy nhất (không markdown).
Định dạng:
{{
  "Universality": <float 1-5>,
  "Altruism_Hope": <float 1-5>,
  "Cohesion_ImpartingInfo": <float 1-5>,
  "Reduced_Defense": <float 1-5>,
  "Reasoning": "Lý do ngắn gọn chứng minh điểm số"
}}
"""

def evaluate_yalom(transcript: str) -> dict:
    prompt = YALOM_RATER_PROMPT.format(transcript=transcript)
    res = generate_text(model="llama-3.3-70b-versatile", contents=prompt, model_type="groq", config={"response_mime_type": "application/json"})
    
    try:
        cleaned = re.sub(r"```(?:json)?|```", "", res).strip()
        data = json.loads(cleaned)
        return data
    except Exception as e:
        return {
            "Universality": 1.0, "Altruism_Hope": 1.0, "Cohesion_ImpartingInfo": 1.0, "Reduced_Defense": 1.0,
            "Reasoning": f"Error parsing eval: {str(e)}"
        }
