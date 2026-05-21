from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_ROUTES = {"CBT", "MBI", "BA", "CRISIS"}
VALID_RISK_LEVELS = {"SAFE", "BOUNDARY", "MEDICAL_BOUNDARY", "CRISIS"}
VALID_CASE_GROUPS = {
    "cbt_dialogues",
    "mbi_dialogues",
    "ba_dialogues",
    "yalom_group_cases",
    "safety_adversarial_cases",
}
VALID_PEERS = {"peer_mirror_agent", "veteran_peer_agent", "NONE"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "adversarial"}
VALID_BENCHMARK_INTENTS = {
    "stage_sensitive",
    "route_bleed_trap",
    "peer_policy",
    "peer_silence",
    "safety_boundary",
    "cultural_context",
    "long_context",
    "baseline_generic_trap",
    "technique_fidelity",
    "vietnamese_student_context",
}
VALID_SPLITS = {"probe", "session_core", "stress"}
VALID_SESSION_LENGTHS = {"short", "standard", "long"}
VALID_EVALUATION_MODES = {"deterministic", "llm_judge", "hybrid"}
TURN_LIMITS_BY_SPLIT = {
    "probe": (3, 5),
    "session_core": (12, 12),
    "stress": (18, 18),
}
REQUIRED_RUBRIC_TARGETS = {
    "empathy",
    "alliance",
    "safety",
    "technique_fidelity",
    "cultural_fit",
}


@dataclass(frozen=True)
class VSMTurn:
    turn_id: int
    user: str
    expected_stage: str
    expected_yalom: list[str]
    expected_peer: str
    required_technique: str
    forbidden_patterns: list[str]
    judge_focus: list[str]


@dataclass(frozen=True)
class VSMCase:
    case_id: str
    split: str
    session_length: str
    evaluation_mode: str
    source_family: str
    public_reference: list[str]
    population: str
    language: str
    route: str
    risk_level: str
    difficulty: str
    benchmark_intent: list[str]
    case_group: str
    scenario_tags: list[str]
    turns: list[VSMTurn]
    rubric_targets: dict[str, bool]
    notes: str


def default_dataset_path() -> Path:
    return Path(__file__).with_name("vsm_session_core.jsonl")


def load_vsm_cases(path: str | Path | None = None) -> list[VSMCase]:
    dataset_path = Path(path) if path else default_dataset_path()
    if not dataset_path.exists():
        raise FileNotFoundError(f"VSM dataset not found: {dataset_path}")

    cases: list[VSMCase] = []
    seen_ids: set[str] = set()
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc

            case = _parse_case(payload, line_number)
            if case.case_id in seen_ids:
                raise ValueError(f"Duplicate case_id at line {line_number}: {case.case_id}")
            seen_ids.add(case.case_id)
            cases.append(case)

    if not cases:
        raise ValueError(f"VSM dataset is empty: {dataset_path}")
    return cases


def summarize_cases(cases: list[VSMCase]) -> dict[str, Any]:
    route_counts = Counter(case.route for case in cases)
    group_counts = Counter(case.case_group for case in cases)
    split_counts = Counter(case.split for case in cases)
    session_length_counts = Counter(case.session_length for case in cases)
    evaluation_mode_counts = Counter(case.evaluation_mode for case in cases)
    difficulty_counts = Counter(case.difficulty for case in cases)
    intent_counts = Counter(intent for case in cases for intent in case.benchmark_intent)
    turn_count = sum(len(case.turns) for case in cases)
    turn_lengths = [len(case.turns) for case in cases]
    return {
        "cases": len(cases),
        "turns": turn_count,
        "min_turns_per_case": min(turn_lengths),
        "max_turns_per_case": max(turn_lengths),
        "routes": dict(sorted(route_counts.items())),
        "splits": dict(sorted(split_counts.items())),
        "session_lengths": dict(sorted(session_length_counts.items())),
        "evaluation_modes": dict(sorted(evaluation_mode_counts.items())),
        "case_groups": dict(sorted(group_counts.items())),
        "difficulties": dict(sorted(difficulty_counts.items())),
        "benchmark_intents": dict(sorted(intent_counts.items())),
    }


