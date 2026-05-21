from __future__ import annotations

import unittest

from ai_engine.blackboard.cbt_contract import cbt_allowed_yalom, cbt_default_yalom, cbt_peer_allowed
from ai_engine.blackboard.cbt_milestones import CBTMilestoneState, detect_cbt_stage_with_milestones
from ai_engine.blackboard.cbt_evidence import CBTEvidence, extract_cbt_evidence_heuristic, sanitize_llm_cbt_evidence
from ai_engine.blackboard.cbt_evidence_normalizer import normalize_cbt_assessor_payload
from ai_engine.blackboard.orchestrator_output_normalizer import normalize_orchestrator_payload
from ai_engine.blackboard.cbt_response_validator import validate_cbt_therapist_response
from ai_engine.blackboard.stage_detector import detect_stage
from ai_engine.agents.clinical_assessor_node import CBTAssessorEvidenceDecision
from ai_engine.services.clinical_knowledge import cbt_stage_knowledge


GOLDEN_CASES = [
    # Stage 1
    ("Mình căng thẳng với thi cuối kỳ.", None, "cbt_stage_1_venting", ["Universality", "Catharsis"], "peer_mirror_agent"),
    ("Mình muốn bỏ cuộc, không biết có ai từng vực dậy nổi không.", None, "cbt_stage_1_venting", ["Hope"], "veteran_peer_agent"),
    ("Mình buồn và thấy chỉ có mình tệ như vậy.", None, "cbt_stage_1_venting", ["Universality", "Catharsis"], "peer_mirror_agent"),
    ("Mình rối quá, đầu óc không chịu nổi nữa.", None, "cbt_stage_1_venting", ["Universality", "Catharsis"], "peer_mirror_agent"),
    ("Mọi thứ đen tối quá, mình không thấy lối ra.", None, "cbt_stage_1_venting", ["Hope"], "veteran_peer_agent"),
    # Stage 2
    ("Hôm qua mình bị điểm 3.5, lúc nhìn kết quả mình hoảng.", "cbt_stage_1_venting", "cbt_stage_2_abc_model", ["NONE"], None),
    ("Bạn mình không trả lời tin nhắn, mình thấy hụt hẫng.", "cbt_stage_1_venting", "cbt_stage_2_abc_model", ["NONE"], None),
    ("Khi sếp nói vậy trước mọi người, mình thấy nghẹn lại.", "cbt_stage_1_venting", "cbt_stage_2_abc_model", ["NONE"], None),
    ("Lúc deadline tới gần, mình thấy tim đập nhanh và lo.", "cbt_stage_1_venting", "cbt_stage_2_abc_model", ["NONE"], None),
    ("Sau đó mình ngồi im rất lâu và thấy buồn.", "cbt_stage_1_venting", "cbt_stage_2_abc_model", ["NONE"], None),
    # Stage 3
    ("Nếu rớt môn này thì hỏng hết cả học kỳ.", "cbt_stage_2_abc_model", "cbt_stage_3_distortions", ["Universality"], "peer_mirror_agent"),
    ("Mình thất bại một lần là mình vô dụng.", "cbt_stage_2_abc_model", "cbt_stage_3_distortions", ["Universality"], "peer_mirror_agent"),
    ("Ai cũng sẽ nghĩ mình kém.", "cbt_stage_2_abc_model", "cbt_stage_3_distortions", ["Universality"], "peer_mirror_agent"),
    ("Chắc chắn mình sẽ không bao giờ khá lên được.", "cbt_stage_2_abc_model", "cbt_stage_3_distortions", ["Hope"], "veteran_peer_agent"),
    ("Mình là một đứa thất bại.", "cbt_stage_2_abc_model", "cbt_stage_3_distortions", ["Universality"], "peer_mirror_agent"),
    # Stage 4
    ("Có lẽ mình đang phóng đại.", "cbt_stage_3_distortions", "cbt_stage_4_socratic", ["NONE"], None),
    ("Mình biết suy nghĩ đó hơi cực đoan nhưng vẫn tin nó.", "cbt_stage_3_distortions", "cbt_stage_4_socratic", ["NONE"], None),
    ("Nghĩ lại thì điều đó không hoàn toàn đúng.", "cbt_stage_3_distortions", "cbt_stage_4_socratic", ["NONE"], None),
    ("Có lẽ mình đang lo quá mức.", "cbt_stage_3_distortions", "cbt_stage_4_socratic", ["NONE"], None),
    ("Mình thấy nó hơi quá, nhưng cảm giác vẫn mạnh.", "cbt_stage_3_distortions", "cbt_stage_4_socratic", ["NONE"], None),
    # Stage 5
    ("Rớt một môn không có nghĩa là hết cơ hội.", "cbt_stage_4_socratic", "cbt_stage_5_action", ["Hope", "Interpersonal Learning"], "veteran_peer_agent"),
    ("Mình vẫn còn cơ hội sửa lại từng phần.", "cbt_stage_4_socratic", "cbt_stage_5_action", ["Hope", "Interpersonal Learning"], "veteran_peer_agent"),
    ("Có thể mình sửa được nếu học lại từng chương nhỏ.", "cbt_stage_4_socratic", "cbt_stage_5_action", ["Hope", "Interpersonal Learning"], "veteran_peer_agent"),
    ("Nhìn cân bằng hơn thì chuyện này không phải là hết.", "cbt_stage_4_socratic", "cbt_stage_5_action", ["Hope", "Interpersonal Learning"], "veteran_peer_agent"),
    ("Mình có thể thử một bước nhỏ hôm nay.", "cbt_stage_4_socratic", "cbt_stage_5_action", ["Hope", "Interpersonal Learning"], "veteran_peer_agent"),
]


