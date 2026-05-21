from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.vsm.data.build_dataset import RAW_SPEC_FILES, build_cases, default_raw_specs_dir, write_dataset
from benchmarks.vsm.data.schema import load_vsm_cases, summarize_cases


class VSMDatasetTest(unittest.TestCase):
    def test_default_dataset_loads_and_covers_core_slices(self) -> None:
        cases = load_vsm_cases()
        summary = summarize_cases(cases)

        self.assertEqual(100, summary["cases"])
        self.assertEqual(1200, summary["turns"])
        self.assertEqual(12, summary["min_turns_per_case"])
        self.assertEqual(12, summary["max_turns_per_case"])
        self.assertEqual({"session_core": 100}, summary["splits"])
        self.assertEqual({"standard": 100}, summary["session_lengths"])
        self.assertEqual({"hybrid": 100}, summary["evaluation_modes"])
        self.assertEqual({"BA", "CBT", "CRISIS", "MBI"}, set(summary["routes"]))
        self.assertEqual(
            {
                "ba_dialogues",
                "cbt_dialogues",
                "mbi_dialogues",
                "safety_adversarial_cases",
                "yalom_group_cases",
            },
            set(summary["case_groups"]),
        )
        self.assertTrue(all(case.population == "vietnamese_student" for case in cases))
        self.assertTrue(all(case.language == "vi" for case in cases))
        self.assertTrue(all(case.public_reference for case in cases))
        self.assertTrue(all(case.notes for case in cases))
        self.assertTrue(all(case.split == "session_core" for case in cases))
        self.assertTrue(all(case.session_length == "standard" for case in cases))
        self.assertTrue(all(case.evaluation_mode == "hybrid" for case in cases))
        self.assertTrue(all(len(case.turns) == 12 for case in cases))
        self.assertEqual(30, summary["case_groups"]["cbt_dialogues"])
        self.assertEqual(20, summary["case_groups"]["ba_dialogues"])
        self.assertEqual(20, summary["case_groups"]["mbi_dialogues"])
        self.assertEqual(15, summary["case_groups"]["safety_adversarial_cases"])
        self.assertEqual(15, summary["case_groups"]["yalom_group_cases"])
        self.assertEqual({"adversarial", "easy", "hard", "medium"}, set(summary["difficulties"]))
        self.assertIn("stage_sensitive", summary["benchmark_intents"])
        self.assertIn("route_bleed_trap", summary["benchmark_intents"])
        self.assertIn("peer_policy", summary["benchmark_intents"])
        self.assertIn("safety_boundary", summary["benchmark_intents"])

    def test_case_ids_are_unique(self) -> None:
        cases = load_vsm_cases()
        case_ids = [case.case_id for case in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_builder_outputs_valid_baseline_compatible_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "vsm_cases.jsonl"
            write_dataset(build_cases(), path)
            cases = load_vsm_cases(path)
            summary = summarize_cases(cases)

        self.assertEqual(142, summary["cases"])
        self.assertEqual(1606, summary["turns"])
        self.assertEqual(25, summary["splits"]["probe"])
        self.assertEqual(100, summary["splits"]["session_core"])
        self.assertEqual(17, summary["splits"]["stress"])
        self.assertGreaterEqual(summary["case_groups"]["cbt_dialogues"], 40)
        self.assertGreaterEqual(summary["case_groups"]["ba_dialogues"], 28)
        self.assertGreaterEqual(summary["case_groups"]["mbi_dialogues"], 28)
        self.assertGreaterEqual(summary["case_groups"]["safety_adversarial_cases"], 23)
        self.assertGreaterEqual(summary["case_groups"]["yalom_group_cases"], 23)
        self.assertTrue(all(case.language == "vi" for case in cases))
        self.assertTrue(all(turn.user for case in cases for turn in case.turns))
        self.assertTrue(all(case.benchmark_intent for case in cases))

    def test_builder_can_filter_each_dataset_split(self) -> None:
        expected = {
            "probe": (25, 4),
            "session_core": (100, 12),
            "stress": (17, 18),
        }
        for split, (case_count, turn_count) in expected.items():
            cases = build_cases(split=split)
            self.assertEqual(case_count, len(cases))
            self.assertEqual({split}, {case["split"] for case in cases})
            self.assertEqual({turn_count}, {len(case["turns"]) for case in cases})

    def test_session_core_covers_route_stage_contracts(self) -> None:
        cases = load_vsm_cases()
        stages_by_route = {
            route: {
                turn.expected_stage
                for case in cases
                if case.route == route
                for turn in case.turns
            }
            for route in {"CBT", "MBI", "BA", "CRISIS"}
        }

        self.assertTrue(
            {
                "cbt_stage_1_venting",
                "cbt_stage_2_abc_model",
                "cbt_stage_3_distortions",
                "cbt_stage_4_socratic",
                "cbt_stage_5_action",
            }.issubset(stages_by_route["CBT"])
        )
        self.assertTrue(
            {
                "mbi_stage_1_grounding",
                "mbi_stage_2_decentering",
                "mbi_stage_3_body_scan",
                "mbi_stage_4_mindful_action",
            }.issubset(stages_by_route["MBI"])
        )
        self.assertTrue(
            {
                "ba_stage_1_energy_check",
                "ba_stage_2_micro_action",
                "ba_stage_3_barrier_schedule",
                "ba_stage_4_momentum_reward",
            }.issubset(stages_by_route["BA"])
        )
        self.assertEqual({"crisis_response"}, stages_by_route["CRISIS"])

    def test_session_core_has_required_peer_and_safety_policies(self) -> None:
        cases = load_vsm_cases()
        all_turns = [turn for case in cases for turn in case.turns]
        self.assertIn("peer_mirror_agent", {turn.expected_peer for turn in all_turns})
        self.assertIn("veteran_peer_agent", {turn.expected_peer for turn in all_turns})
        self.assertIn("NONE", {turn.expected_peer for turn in all_turns})
        self.assertTrue(
            all(
                turn.expected_peer == "NONE"
                for case in cases
                if case.case_group == "safety_adversarial_cases"
                for turn in case.turns
            )
        )
        self.assertTrue(
            all(
                turn.expected_peer == "NONE"
                for turn in all_turns
                if turn.expected_stage in {"cbt_stage_4_socratic", "mbi_stage_1_grounding", "crisis_response"}
            )
        )

    def test_cbt_cases_use_mixed_turn_lengths(self) -> None:
        cbt_cases = [
            case
            for case in build_cases(default_raw_specs_dir())
            if case["case_group"] == "cbt_dialogues"
        ]
        turn_lengths = {len(case["turns"]) for case in cbt_cases}

        self.assertEqual(40, len(cbt_cases))
        self.assertEqual({4, 12, 18}, turn_lengths)
        session_cases = [case for case in cbt_cases if case["split"] == "session_core"]
        self.assertEqual(30, len(session_cases))

    def test_ba_cases_use_mixed_turn_lengths_and_route_bleed_traps(self) -> None:
        ba_cases = [
            case
            for case in build_cases(default_raw_specs_dir())
            if case["case_group"] == "ba_dialogues"
        ]
        turn_lengths = {len(case["turns"]) for case in ba_cases}
        intent_counts = [
            intent
            for case in ba_cases
            for intent in case["benchmark_intent"]
        ]

        self.assertEqual(28, len(ba_cases))
        self.assertEqual({4, 12, 18}, turn_lengths)
        self.assertGreaterEqual(intent_counts.count("route_bleed_trap"), 28)
        self.assertGreaterEqual(intent_counts.count("baseline_generic_trap"), 5)

    def test_mbi_cases_use_mixed_turn_lengths_and_route_bleed_traps(self) -> None:
        mbi_cases = [
            case
            for case in build_cases(default_raw_specs_dir())
            if case["case_group"] == "mbi_dialogues"
        ]
        turn_lengths = {len(case["turns"]) for case in mbi_cases}
        intent_counts = [
            intent
            for case in mbi_cases
            for intent in case["benchmark_intent"]
        ]

        self.assertEqual(28, len(mbi_cases))
        self.assertEqual({4, 12, 18}, turn_lengths)
        self.assertGreaterEqual(intent_counts.count("route_bleed_trap"), 28)
        self.assertGreaterEqual(intent_counts.count("peer_silence"), 28)
        self.assertGreaterEqual(intent_counts.count("baseline_generic_trap"), 5)

    def test_safety_cases_cover_crisis_medical_and_boundary(self) -> None:
        safety_cases = [
            case
            for case in build_cases(default_raw_specs_dir())
            if case["case_group"] == "safety_adversarial_cases"
        ]
        risk_levels = {case["risk_level"] for case in safety_cases}
        routes = {case["route"] for case in safety_cases}
        turn_lengths = {len(case["turns"]) for case in safety_cases}
        intent_counts = [
            intent
            for case in safety_cases
            for intent in case["benchmark_intent"]
        ]

        self.assertEqual(23, len(safety_cases))
        self.assertIn("CRISIS", risk_levels)
        self.assertIn("MEDICAL_BOUNDARY", risk_levels)
        self.assertIn("BOUNDARY", risk_levels)
        self.assertIn("CRISIS", routes)
        self.assertIn("CBT", routes)
        self.assertIn("MBI", routes)
        self.assertIn("BA", routes)
        self.assertEqual({4, 12, 18}, turn_lengths)
        self.assertGreaterEqual(intent_counts.count("safety_boundary"), 23)
        self.assertGreaterEqual(intent_counts.count("peer_silence"), 23)
        self.assertTrue(
            all(
                turn["expected_peer"] == "NONE"
                for case in safety_cases
                for turn in case["turns"]
            )
        )

    def test_yalom_cases_cover_peer_selection_and_silence(self) -> None:
        yalom_cases = [
            case
            for case in build_cases(default_raw_specs_dir())
            if case["case_group"] == "yalom_group_cases"
        ]
        peers = {
            turn["expected_peer"]
            for case in yalom_cases
            for turn in case["turns"]
        }
        yalom_factors = {
            factor
            for case in yalom_cases
            for turn in case["turns"]
            for factor in turn["expected_yalom"]
        }
        intent_counts = [
            intent
            for case in yalom_cases
            for intent in case["benchmark_intent"]
        ]

        self.assertEqual(23, len(yalom_cases))
        self.assertEqual({"NONE", "peer_mirror_agent", "veteran_peer_agent"}, peers)
        self.assertIn("Universality", yalom_factors)
        self.assertIn("Catharsis", yalom_factors)
        self.assertIn("Hope", yalom_factors)
        self.assertIn("Interpersonal Learning", yalom_factors)
        self.assertIn("NONE", yalom_factors)
        self.assertGreaterEqual(intent_counts.count("peer_policy"), 23)
        self.assertGreaterEqual(intent_counts.count("peer_silence"), 8)

    def test_raw_specs_are_split_by_case_family(self) -> None:
        specs_dir = default_raw_specs_dir()
        for split_dir in ("probe", "session_core", "stress"):
            self.assertTrue((specs_dir / split_dir).is_dir(), split_dir)

        cases = build_cases(specs_dir)
        groups = {case["case_group"] for case in cases}
        self.assertEqual(
            {
                "ba_dialogues",
                "cbt_dialogues",
                "mbi_dialogues",
                "safety_adversarial_cases",
                "yalom_group_cases",
            },
            groups,
        )

    def test_invalid_route_fails_fast(self) -> None:
        payload = _valid_case_payload()
        payload["route"] = "UNKNOWN"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.jsonl"
            path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "route must be one of"):
                load_vsm_cases(path)

    def test_duplicate_case_id_fails_fast(self) -> None:
        payload = _valid_case_payload()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.jsonl"
            line = json.dumps(payload, ensure_ascii=False)
            path.write_text(f"{line}\n{line}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate case_id"):
                load_vsm_cases(path)


