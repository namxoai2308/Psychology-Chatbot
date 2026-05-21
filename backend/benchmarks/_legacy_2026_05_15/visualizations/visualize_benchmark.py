import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def plot_benchmark_results():
    results_path = Path(__file__).resolve().parent / "results" / "benchmark_results.json"
    charts_dir = Path(__file__).resolve().parent / "results" / "charts"
    charts_dir.mkdir(exist_ok=True, parents=True)

    if not results_path.exists():
        print(f"File {results_path} không tồn tại. Hãy chạy benchmark_cbt.py trước.")
        return

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    valid_results = [r for r in results if "error" not in r["Evaluation"]]
    if not valid_results:
        print("Không có kết quả hợp lệ để vẽ biểu đồ.")
        return

    # Trích xuất dữ liệu của D2 (Therapeutic Approach) theo Agent A và B
    cases = []
    scores_a = []
    scores_b = []

    for r in valid_results:
        cases.append(r["Case_ID"].split("-")[2] if "GEN" in r["Case_ID"] else r["Case_ID"])
        eval_data = r["Evaluation"]
        scores_a.append(eval_data.get("Agent_A", {}).get("scores", {}).get("D2", 0))
        scores_b.append(eval_data.get("Agent_B", {}).get("scores", {}).get("D2", 0))

    x = np.arange(len(cases))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, scores_a, width, label='Agent A (Baseline)', color='#ff9999')
    rects2 = ax.bar(x + width/2, scores_b, width, label='Agent B (CBT System)', color='#66b3ff')

    ax.set_ylabel('Điểm D2 (Therapeutic Approach) / 4 Lên')
    ax.set_title('So sánh điểm tuân thủ trị liệu giữa Baseline và CBT System')
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=45, ha='right')
    ax.legend(loc='lower left')

    # Thêm số liệu lên đỉnh các cột
    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)

    fig.tight_layout()

    out_file = charts_dir / "cbt_comparison_chart.png"
    plt.savefig(out_file)
    print(f"✅ Đã tạo biểu đồ tại {out_file}")

if __name__ == "__main__":
    plot_benchmark_results()