VALID_SPEECH = {
    "cbt_stage_1_venting": "Nghe vậy thì việc bạn thấy nặng nề là rất dễ hiểu. Phần nào đang đè lên bạn nhất lúc này?",
    "cbt_stage_2_abc_model": "Mình tách nhẹ ra nhé: sự kiện là điểm thi, còn suy nghĩ tự động là câu bạn tự nói với mình. Khoảnh khắc đó câu gì xuất hiện đầu tiên?",
    "cbt_stage_3_distortions": "Câu đó nghe giống bẫy thảm họa hóa, khi não biến một khả năng thành kết luận tuyệt đối. Bạn thấy nó có đang phóng đại hậu quả không?",
    "cbt_stage_4_socratic": "Có bằng chứng nào cho thấy kết luận đó đúng 100%, và có bằng chứng nào làm nó bớt tuyệt đối hơn?",
    "cbt_stage_5_action": "Một kết quả không như ý không có nghĩa là hết cơ hội. Một bước nhỏ hôm nay bạn có thể thử là gì?",
}


INVALID_SPEECH = {
    "cbt_stage_1_venting": "Có bằng chứng nào cho thấy suy nghĩ đó đúng 100% không?",
    "cbt_stage_2_abc_model": "Đây là bẫy thảm họa hóa rất rõ.",
    "cbt_stage_3_distortions": "Có bằng chứng nào cho thấy điều đó đúng 100% không?",
    "cbt_stage_4_socratic": "Hãy cho tôi biết thêm về những suy nghĩ và cảm xúc của bạn.",
    "cbt_stage_5_action": "Hãy kể thêm về lỗi tư duy này.",
}