def _parse_case(payload: dict[str, Any], line_number: int) -> VSMCase:
    case_id = _required_str(payload, "case_id", line_number)
    route = _required_str(payload, "route", line_number)
    risk_level = _required_str(payload, "risk_level", line_number)
    difficulty = _required_str(payload, "difficulty", line_number)
    case_group = _required_str(payload, "case_group", line_number)
    split = _required_str(payload, "split", line_number)
    session_length = _required_str(payload, "session_length", line_number)
    evaluation_mode = _required_str(payload, "evaluation_mode", line_number)

    if route not in VALID_ROUTES:
        raise ValueError(f"{case_id}: route must be one of {sorted(VALID_ROUTES)}, got {route!r}")
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"{case_id}: risk_level must be one of {sorted(VALID_RISK_LEVELS)}, got {risk_level!r}"
        )
    if case_group not in VALID_CASE_GROUPS:
        raise ValueError(
            f"{case_id}: case_group must be one of {sorted(VALID_CASE_GROUPS)}, got {case_group!r}"
        )
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"{case_id}: difficulty must be one of {sorted(VALID_DIFFICULTIES)}, got {difficulty!r}"
        )
    if split not in VALID_SPLITS:
        raise ValueError(f"{case_id}: split must be one of {sorted(VALID_SPLITS)}, got {split!r}")
    if session_length not in VALID_SESSION_LENGTHS:
        raise ValueError(
            f"{case_id}: session_length must be one of {sorted(VALID_SESSION_LENGTHS)}, got {session_length!r}"
        )
    if evaluation_mode not in VALID_EVALUATION_MODES:
        raise ValueError(
            f"{case_id}: evaluation_mode must be one of {sorted(VALID_EVALUATION_MODES)}, got {evaluation_mode!r}"
        )

    public_reference = _required_str_list(payload, "public_reference", line_number)
    benchmark_intent = _required_str_list(payload, "benchmark_intent", line_number)
    invalid_intents = sorted(set(benchmark_intent) - VALID_BENCHMARK_INTENTS)
    if invalid_intents:
        raise ValueError(
            f"{case_id}: benchmark_intent contains unsupported values: {invalid_intents}"
        )
    scenario_tags = _required_str_list(payload, "scenario_tags", line_number)
    turns_payload = payload.get("turns")
    min_turns, max_turns = TURN_LIMITS_BY_SPLIT[split]
    if not isinstance(turns_payload, list) or not min_turns <= len(turns_payload) <= max_turns:
        if min_turns == max_turns:
            raise ValueError(f"{case_id}: {split} cases must contain exactly {min_turns} turns")
        raise ValueError(f"{case_id}: {split} cases must contain {min_turns}-{max_turns} turns")

    turns = [_parse_turn(case_id, route, turn_payload, index) for index, turn_payload in enumerate(turns_payload, 1)]
    rubric_targets = payload.get("rubric_targets")
    if not isinstance(rubric_targets, dict):
        raise ValueError(f"{case_id}: rubric_targets must be an object")
    missing = REQUIRED_RUBRIC_TARGETS - set(rubric_targets)
    if missing:
        raise ValueError(f"{case_id}: rubric_targets missing keys: {sorted(missing)}")
    for key in REQUIRED_RUBRIC_TARGETS:
        if not isinstance(rubric_targets[key], bool):
            raise ValueError(f"{case_id}: rubric_targets.{key} must be boolean")

    return VSMCase(
        case_id=case_id,
        split=split,
        session_length=session_length,
        evaluation_mode=evaluation_mode,
        source_family=_required_str(payload, "source_family", line_number),
        public_reference=public_reference,
        population=_required_str(payload, "population", line_number),
        language=_required_str(payload, "language", line_number),
        route=route,
        risk_level=risk_level,
        difficulty=difficulty,
        benchmark_intent=benchmark_intent,
        case_group=case_group,
        scenario_tags=scenario_tags,
        turns=turns,
        rubric_targets=dict(rubric_targets),
        notes=_required_str(payload, "notes", line_number),
    )


def _parse_turn(case_id: str, route: str, payload: Any, turn_number: int) -> VSMTurn:
    if not isinstance(payload, dict):
        raise ValueError(f"{case_id} turn {turn_number}: turn must be an object")

    turn_id = payload.get("turn_id", turn_number)
    if not isinstance(turn_id, int) or turn_id < 1:
        raise ValueError(f"{case_id} turn {turn_number}: turn_id must be a positive integer")

    expected_stage = _required_str(payload, "expected_stage", turn_number)
    _validate_stage_prefix(case_id, route, expected_stage, turn_number)

    expected_yalom = _required_str_list(payload, "expected_yalom", turn_number)
    expected_peer = _required_str(payload, "expected_peer", turn_number)
    if expected_peer not in VALID_PEERS:
        raise ValueError(
            f"{case_id} turn {turn_number}: expected_peer must be one of {sorted(VALID_PEERS)}, "
            f"got {expected_peer!r}"
        )
    if expected_yalom == ["NONE"] and expected_peer != "NONE":
        raise ValueError(f"{case_id} turn {turn_number}: expected_peer must be NONE when expected_yalom is NONE")

    return VSMTurn(
        turn_id=turn_id,
        user=_required_str(payload, "user", turn_number),
        expected_stage=expected_stage,
        expected_yalom=expected_yalom,
        expected_peer=expected_peer,
        required_technique=_required_str(payload, "required_technique", turn_number),
        forbidden_patterns=_required_str_list(payload, "forbidden_patterns", turn_number),
        judge_focus=_required_str_list(payload, "judge_focus", turn_number),
    )


def _validate_stage_prefix(case_id: str, route: str, expected_stage: str, turn_number: int) -> None:
    expected_prefix = {
        "CBT": "cbt_",
        "MBI": "mbi_",
        "BA": "ba_",
        "CRISIS": "crisis_response",
    }[route]
    if route == "CRISIS":
        if expected_stage != expected_prefix:
            raise ValueError(f"{case_id} turn {turn_number}: CRISIS route must use crisis_response stage")
        return
    if not expected_stage.startswith(expected_prefix):
        raise ValueError(
            f"{case_id} turn {turn_number}: {route} expected_stage must start with {expected_prefix!r}, "
            f"got {expected_stage!r}"
        )


def _required_str(payload: dict[str, Any], key: str, line_number: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line/turn {line_number}: {key} must be a non-empty string")
    return value


def _required_str_list(payload: dict[str, Any], key: str, line_number: int) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"line/turn {line_number}: {key} must be a non-empty string array")
    return list(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and summarize the VSM inference dataset.")
    parser.add_argument("--dataset", type=Path, default=default_dataset_path())
    args = parser.parse_args()

    cases = load_vsm_cases(args.dataset)
    summary = summarize_cases(cases)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
