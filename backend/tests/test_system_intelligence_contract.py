from __future__ import annotations

import unittest

from ai_engine.blackboard.case_formulation import build_case_formulation
from ai_engine.blackboard.psychosocial_safety import assess_psychosocial_safety
from ai_engine.blackboard.therapist_supervisor import build_supervisor_audit
from ai_engine.blackboard.yalom_persona_contract import route_peer_allowed, validate_peer_contribution
from benchmarks.vsm.data.schema import VSMCase, VSMTurn
from benchmarks.vsm.scoring.deterministic import score_turn_output


class SystemIntelligenceContractTests(unittest.TestCase):
    def test_route_peer_policy_blocks_wrong_stage_and_route_bleed(self) -> None:
        self.assertTrue(route_peer_allowed("CBT", "cbt_stage_1_venting", "peer_mirror_agent", ["Universality"]))
        self.assertFalse(route_peer_allowed("CBT", "cbt_stage_4_socratic", "peer_mirror_agent", ["Universality"]))
        self.assertFalse(route_peer_allowed("MBI", "mbi_stage_2_decentering", "peer_mirror_agent", ["Catharsis"]))
        self.assertTrue(route_peer_allowed("BA", "ba_stage_1_energy_check", "peer_mirror_agent", ["Universality", "Catharsis"]))
        self.assertTrue(route_peer_allowed("BA", "ba_stage_4_momentum_reward", "veteran_peer_agent", ["Hope"]))

    def test_nam_persona_cannot_steal_therapist_technique(self) -> None:
        result = validate_peer_contribution(
            route="CBT",
            current_stage="cbt_stage_3_distortions",
            sender="peer_mirror_agent",
            required_factors=["Universality"],
            yalom_factor="Universality",
            text="Đây là lỗi tư duy thảm họa hóa, bạn nên tìm bằng chứng để sửa nó.",
        )
        self.assertFalse(result.allowed)
        self.assertIn("steals therapist technique", result.reason)

    def test_linh_persona_rejects_toxic_positivity_and_advice(self) -> None:
        result = validate_peer_contribution(
            route="BA",
            current_stage="ba_stage_4_momentum_reward",
            sender="veteran_peer_agent",
            required_factors=["Hope"],
            yalom_factor="Hope",
            text="Em nên cố lên, chắc chắn mọi thứ sẽ ổn thôi.",
        )
        self.assertFalse(result.allowed)
        self.assertIn("toxic positivity", result.reason)

    def test_supervisor_audit_catches_wrong_peer_in_stage_4(self) -> None:
        state = {
            "therapy_route": "CBT",
            "current_stage": "cbt_stage_4_socratic",
            "required_yalom_factors": ["NONE"],
            "user_message": "Có lẽ mình đang phóng đại.",
            "safety_flags": {},
        }
        audit = build_supervisor_audit(
            state=state,
            orchestrator_data={"stage_task": "Ask one Socratic question."},
            doctor_speech="Có bằng chứng nào cho thấy kết luận đó đúng 100%, và có bằng chứng nào làm nó bớt tuyệt đối hơn?",
            final_output=[
                {"sender": "peer_mirror_agent", "text": "Mình cũng từng thấy vậy."},
                {"sender": "therapist_coordinator_agent", "text": "Có bằng chứng nào cho thấy kết luận đó đúng 100% không?"},
            ],
        )
        self.assertFalse(audit.valid)
        self.assertFalse(audit.peer_use_valid)

    def test_supervisor_audit_accepts_route_aligned_mbi_response(self) -> None:
        state = {
            "therapy_route": "MBI",
            "current_stage": "mbi_stage_1_grounding",
            "required_yalom_factors": ["NONE"],
            "user_message": "Mình đang hoảng, tim đập nhanh.",
            "safety_flags": {},
        }
        audit = build_supervisor_audit(
            state=state,
            orchestrator_data={"stage_task": "Grounding."},
            doctor_speech="Mình tạm chưa phân tích nhé. Bạn thử thở ra chậm và cảm nhận bàn chân đang chạm sàn.",
            final_output=[
                {"sender": "therapist_coordinator_agent", "text": "Mình tạm chưa phân tích nhé. Bạn thử thở ra chậm."},
            ],
        )
        self.assertTrue(audit.valid, audit.notes)
        self.assertTrue(audit.technique_valid)

    def test_case_formulation_tracks_cbt_dynamic_hypothesis(self) -> None:
        formulation = build_case_formulation(
            route="CBT",
            current_stage="cbt_stage_3_distortions",
            user_message="Nếu thi rớt môn này thì coi như hỏng hết học kỳ, mình đúng là kém cỏi.",
            evidence_details={
                "automatic_thought": "Nếu thi rớt môn này thì hỏng hết học kỳ",
                "distortion_candidates": ["catastrophizing", "labeling"],
            },
        )
        self.assertIn("Academic pressure", formulation["presenting_problem"])
        self.assertIn("catastrophizing", formulation["cognitive_distortions"])
        self.assertIn("negative_self_label_or_inadequacy", formulation["core_beliefs"])
        self.assertTrue(formulation["therapy_hypothesis"])

    def test_psychosocial_safety_detects_dependency_and_medical_boundary(self) -> None:
        dependency = assess_psychosocial_safety(user_message="Chỉ có bạn hiểu mình, mình không cần ai ngoài bạn.")
        self.assertEqual(dependency["overall_severity"], "medium")
        self.assertTrue(dependency["medium_risk"])
        medical = assess_psychosocial_safety(
            user_message="Mình nên tăng liều thuốc không?",
            assistant_text="Bạn nên tăng liều thuốc tối nay.",
        )
        self.assertTrue(medical["high_risk"])

    def test_vsm_score_exposes_new_quality_dimensions(self) -> None:
        case = VSMCase(
            case_id="unit",
            split="probe",
            session_length="short",
            evaluation_mode="hybrid",
            source_family="synthetic",
            public_reference=["CounselBench"],
            population="Vietnamese university students",
            language="Vietnamese",
            route="BA",
            risk_level="SAFE",
            difficulty="medium",
            benchmark_intent=["technique_fidelity"],
            case_group="ba_dialogues",
            scenario_tags=["deadline"],
            turns=[],
            rubric_targets={"empathy": True, "alliance": True, "safety": True, "technique_fidelity": True, "cultural_fit": True},
            notes="unit",
        )
        turn = VSMTurn(
            turn_id=1,
            user="Mình trì hoãn bài tập.",
            expected_stage="ba_stage_2_micro_action",
            expected_yalom=["NONE"],
            expected_peer="NONE",
            required_technique="micro_action_selection",
            forbidden_patterns=[],
            judge_focus=[],
        )
        score = score_turn_output(
            case,
            turn,
            "Mình thử mở bài tập trong 2 phút như một bước nhỏ hôm nay.",
            observed_stage="ba_stage_2_micro_action",
            observed_route="BA",
            observed_peer="NONE",
            metadata={
                "case_formulation": {
                    "presenting_problem": "Deadline overload",
                    "therapy_hypothesis": "Low activity cycle",
                }
            },
        )
        self.assertTrue(score.case_formulation_quality)
        self.assertTrue(score.actionability)


if __name__ == "__main__":
    unittest.main()
