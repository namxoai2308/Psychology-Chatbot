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

from benchmarks.core.simulation import PatientSimulator, SimulationEngine
from benchmarks.agents.llm_agent import LLMTherapistAgent
from benchmarks.agents.fsm_agent import FSMAgent
from benchmarks.agents.external_api_agent import ExternalAPIAgent
from benchmarks.agents.deepseek_agent import DeepSeekAgent

load_dotenv()

def get_agent_registry(case_id: str):
    """Returns a dictionary of all available agents."""
    return {
        "Base_LLM": LLMTherapistAgent(
            name="Base_LLM", 
            model="llama-3.3-70b-versatile",
            model_type="groq"
        ),
        "Prompt_Therapist": LLMTherapistAgent(
            name="Prompt_Therapist",
            system_prompt="Bạn là một Bác sĩ tâm lý trị liệu chung (Biết cả CBT, MBI, BA). Hãy lắng nghe, thấu cảm và đưa định hướng thích hợp. Luôn thông báo mình là AI, bảo vệ bí mật thông tin của khách hàng. Không khuyên những điều gây hại.",
            model="llama-3.3-70b-versatile",
            model_type="groq"
        ),
        "Ours_FSM_Multi": FSMAgent(
            name="Ours_FSM_Multi", 
            thread_id=f"{case_id}_groq", 
            model_provider="groq"
        ),
        "Ours_FSM_DeepSeek": FSMAgent(
            name="Ours_FSM_DeepSeek", 
            thread_id=f"{case_id}_ds", 
            model_provider="deepseek"
        ),
        "SoulChat": ExternalAPIAgent(
            name="SoulChat", 
            env_var_url="SOULCHAT_NGROK_URL"
        ),
        "MindChat": ExternalAPIAgent(
            name="MindChat", 
            env_var_url="MINDCHAT_NGROK_URL"
        ),
        "DeepSeek": DeepSeekAgent(
            name="DeepSeek_Baseline"
        )
    }

async def main():
    parser = argparse.ArgumentParser(description="Run Benchmark Simulations")
    parser.add_argument("--cases", type=int, default=3, help="Number of cases to run")
    parser.add_argument("--turns", type=int, default=3, help="Number of turns per session")
    parser.add_argument("--models", type=str, default="all", help="Comma separated list of models to run (or 'all')")
    parser.add_argument("--input", type=str, default="synthetic_patients.json", help="Input file name in data directory")
    parser.add_argument("--output", type=str, default="generated_transcripts.json", help="Output file name in data directory")
    
    args = parser.parse_args()
    
    data_dir = backend_dir / "benchmarks" / "data"
    input_path = data_dir / args.input
    output_path = data_dir / args.output
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)
    
    cases_to_run = test_cases[:args.cases]
    
    patient_sim = PatientSimulator()
    engine = SimulationEngine(patient_sim)
    
    results = []
    
    target_models = args.models.split(",") if args.models != "all" else None
    
    print(f"[START] Running simulation for {len(cases_to_run)} cases...")
    
    for tc in cases_to_run:
        case_id = tc["id"]
        print(f"\n--- Processing Case: {case_id} ---")
        
        agent_registry = get_agent_registry(case_id)
        
        case_transcripts = {}
        fsm_computed_route = "CBT" # Default
        
        for model_name, agent in agent_registry.items():
            if target_models and model_name not in target_models:
                continue
                
            print(f"  [WAIT] Running model: {model_name}...")
            session_res = await engine.run_session(agent, tc, num_turns=args.turns)
            
            case_transcripts[model_name] = session_res["transcript"]
            
            # Extract FSM route if available
            if "Ours_FSM" in model_name:
                fsm_computed_route = session_res["final_state"].get("therapy_route", fsm_computed_route)

        results.append({
            "case_id": case_id,
            "fsm_route": fsm_computed_route,
            "transcripts": case_transcripts
        })
        
        # Save intermediate results to prevent data loss
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] Simulation complete. Results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
