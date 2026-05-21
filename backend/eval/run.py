import sys
import os
import asyncio
import json

# Tự động thêm thư mục backend vào path để tránh lỗi import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from eval.engine import EvaluationEngine

async def run_inference():
    engine = EvaluationEngine()
    
    # Load cases
    with open("backend/eval/cases.json", "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    print("🚀 Bắt đầu quá trình lấy Output từ Raw Models (Không chấm điểm)...")
    print(f"📊 Số lượng Test Cases: {len(cases)}")
    print("-" * 50)

    # Chạy cho 2 con Raw Model trên Kaggle
    agents_to_test = [
        {"name": "Raw_MindChat", "url": engine.mindchat_url},
        {"name": "Raw_SoulChat", "url": engine.soulchat_url}
    ]

    all_outputs = []

    for agent_info in agents_to_test:
        name = agent_info["name"]
        print(f"\n🤖 Đang chạy mô hình: {name}")
        
        agent_results = {"agent_name": name, "cases": []}
        
        for case in cases:
            print(f"  📂 Case: {case['name']}...", end=" ", flush=True)
            
            try:
                # Chạy 10 lượt hội thoại
                responses = await engine.run_raw_session(agent_info["url"], case)
                
                # Tạo transcript
                dialogue = []
                for i, user_msg in enumerate(case["user_turns"]):
                    dialogue.append({
                        "turn": i + 1,
                        "user": user_msg,
                        "assistant": responses[i]
                    })
                
                agent_results["cases"].append({
                    "case_id": case["id"],
                    "case_name": case["name"],
                    "dialogue": dialogue
                })
                print("✅ Xong!")
                
            except Exception as e:
                print(f"❌ Lỗi: {e}")
        
        all_outputs.append(agent_results)

    # Lưu kết quả Transcript
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"backend/eval/results/raw_outputs_{timestamp}.json"
    os.makedirs("backend/eval/results", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_outputs, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print("✅ HOÀN TẤT THU THẬP OUTPUT!")
    print(f"📁 Kết quả transcript đã được lưu tại: {output_path}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_inference())
