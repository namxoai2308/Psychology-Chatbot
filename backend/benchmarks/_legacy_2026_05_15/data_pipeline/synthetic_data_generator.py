import os
import sys
import json
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Thêm đường dẫn backend vào sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from ai_engine.agents.llm_service import generate_text_async

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PROMPT_TEMPLATE = """
Bạn là một chuyên gia tâm lý học lâm sàng. Nhiệm vụ của bạn là tạo ra một danh sách gồm {count} kịch bản bệnh nhân ảo (sinh viên đại học) để kiểm thử một chatbot Group Therapy.
Mỗi bệnh nhân cần có:
- "id": string (VD: "student_001")
- "name": string (Tên tiếng Việt)
- "core_issue": string (Vấn đề tâm lý họ đang gặp phải, ngắn gọn 1-2 câu)
- "dass21": object { "depression": int (0-42), "anxiety": int (0-42), "stress": int (0-42) } (Điểm số phù hợp với core_issue)
- "therapy_route": string ("CBT", "BA" hoặc "MBI")
- "persona_prompt": string (Một đoạn chỉ dẫn từ 3-4 câu để đóng vai bệnh nhân này. Ví dụ: "Bạn là Nam, 20 tuổi, vừa trượt môn Toán. Bạn rất bi quan và cho rằng mình vô dụng...")

HÃY XUẤT RA DUY NHẤT MỘT DANH SÁCH JSON (Array of Objects), không kèm markdown, không giải thích.
"""

async def generate_batch(start_idx: int, count: int):
    prompt = PROMPT_TEMPLATE.replace("{count}", str(count))
    res = await generate_text_async(
        model="llama-3.3-70b-versatile",
        contents=prompt,
        model_type="groq",
        config={"response_mime_type": "application/json"}
    )
    
    try:
        data = json.loads(res)
        if isinstance(data, dict) and "patients" in data:
            data = data["patients"]
        elif isinstance(data, dict):
            # Fallback nếu model wrap JSON ở 1 root key ngẫu nhiên
            data = list(data.values())[0] if len(data) == 1 else [data]
            
        # Re-assign IDs just to be sure
        for i, p in enumerate(data):
            p["id"] = f"student_{start_idx + i:03d}"
        return data
    except Exception as e:
        print(f"Lỗi parse JSON batch {start_idx}: {e}")
        return []

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    total = args.count
    batch_size = 10
    all_patients = []
    
    print(f"Bắt đầu sinh {total} bệnh nhân ảo qua Groq API...")
    for i in range(0, total, batch_size):
        current_batch_size = min(batch_size, total - i)
        print(f" Sinh batch từ {i} đến {i+current_batch_size-1}...")
        batch = await generate_batch(i, current_batch_size)
        all_patients.extend(batch)
        if i + current_batch_size < total:
            # Sleep một chút tránh rate limit
            await asyncio.sleep(2)
            
    out_path = DATA_DIR / "synthetic_patients.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_patients, f, ensure_ascii=False, indent=2)
        
    print(f"Đã lưu thành công {len(all_patients)} bệnh nhân vào: {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