class CBTStageContractTests(unittest.TestCase):
    def test_25_golden_stage_yalom_and_peer_policy_cases(self) -> None:
        for message, previous, expected_stage, expected_yalom, expected_peer in GOLDEN_CASES:
            with self.subTest(message=message):
                decision = detect_stage("CBT", previous, message)
                self.assertEqual(decision.current_stage, expected_stage)
                self.assertEqual(cbt_default_yalom(expected_stage, message), expected_yalom)
                self.assertTrue(set(expected_yalom).issubset(cbt_allowed_yalom(expected_stage)))
                self.assertEqual(cbt_peer_allowed(expected_stage, "peer_mirror_agent", expected_yalom), expected_peer == "peer_mirror_agent")
                self.assertEqual(cbt_peer_allowed(expected_stage, "veteran_peer_agent", expected_yalom), expected_peer == "veteran_peer_agent")

    def test_valid_therapist_speech_passes_each_stage(self) -> None:
        for stage, speech in VALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_cbt_therapist_response(stage, speech, "Nếu rớt môn này thì hỏng hết.")
                self.assertTrue(result.valid, result.reason)
                self.assertFalse(result.fallback_used)

    def test_invalid_therapist_speech_falls_back_each_stage(self) -> None:
        for stage, speech in INVALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_cbt_therapist_response(stage, speech, "Nếu rớt môn này thì hỏng hết.")
                self.assertFalse(result.valid)
                self.assertTrue(result.fallback_used)
                self.assertTrue(result.fallback_response)

    def test_therapist_knowledge_and_quality_scores_are_debuggable(self) -> None:
        knowledge = cbt_stage_knowledge("cbt_stage_3_distortions", "catastrophizing")
        self.assertIn("Stage task:", knowledge)
        self.assertIn("Micro-skills:", knowledge)
        self.assertIn("thảm họa hóa", knowledge)

        result = validate_cbt_therapist_response(
            "cbt_stage_3_distortions",
            "Câu 'hỏng hết học kỳ' nghe giống bẫy thảm họa hóa. Bạn thấy nhãn đó có khớp không?",
            "Nếu rớt môn này thì hỏng hết học kỳ.",
        )
        self.assertTrue(result.valid)
        self.assertIsInstance(result.quality_scores, dict)
        self.assertGreaterEqual(result.quality_scores.get("specificity", 0), 1)
        self.assertEqual(result.quality_scores.get("stage_fit"), 2)

    def test_hybrid_rubric_blocks_known_false_stage_jumps(self) -> None:
        self.assertNotEqual(
            detect_stage("CBT", None, "Mấy hôm nay mình đau đầu nhẹ và cứ lo mãi.").current_stage,
            "cbt_stage_5_action",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_1_venting", "Mình trả lời không tốt một câu, chắc mình đúng là kém cỏi.").current_stage,
            "cbt_stage_2_abc_model",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_1_venting", "Mình cứ nghĩ chắc tại mình học hành không tốt nên nhà mới căng thẳng như vậy.").current_stage,
            "cbt_stage_1_venting",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_2_abc_model", "Mình nghĩ chắc bạn ấy ghét mình rồi và không muốn chơi với mình nữa.").current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Mình không có bằng chứng chắc chắn là bạn ấy ghét mình.").current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Mình chưa có bằng chứng chắc chắn là họ né mình.").current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_1_venting", "Mình nghĩ nếu hôm nay không học được nhiều thì mình là đứa vô kỷ luật.").current_stage,
            "cbt_stage_2_abc_model",
        )
        self.assertEqual(
            detect_stage("CBT", None, "Mình muốn bỏ cuộc với luận văn rồi, không biết có ai từng kẹt như mình mà thoát ra được không.").current_stage,
            "cbt_stage_1_venting",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Có lẽ nói không bao giờ hoàn thành là quá tuyệt đối, nhưng mình vẫn rất đuối.").current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Có lẽ từ đau đầu nhẹ đến bệnh rất nặng là mình đang nhảy quá xa.").current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Có lẽ không xong tuần này không đồng nghĩa mọi thứ sụp đổ.").current_stage,
            "cbt_stage_5_action",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Mình biết một cuộc cãi nhau không chứng minh ai cũng sẽ rời đi.").current_stage,
            "cbt_stage_5_action",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_3_distortions", "Có lẽ một việc bị trì hoãn không nói hết con người mình.").current_stage,
            "cbt_stage_5_action",
        )
        self.assertNotEqual(
            detect_stage("CBT", "cbt_stage_1_venting", "Mình có thể luyện lại phần mở đầu 10 phút tối nay.").current_stage,
            "cbt_stage_5_action",
        )
        self.assertEqual(
            detect_stage("CBT", "cbt_stage_1_venting", "Trong cuộc họp mình nói sai một ý, giờ cứ nghĩ lại mãi.").current_stage,
            "cbt_stage_2_abc_model",
        )

    def test_cbt_session_core_stage_progression_does_not_skip_steps(self) -> None:
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_2_abc_model",
                "Nghe lại thì suy nghĩ 'nếu rớt môn này thì hỏng hết học kỳ' có vẻ rất cực đoan.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_3_distortions",
                "Mình biết vậy nhưng cảm giác vẫn tự động kéo mình đi.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_4_socratic",
                "Nếu là bạn mình gặp chuyện này, chắc mình sẽ không nói nặng như vậy.",
            ).current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_3_distortions",
                "Mình muốn thử một cách nói hoặc một bước nhỏ.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )

    def test_cbt_strict_milestones_do_not_advance_on_user_evidence_alone(self) -> None:
        milestones = CBTMilestoneState(strict_pacing=True)

        turn1 = detect_cbt_stage_with_milestones(
            None,
            "Mình đang rất căng thẳng vì thi cuối kỳ.",
            CBTEvidence(emotion_present=True, event_present=True),
            milestones,
        )
        self.assertEqual(turn1.current_stage, "cbt_stage_1_venting")

        turn2 = detect_cbt_stage_with_milestones(
            turn1.current_stage,
            "Nó làm mình thấy nặng ngực và muốn tránh hết.",
            CBTEvidence(emotion_present=True, event_present=True, abc_present=True),
            milestones,
        )
        self.assertEqual(turn2.current_stage, "cbt_stage_1_venting")

        turn3 = detect_cbt_stage_with_milestones(
            turn2.current_stage,
            "Nếu rớt môn này thì hỏng hết học kỳ.",
            CBTEvidence(event_present=True, automatic_thought_present=True, distortion_candidates=["catastrophizing"]),
            milestones,
        )
        self.assertEqual(turn3.current_stage, "cbt_stage_2_abc_model")

        turn4 = detect_cbt_stage_with_milestones(
            turn3.current_stage,
            "Sự kiện là lịch thi, cảm xúc là lo.",
            CBTEvidence(event_present=True, emotion_present=True, abc_present=True),
            milestones,
        )
        self.assertEqual(turn4.current_stage, "cbt_stage_2_abc_model")

        turn5 = detect_cbt_stage_with_milestones(
            turn4.current_stage,
            "Nghe lại thì suy nghĩ đó khá cực đoan.",
            CBTEvidence(distortion_reflection=True, insight_present=True, distortion_candidates=["catastrophizing"]),
            milestones,
        )
        self.assertEqual(turn5.current_stage, "cbt_stage_3_distortions")

    def test_cbt_strict_stage_four_requires_socratic_or_reframe_before_action(self) -> None:
        milestones = CBTMilestoneState(
            distortion_named=True,
            strict_pacing=True,
            last_stage="cbt_stage_3_distortions",
            stage_visit_counts={
                "cbt_stage_1_venting": 2,
                "cbt_stage_2_abc_model": 2,
                "cbt_stage_3_distortions": 1,
                "cbt_stage_4_socratic": 0,
                "cbt_stage_5_action": 0,
            },
        )
        decision = detect_cbt_stage_with_milestones(
            "cbt_stage_3_distortions",
            "Mình muốn thử một bước nhỏ.",
            CBTEvidence(action_step=True, action_commitment=False),
            milestones,
        )
        self.assertEqual(decision.current_stage, "cbt_stage_3_distortions")

    def test_cbt_milestone_detector_generalizes_across_paraphrases(self) -> None:
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_2_abc_model",
                "Trong đầu mình kết luận rằng một điểm thấp sẽ phá hỏng cả học kỳ.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_2_abc_model",
                "Mình nhận ra kết luận đó tuyệt đối hơn dữ kiện mình đang có.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_3_distortions",
                "Mình nhận ra kết luận đó tuyệt đối hơn dữ kiện mình đang có.",
            ).current_stage,
            "cbt_stage_4_socratic",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_3_distortions",
                "Mình sẽ học 15 phút tối nay.",
            ).current_stage,
            "cbt_stage_3_distortions",
        )
        self.assertEqual(
            detect_stage(
                "CBT",
                "cbt_stage_4_socratic",
                "Mình sẽ học 15 phút tối nay.",
            ).current_stage,
            "cbt_stage_5_action",
        )

    def test_cbt_evidence_extracts_semantic_peer_boundary(self) -> None:
        evidence = extract_cbt_evidence_heuristic(
            "Mình muốn phần chia sẻ nhóm dừng lại để tập trung với nhà trị liệu."
        )

        self.assertTrue(evidence.peer_boundary_intent)

    def test_cbt_assessor_normalizer_accepts_deepseek_schema_drift(self) -> None:
        raw = {
            "clinical_summary": "User feels guilty after being slow on a group task.",
            "safety_flags": [],
            "cbt_evidence": {
                "emotion_present": "thấy tội lỗi",
                "event_present": "mình làm phần bài nhóm chậm",
                "automatic_thought": "",
                "automatic_thought_present": "",
                "distortion_candidates": "personalization",
                "distortion_reflection": "",
                "socratic_reasoning": "",
                "insight_present": False,
                "balanced_reframe": "",
                "action_step": "",
                "action_commitment": "",
                "peer_boundary_intent": "",
                "overload": False,
                "hope_request": False,
                "confidence": "0.72",
                "evidence_quotes": {
                    "emotion": "thấy tội lỗi",
                    "event": "làm phần bài nhóm chậm",
                },
            },
        }

        decision = CBTAssessorEvidenceDecision.model_validate(normalize_cbt_assessor_payload(raw))

        self.assertEqual(decision.safety_flags, {})
        self.assertTrue(decision.cbt_evidence.emotion_present)
        self.assertTrue(decision.cbt_evidence.event_present)
        self.assertFalse(decision.cbt_evidence.balanced_reframe)
        self.assertFalse(decision.cbt_evidence.action_step)
        self.assertFalse(decision.cbt_evidence.peer_boundary_intent)
        self.assertEqual(decision.cbt_evidence.distortion_candidates, ["personalization"])
        self.assertEqual(decision.cbt_evidence.evidence_quotes, ["thấy tội lỗi", "làm phần bài nhóm chậm"])
        self.assertEqual(decision.cbt_evidence.confidence, 0.72)

    def test_llm_cbt_evidence_sanitizer_blocks_inferred_distortion_without_thought(self) -> None:
        evidence = CBTEvidence(
            emotion_present=True,
            event_present=True,
            automatic_thought="",
            distortion_candidates=["personalization"],
            evidence_quotes=["có thể suy diễn rằng mình không quan trọng"],
            source="llm",
        )
        sanitized = sanitize_llm_cbt_evidence(evidence, "Bạn mình không trả lời tin nhắn, mình thấy hụt hẫng.")
        decision = detect_stage("CBT", "cbt_stage_1_venting", "Bạn mình không trả lời tin nhắn, mình thấy hụt hẫng.", cbt_evidence=sanitized)
        self.assertEqual(sanitized.distortion_candidates, [])
        self.assertEqual(decision.current_stage, "cbt_stage_2_abc_model")

    def test_llm_cbt_evidence_sanitizer_keeps_hopelessness_in_venting(self) -> None:
        evidence = CBTEvidence(
            emotion_present=True,
            event_present=False,
            automatic_thought="Mình muốn bỏ cuộc",
            distortion_candidates=["catastrophizing"],
            hope_request=True,
            evidence_quotes=["Mình muốn bỏ cuộc"],
            source="llm",
        )
        sanitized = sanitize_llm_cbt_evidence(evidence, "Mình muốn bỏ cuộc, không biết có ai từng rơi vào chỗ này mà vực dậy được không.")
        decision = detect_stage("CBT", None, "Mình muốn bỏ cuộc, không biết có ai từng rơi vào chỗ này mà vực dậy được không.", cbt_evidence=sanitized)
        self.assertEqual(sanitized.automatic_thought, "")
        self.assertEqual(sanitized.distortion_candidates, [])
        self.assertEqual(decision.current_stage, "cbt_stage_1_venting")

    def test_orchestrator_normalizer_accepts_null_cognitive_distortion(self) -> None:
        normalized = normalize_orchestrator_payload(
            {
                "clinical_reasoning_scratchpad": "ok",
                "cognitive_distortion": None,
                "draft_decisions": [{"sender": "peer_mirror_agent", "action": None}],
                "doctor_speech": "Nghe như bạn đang rất áp lực.",
            }
        )
        self.assertEqual(normalized["cognitive_distortion"], "None")
        self.assertEqual(normalized["draft_decisions"][0]["action"], "discard")


if __name__ == "__main__":
    unittest.main()
