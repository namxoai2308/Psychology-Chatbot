from __future__ import annotations

from typing import Any


SYSTEMS = ["ours_multi_agent", "prompt_1_1", "soulchat", "mindchat", "base_model"]


DISPLAY_NAMES = {
    "ours_full": "Ours Full",
    "ours_multi_agent": "Ours Multi-Agent",
    "ours_no_peer": "Ours No Peer",
    "ours_no_validator": "Ours No Validator",
    "ours_no_safety_critic": "Ours No Safety Critic",
    "single_agent_stage_prompt": "Single Agent + Stage",
    "single_agent_plain": "Single Agent Plain",
    "prompt_1_1": "Prompt 1-1",
    "soulchat": "SoulChat",
    "mindchat": "MindChat",
    "base_model": "Base Model",
    "dry_run": "Dry Run",
    "ours_structural": "Ours Structural",
    "seallm": "SeaLLM",
    "camel": "CAMEL",
    "camel_cbt": "CAMEL-CBT",
}


METRIC_DISPLAY = {
    "clinical_safety": "Clinical Safety",
    "therapeutic_quality": "Therapeutic Quality",
    "modality_fidelity": "Modality Fidelity",
    "group_therapy_dynamics": "Group Therapy Dynamics",
    "conversation_progress": "Conversation Progress",
    "system_reliability": "System Reliability",
    "runtime_efficiency": "Runtime Efficiency",
}


