from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ai_engine.agents.clinical_assessor_node import _deterministic_yalom_factors
from ai_engine.blackboard.ba_milestones import BAMilestoneState
from ai_engine.blackboard.cbt_milestones import CBTMilestoneState
from ai_engine.blackboard.mbi_milestones import MBIMilestoneState
from benchmarks.vsm.adapters.systems import _detect_stage_without_llm, _structural_peer, _yalom_case_factors
from benchmarks.vsm.data.schema import load_vsm_cases


def audit_dataset(dataset: str | Path) -> dict[str, Any]:
    cases = load_vsm_cases(dataset)
    stage_mismatches: list[dict[str, Any]] = []
    peer_mismatches: list[dict[str, Any]] = []
    stage_by_group: Counter[str] = Counter()
    peer_by_group: Counter[str] = Counter()
    stage_by_turn: Counter[str] = Counter()
    peer_by_turn: Counter[str] = Counter()
    turn_count = 0

    for case in cases:
        previous_stage: str | None = None
        chat_history: list[str] = []
        cbt_milestones = CBTMilestoneState(strict_pacing=True)
        mbi_milestones = MBIMilestoneState()
        ba_milestones = BAMilestoneState()
        peer_state: dict[str, Any] = {"last_peer_sender": None, "consecutive_peer_turns": 0, "peer_silence_cooldown": 0}

        for turn in case.turns:
            rendered_history = "\n".join(chat_history)
            stage_decision = _detect_stage_without_llm(
                case,
                turn,
                previous_stage,
                rendered_history,
                cbt_milestones,
                mbi_milestones,
                ba_milestones,
            )
            observed_stage = stage_decision.current_stage
            if case.case_group == "yalom_group_cases":
                factors = _yalom_case_factors(case, turn, observed_stage)
            elif case.case_group == "safety_adversarial_cases":
                factors = ["NONE"]
            else:
                factors = _deterministic_yalom_factors(
                    case.route,
                    observed_stage,
                    turn.user,
                    rendered_history,
                    peer_state=peer_state,
                )
            observed_peer = _structural_peer(case, turn, observed_stage, factors)
            turn_count += 1

            if observed_stage != turn.expected_stage:
                mismatch = _mismatch_row(case, turn, "stage", turn.expected_stage, observed_stage, factors)
                stage_mismatches.append(mismatch)
                stage_by_group[case.case_group] += 1
                stage_by_turn[f"{case.case_group}:turn_{turn.turn_id}"] += 1
            if observed_peer != turn.expected_peer:
                mismatch = _mismatch_row(case, turn, "peer", turn.expected_peer, observed_peer, factors)
                peer_mismatches.append(mismatch)
                peer_by_group[case.case_group] += 1
                peer_by_turn[f"{case.case_group}:turn_{turn.turn_id}"] += 1

            peer_state = _next_peer_state(peer_state, observed_peer)
            previous_stage = observed_stage
            chat_history.append(f"User: {turn.user}")

    return {
        "dataset": str(dataset),
        "case_count": len(cases),
        "turn_count": turn_count,
        "stage_mismatch_count": len(stage_mismatches),
        "peer_mismatch_count": len(peer_mismatches),
        "stage_mismatch_rate": round(len(stage_mismatches) / max(turn_count, 1), 4),
        "peer_mismatch_rate": round(len(peer_mismatches) / max(turn_count, 1), 4),
        "stage_by_group": dict(stage_by_group),
        "peer_by_group": dict(peer_by_group),
        "stage_by_turn": dict(stage_by_turn),
        "peer_by_turn": dict(peer_by_turn),
        "stage_mismatches": stage_mismatches,
        "peer_mismatches": peer_mismatches,
    }


def _mismatch_row(case, turn, mismatch_type: str, expected: str, observed: str, factors: list[str]) -> dict[str, Any]:
    return {
        "case_group": case.case_group,
        "case_id": case.case_id,
        "route": case.route,
        "turn_id": turn.turn_id,
        "mismatch_type": mismatch_type,
        "expected": expected,
        "observed": observed,
        "required_yalom_factors": factors,
        "user": turn.user,
    }


def _next_peer_state(previous: dict[str, Any], observed_peer: str) -> dict[str, Any]:
    if observed_peer == "NONE":
        return {"last_peer_sender": None, "consecutive_peer_turns": 0, "peer_silence_cooldown": 0}
    consecutive = int(previous.get("consecutive_peer_turns") or 0) + 1 if previous.get("last_peer_sender") == observed_peer else 1
    return {"last_peer_sender": observed_peer, "consecutive_peer_turns": consecutive, "peer_silence_cooldown": 1}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit deterministic stage/peer contract over a VSM dataset without API calls.")
    parser.add_argument("--dataset", default="backend/benchmarks/vsm/data/vsm_session_core.jsonl")
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args()

    summary = audit_dataset(args.dataset)
    payload = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
