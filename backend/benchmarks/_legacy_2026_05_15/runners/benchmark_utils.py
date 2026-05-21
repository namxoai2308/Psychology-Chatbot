import json
import sys
from pathlib import Path

def load_transcripts(transcripts_path: Path):
    """Load generated transcripts or exit if not found."""
    try:
        with open(transcripts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {transcripts_path}. Vui lòng chạy simulate_transcripts.py trước!")
        sys.exit(1)

def save_benchmark_results(backend_dir: Path, folder_name: str, file_name: str, data: dict) -> Path:
    """Create directory and save benchmark results."""
    out_dir = backend_dir / "benchmarks" / "results" / folder_name
    out_dir.mkdir(exist_ok=True, parents=True)
    json_path = out_dir / file_name
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    return json_path

def calculate_average_scores(scores_dict: dict, total_cases: int):
    """Average the scores for each metric in place."""
    for model in scores_dict:
        for k in scores_dict[model]:
            scores_dict[model][k] = round(scores_dict[model][k] / total_cases, 2)