def demo_summary() -> dict[str, Any]:
    """Stable demo summary for report/visual smoke tests before live benchmark exists."""
    return {
        "systems": SYSTEMS,
        "overall": {
            "ours_multi_agent": {
                "vsm_total": 86.2,
                "clinical_safety": 100.0,
                "therapeutic_quality": 84.1,
                "modality_fidelity": 88.0,
                "group_therapy_dynamics": 91.5,
                "conversation_progress": 86.4,
                "system_reliability": 95.2,
                "runtime_efficiency": 78.0,
                "fallback_rate": 12.0,
                "avg_latency_seconds": 4.2,
                "token_cost_estimate": 0.024,
            },
            "prompt_1_1": {
                "vsm_total": 74.1,
                "clinical_safety": 92.0,
                "therapeutic_quality": 81.0,
                "modality_fidelity": 61.3,
                "group_therapy_dynamics": None,
                "conversation_progress": 72.5,
                "system_reliability": 88.0,
                "runtime_efficiency": 86.0,
                "fallback_rate": None,
                "avg_latency_seconds": 2.1,
                "token_cost_estimate": 0.011,
            },
            "soulchat": {
                "vsm_total": 70.5,
                "clinical_safety": 88.0,
                "therapeutic_quality": 83.2,
                "modality_fidelity": 50.4,
                "group_therapy_dynamics": None,
                "conversation_progress": 70.0,
                "system_reliability": 84.5,
                "runtime_efficiency": 83.0,
                "fallback_rate": None,
                "avg_latency_seconds": 2.4,
                "token_cost_estimate": 0.013,
            },
            "mindchat": {
                "vsm_total": 68.7,
                "clinical_safety": 85.0,
                "therapeutic_quality": 78.8,
                "modality_fidelity": 52.1,
                "group_therapy_dynamics": None,
                "conversation_progress": 68.1,
                "system_reliability": 82.2,
                "runtime_efficiency": 82.0,
                "fallback_rate": None,
                "avg_latency_seconds": 2.5,
                "token_cost_estimate": 0.014,
            },
            "base_model": {
                "vsm_total": 55.2,
                "clinical_safety": 72.0,
                "therapeutic_quality": 65.0,
                "modality_fidelity": 30.0,
                "group_therapy_dynamics": None,
                "conversation_progress": 55.0,
                "system_reliability": 70.0,
                "runtime_efficiency": 92.0,
                "fallback_rate": None,
                "avg_latency_seconds": 1.8,
                "token_cost_estimate": 0.008,
            },
        },
        "route_performance": [
            {"system": "ours_multi_agent", "route": "CBT", "cases": 120, "stage_accuracy": 96.7, "technique_fidelity": 91.2, "route_bleed_count": 2, "validator_pass": 98.1, "fallback_rate": 10.0},
            {"system": "ours_multi_agent", "route": "MBI", "cases": 80, "stage_accuracy": 97.5, "technique_fidelity": 90.0, "route_bleed_count": 1, "validator_pass": 96.5, "fallback_rate": 8.7},
            {"system": "ours_multi_agent", "route": "BA", "cases": 80, "stage_accuracy": 95.8, "technique_fidelity": 89.5, "route_bleed_count": 2, "validator_pass": 97.0, "fallback_rate": 11.2},
            {"system": "prompt_1_1", "route": "CBT", "cases": 120, "stage_accuracy": 84.0, "technique_fidelity": 73.5, "route_bleed_count": 10, "validator_pass": 86.0, "fallback_rate": None},
            {"system": "prompt_1_1", "route": "MBI", "cases": 80, "stage_accuracy": 73.0, "technique_fidelity": 65.0, "route_bleed_count": 13, "validator_pass": 78.0, "fallback_rate": None},
            {"system": "prompt_1_1", "route": "BA", "cases": 80, "stage_accuracy": 76.0, "technique_fidelity": 68.0, "route_bleed_count": 12, "validator_pass": 80.0, "fallback_rate": None},
        ],
        "safety": {
            "ours_multi_agent": {"crisis_safe_response": 100.0, "unsafe_advice_violation": 0, "medical_boundary": 98.0, "dependency_boundary": 96.0, "adversarial_pass_rate": 97.5, "safety_gate_failures": 0},
            "prompt_1_1": {"crisis_safe_response": 94.0, "unsafe_advice_violation": 3, "medical_boundary": 88.0, "dependency_boundary": 82.0, "adversarial_pass_rate": 86.0, "safety_gate_failures": 5},
            "soulchat": {"crisis_safe_response": 90.0, "unsafe_advice_violation": 4, "medical_boundary": 84.0, "dependency_boundary": 80.0, "adversarial_pass_rate": 82.0, "safety_gate_failures": 7},
            "mindchat": {"crisis_safe_response": 88.0, "unsafe_advice_violation": 5, "medical_boundary": 82.0, "dependency_boundary": 78.0, "adversarial_pass_rate": 80.0, "safety_gate_failures": 8},
            "base_model": {"crisis_safe_response": 78.0, "unsafe_advice_violation": 11, "medical_boundary": 70.0, "dependency_boundary": 65.0, "adversarial_pass_rate": 68.0, "safety_gate_failures": 19},
        },
        "yalom_group": {
            "ours_multi_agent": {"peer_selection_accuracy": 93.5, "yalom_factor_match": 94.1, "nam_persona_validity": 96.0, "linh_persona_validity": 95.2, "peer_silence_accuracy": 97.0, "repetition_penalty": 3.1},
            "prompt_1_1": {},
            "soulchat": {},
            "mindchat": {},
            "base_model": {},
        },
        "yalom_factors": {"Universality": 94.0, "Catharsis": 91.5, "Hope": 95.0, "Interpersonal Learning": 92.0, "Peer Silence": 97.0},
        "failure_taxonomy": {
            "stage_mismatch": {"ours_multi_agent": 5, "prompt_1_1": 28, "soulchat": 31, "mindchat": 29, "base_model": 55},
            "route_bleed": {"ours_multi_agent": 5, "prompt_1_1": 35, "soulchat": 42, "mindchat": 40, "base_model": 80},
            "generic_response": {"ours_multi_agent": 8, "prompt_1_1": 38, "soulchat": 45, "mindchat": 48, "base_model": 90},
            "unsafe_advice": {"ours_multi_agent": 0, "prompt_1_1": 3, "soulchat": 4, "mindchat": 5, "base_model": 11},
            "over_empathy": {"ours_multi_agent": 6, "prompt_1_1": 20, "soulchat": 24, "mindchat": 21, "base_model": 35},
            "wrong_peer": {"ours_multi_agent": 4, "prompt_1_1": 0, "soulchat": 0, "mindchat": 0, "base_model": 0},
            "repeated_question": {"ours_multi_agent": 7, "prompt_1_1": 18, "soulchat": 22, "mindchat": 20, "base_model": 31},
            "schema_failure": {"ours_multi_agent": 2, "prompt_1_1": 0, "soulchat": 0, "mindchat": 0, "base_model": 0},
            "fallback_used": {"ours_multi_agent": 34, "prompt_1_1": 0, "soulchat": 0, "mindchat": 0, "base_model": 0},
        },
        "fallback_by_stage": {
            "cbt_stage_1_venting": 6.0,
            "cbt_stage_2_abc_model": 8.0,
            "cbt_stage_3_distortions": 9.5,
            "cbt_stage_4_socratic": 12.0,
            "cbt_stage_5_action": 14.0,
            "mbi_stage_1_grounding": 7.0,
            "mbi_stage_4_mindful_action": 10.5,
            "ba_stage_1_energy_check": 12.0,
            "ba_stage_2_micro_action": 8.5,
            "ba_stage_4_momentum_reward": 9.0,
        },
    }
