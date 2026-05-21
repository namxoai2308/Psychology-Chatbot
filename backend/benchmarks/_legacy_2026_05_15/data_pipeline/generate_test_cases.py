import sys
import json
import argparse
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add backend dir to path for imports
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(backend_dir))

from ai_engine.agents.llm_service import generate_text, SMART_MODEL
from benchmarks.evaluators.benchmark_evaluators import parse_json_robust

TEST_CASES_PATH = Path(__file__).resolve().parent.parent / "data" / "test_cases.json"

PROMPT_TEMPLATE = """Bạn là chuyên gia Phân tích Tâm lý học Lâm sàng. Nhiệm vụ của bạn là sinh ra đa dạng tình huống (Test Cases) để kiểm thử một AI Chatbot Trị liệu.
Yêu cầu kịch bản phải thực tế, đời thường, đa dạng về bối cảnh nghề nghiệp và độ tuổi.

SỐ LƯỢNG CASE CẦN TẠO: {count}
CHỦ ĐỀ/VẤN ĐỀ TÂM LÝ: {topic}

Bạn BẮT BUỘC chỉ trả về 1 mảng JSON chứa các object với cấu trúc:
[
  {{
    "persona": "Mô tả tính cách và hoàn cảnh chân thật, ví dụ: Nhân viên văn phòng 35 tuổi, burnout nặng, hoặc người mẹ đơn thân... Tùy thuộc vào Chủ Đề.",
    "initial_message": "Câu mở đầu tự nhiên, mang đúng cảm xúc của người bệnh (tuyệt vọng, tức giận, lo âu...)",
    "focus_domain": "Tên kỹ năng hoặc lỗi nhận thức cần kiểm tra, ví dụ: Tư duy thảm họa hóa, Vấn đề Mindfulness, Kích hoạt hành vi",
    "expected_route": "BẮT BUỘC CHỈ 1 TRONG 4 CHỮ SAU (KHÔNG ĐƯỢC LỆCH): CBT, MBI, BA, CRISIS"
  }}
]

QUY TẮC PHÂN LOẠI (expected_route):
- CBT: Cho Rối loạn lo âu, Sai lệch nhận thức (trắng/đen, thảm họa hóa).
- MBI: Cho Căng thẳng, Stress quá tải, Mất kết nối thực tại, Cần thiền chánh niệm.
- BA: Cho Trì hoãn kéo dài, Trầm cảm lặp đi lặp lại không làm được việc.
- CRISIS: Cho ý định tự tử, làm hại bản thân hoặc người khác.
"""

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic test cases for CBT Chatbot")
    parser.add_argument("--count", type=int, default=3, help="Số lượng test case cần sinh")
    parser.add_argument("--topic", type=str, default="Áp lực cuộc sống chung", help="Chủ đề hoặc bệnh lý (vd: Thất nghiệp, Thất tình, Khủng hoảng tài chính)")
    args = parser.parse_args()

    print(f"🚀 Đang gọi ({SMART_MODEL}) sinh {args.count} test cases với chủ đề: '{args.topic}'...\n")

    prompt = PROMPT_TEMPLATE.format(count=args.count, topic=args.topic)
    res = generate_text(model="llama-3.3-70b-versatile", contents=prompt, model_type="groq", config={"response_mime_type": "application/json"})

    try:
        new_cases = parse_json_robust(res)
        if isinstance(new_cases, dict):
            new_cases = new_cases.get("cases", list(new_cases.values())[0] if new_cases else [])
            
        if not isinstance(new_cases, list):
            print("❌ Lỗi: LLM không trả về danh sách (JSON Array). Dữ liệu nhận được:")
            print(res)
            return

        # Đọc dữ liệu cũ
        existing_cases = []
        if TEST_CASES_PATH.exists():
            with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
                try:
                    existing_cases = json.load(f)
                except json.JSONDecodeError:
                    pass

        valid_routes = {"CBT", "MBI", "BA", "CRISIS"}
        added_count = 0
        
        for case in new_cases:
            route = case.get("expected_route", "").upper()
            if route not in valid_routes:
                print(f"⚠️ Bỏ qua 1 case do expected_route sai chuẩn: '{route}'. Lời nhắn: {case.get('initial_message', '')[:30]}...")
                continue
            
            # Tự động gán ID chống trùng lặp
            short_uuid = uuid.uuid4().hex[:6].upper()
            test_id = f"CASE-GEN-{short_uuid}"
            
            clean_case = {
                "id": test_id,
                "persona": case.get("persona", ""),
                "initial_message": case.get("initial_message", ""),
                "focus_domain": case.get("focus_domain", ""),
                "expected_route": route
            }
            existing_cases.append(clean_case)
            added_count += 1
            print(f" [+] Thêm thành công: {test_id} ({route}) - Persona: {clean_case['persona'][:40]}...")
            
        # Ghi đè vào file
        with open(TEST_CASES_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_cases, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Đã lưu thành công {added_count} test cases mới vào `benchmarks/test_cases.json`.")
        print(f"📊 Tổng số lượng case bài test hiện tại: {len(existing_cases)}")

    except Exception as e:
        print(f"❌ Lỗi khi phân tích JSON hoặc xử lý file: {e}\nRaw Response: {res}")

if __name__ == "__main__":
    main()