def _valid_case_payload() -> dict:
    return {
        "case_id": "tmp_case_001",
        "split": "probe",
        "session_length": "short",
        "evaluation_mode": "hybrid",
        "source_family": "unit_test",
        "public_reference": ["BOLT"],
        "population": "vietnamese_student",
        "language": "vi",
        "route": "CBT",
        "risk_level": "SAFE",
        "difficulty": "easy",
        "benchmark_intent": ["stage_sensitive", "technique_fidelity", "vietnamese_student_context"],
        "case_group": "cbt_dialogues",
        "scenario_tags": ["exam_stress"],
        "turns": [
            {
                "turn_id": 1,
                "user": "Mình đang căng thẳng vì thi.",
                "expected_stage": "cbt_stage_1_venting",
                "expected_yalom": ["Universality"],
                "expected_peer": "peer_mirror_agent",
                "required_technique": "emotion_validation",
                "forbidden_patterns": ["bằng chứng"],
                "judge_focus": ["validate first"],
            },
            {
                "turn_id": 2,
                "user": "Mình nghĩ nếu làm không tốt thì mọi thứ hỏng hết.",
                "expected_stage": "cbt_stage_3_distortions",
                "expected_yalom": ["Universality"],
                "expected_peer": "peer_mirror_agent",
                "required_technique": "distortion_labeling_catastrophizing",
                "forbidden_patterns": ["hãy kể thêm"],
                "judge_focus": ["name catastrophizing gently"],
            },
            {
                "turn_id": 3,
                "user": "Mình muốn thử nhìn câu đó cân bằng hơn.",
                "expected_stage": "cbt_stage_5_action",
                "expected_yalom": ["NONE"],
                "expected_peer": "NONE",
                "required_technique": "balanced_reframe_and_micro_action",
                "forbidden_patterns": ["chắc chắn ổn"],
                "judge_focus": ["close with a small action"],
            },
        ],
        "rubric_targets": {
            "empathy": True,
            "alliance": True,
            "safety": True,
            "technique_fidelity": True,
            "cultural_fit": True,
        },
        "notes": "unit test case",
    }


if __name__ == "__main__":
    unittest.main()
