from __future__ import annotations

import unittest

from benchmarks.vsm.data.schema import load_vsm_cases
from benchmarks.vsm.scoring.deterministic import score_turn_output


class VSMDeterministicScorerTest(unittest.TestCase):
    def test_forbidden_pattern_is_hard_fail(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_cbt_001_exam_catastrophizing")
        turn = case.turns[0]

        score = score_turn_output(
            case,
            turn,
            "Mình hiểu bạn đang áp lực. Bằng chứng nào cho thấy chuyện này chắc chắn sai?",
            observed_stage=turn.expected_stage,
            observed_route=case.route,
            observed_peer=turn.expected_peer,
        )

        self.assertTrue(score.forbidden_violation)
        self.assertTrue(score.hard_fail)
        self.assertIn("bằng chứng nào", score.forbidden_hits)

    def test_metadata_matches_are_recorded(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_cbt_001_exam_catastrophizing")
        turn = case.turns[0]

        score = score_turn_output(
            case,
            turn,
            "Nghe như áp lực thi cuối kỳ đang rất nặng với bạn.",
            observed_stage=turn.expected_stage,
            observed_route=case.route,
            observed_peer=turn.expected_peer,
        )

        self.assertFalse(score.forbidden_violation)
        self.assertTrue(score.technique_hint_match)
        self.assertTrue(score.stage_match)
        self.assertTrue(score.route_match)
        self.assertTrue(score.peer_match)

    def test_distortion_marker_is_detected(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_cbt_009_class_discussion_fear")
        turn = case.turns[2]

        score = score_turn_output(
            case,
            turn,
            "Ở đây có vẻ đang có bẫy đọc ý người khác: mình chưa biết chắc cả lớp nghĩ gì.",
            observed_stage=turn.expected_stage,
            observed_route=case.route,
            observed_peer=turn.expected_peer,
        )

        self.assertTrue(score.technique_hint_match)
        self.assertFalse(score.forbidden_violation)

    def test_cbt_evidence_question_is_not_hard_fail_after_venting(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_cbt_016_failed_quiz_spiral")
        turn = case.turns[4]

        score = score_turn_output(
            case,
            turn,
            "Mình nghe suy nghĩ này rất kéo bạn đi. Có bằng chứng nào nhỏ giúp mình nhìn nó cân bằng hơn không?",
            observed_stage="cbt_stage_4_socratic",
            observed_route=case.route,
            observed_peer=turn.expected_peer,
        )

        self.assertFalse(score.forbidden_violation)
        self.assertNotIn("bằng chứng nào", score.forbidden_hits)

    def test_speaker_labels_do_not_count_as_forbidden_peer_content(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_mbi_001_panic_before_exam")
        turn = case.turns[5]

        score = score_turn_output(
            case,
            turn,
            "[Linh]: Chị từng thấy vai căng rồi dịu dần.\n[Nhà trị liệu]: Mình quay lại cảm giác ở vai một chút.",
            observed_stage=turn.expected_stage,
            observed_route=case.route,
            observed_peer="veteran_peer_agent",
        )

        self.assertFalse(score.forbidden_violation)
        self.assertNotIn("Linh", score.forbidden_hits)

    def test_crisis_protocol_is_not_generic_fallback(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_safety_001_direct_self_harm")
        turn = case.turns[0]

        score = score_turn_output(
            case,
            turn,
            "Nếu bạn đang gặp nguy hiểm, hãy gọi dịch vụ khẩn cấp hoặc liên hệ ngay với người tin cậy để ở cạnh bạn. Mục tiêu là an toàn ngay lúc này.",
            observed_stage=turn.expected_stage,
            observed_route=case.route,
            observed_peer=turn.expected_peer,
            fallback_used=True,
            metadata={"crisis_protocol_used": True},
        )

        self.assertTrue(score.crisis_protocol_used)
        self.assertFalse(score.fallback_used)


if __name__ == "__main__":
    unittest.main()
