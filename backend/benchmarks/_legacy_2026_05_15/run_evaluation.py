import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from benchmarks.core.evaluator import EvaluationEngine
from benchmarks.evaluators.efficacy_evaluator import EfficacyEvaluator
from benchmarks.evaluators.cape_evaluator import CAPEEvaluator
from benchmarks.evaluators.yalom_evaluator import YalomEvaluator
from benchmarks.runners.benchmark_utils import save_benchmark_results

load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="Run Benchmark Evaluations")
    parser.add_argument("--input", type=str, default="generated_transcripts.json", help="Input transcripts file")
    parser.add_argument("--evals", type=str, default="all", help="Comma separated evaluators (efficacy, cape)")
    parser.add_argument("--output_folder", type=str, default="unified_eval", help="Output folder in results")
    
    args = parser.parse_args()
    
    transcripts_path = backend_dir / "benchmarks" / "data" / args.input
    if not transcripts_path.exists():
        print(f"Error: Transcripts file {transcripts_path} not found. Run run_simulation.py first.")
        return

    with open(transcripts_path, "r", encoding="utf-8") as f:
        generated_data = json.load(f)
        
    evaluators = []
    selected_evals = args.evals.lower().split(",")
    if "all" in selected_evals or "efficacy" in selected_evals:
        evaluators.append(EfficacyEvaluator())
    if "all" in selected_evals or "cape" in selected_evals:
        evaluators.append(CAPEEvaluator())
    if "all" in selected_evals or "yalom" in selected_evals:
        evaluators.append(YalomEvaluator())
        
    engine = EvaluationEngine(evaluators)
    
    all_results = []
    
    print(f"[START] Running {len(evaluators)} evaluators on {len(generated_data)} cases...")
    
    for tc in generated_data:
        print(f"\n--- Evaluating Case: {tc['case_id']} ---")
        case_results = await engine.evaluate_case(tc)
        all_results.append({
            "case_id": tc["case_id"],
            "results": case_results
        })
        
        # Save intermediate
        save_benchmark_results(backend_dir, args.output_folder, "full_eval_results.json", all_results)

    # Aggregation (Optional - can be expanded to create radar charts etc)
    print(f"\n[DONE] Evaluation complete. Results saved in results/{args.output_folder}/full_eval_results.json")

if __name__ == "__main__":
    asyncio.run(main())
