from __future__ import annotations

import unittest

from ai_engine.agents.personas.blackboard_peer import (
    contribution_update,
    no_contribution,
    parse_peer_contribution,
)
from ai_engine.agents.orchestrator_node import (
    _doctor_speech_misses_stage_goal,
    _stage_specific_therapist_message,
    _therapist_bridge_fallback,
    _too_similar,
)
from ai_engine.agents.clinical_assessor_node import _cbt_history_sensitive_yalom, _cbt_state_sensitive_yalom
from ai_engine.blackboard.cbt_evidence import CBTEvidence
from ai_engine.blackboard.stage_detector import (
    allowed_yalom_factors_for_stage,
    detect_stage,
    yalom_factors_for_stage,
)
from ai_engine.services.prompt_renderer import render_template
from ai_engine.services.protocol_loader import load_protocol
from ai_engine.services.safety import clean_toxic_advice, is_crisis_input, is_unsafe_output
from ai_engine.agents.guardrails_node import _next_peer_state
from api.services.sse import graph_update_payload


class BlackboardRefactorTests(unittest.TestCase):
    def test_prompt_renderer_replaces_braced_variables(self) -> None:
        self.assertEqual(render_template("Xin chào {name}", name="Nam"), "Xin chào Nam")

    def test_protocol_loader_returns_department_and_goals(self) -> None:
        protocol = load_protocol("CBT")
        self.assertEqual(protocol["department"], "CBT")
        self.assertIsInstance(protocol["goals"], str)

    def test_safety_detects_crisis_and_unsafe_output(self) -> None:
        self.assertTrue(is_crisis_input("tôi muốn tự tử"))
        self.assertTrue(is_unsafe_output("bạn mắc bệnh này rồi"))
        self.assertIn("bạn nghĩ sao nếu", clean_toxic_advice("bạn nên nghỉ một chút"))

    def test_peer_json_fallback_records_no_contribution(self) -> None:
        contribution = parse_peer_contribution("not-json", sender="Peer Mirror")
        update = contribution_update(
            sender="peer_mirror_agent",
            contribution=contribution,
            default_type="peer_reflection",
            default_factor="Universality",
        )
        decision = update["peer_contribution_decisions"][0]
        self.assertEqual(decision["decision"], "NO_CONTRIBUTION")
        self.assertTrue(decision["safety_risk"])

    def test_no_contribution_schema_is_stable(self) -> None:
        update = no_contribution(sender="veteran_peer_agent", reason="not needed")
        decision = update["peer_contribution_decisions"][0]
        self.assertEqual(decision["sender"], "veteran_peer_agent")
        self.assertEqual(decision["decision"], "NO_CONTRIBUTION")

    def test_sse_payload_keeps_peer_debug_contract(self) -> None:
        payload = graph_update_payload(
            {
                "Blackboard_Peer_Nam": {
                    "peer_drafts": [{"sender": "peer_mirror_agent"}],
                    "peer_contribution_decisions": [{"decision": "CONTRIBUTE"}],
                }
            }
        )
        self.assertEqual(payload["node"], "Blackboard_Peer_Nam")
        self.assertEqual(payload["peer_contribution_decisions"][0]["decision"], "CONTRIBUTE")

    def test_orchestrator_detects_duplicate_peer_and_therapist_text(self) -> None:
        peer_text = "Áp lực thi cuối kỳ thật sự có thể rất căng thẳng."
        doctor_text = "Áp lực thi cuối kỳ thật sự có thể rất căng thẳng. Hãy cho tôi biết thêm."
        self.assertTrue(_too_similar(peer_text, doctor_text))

    def test_cbt_stage_detector_advances_with_evidence(self) -> None:
        stage1 = detect_stage("CBT", None, "Mình đang rất căng thẳng với áp lực thi cuối kỳ.")
        self.assertEqual(stage1.current_stage, "cbt_stage_1_venting")
        stage3 = detect_stage("CBT", "cbt_stage_2_abc_model", "Nếu thi rớt môn này thì coi như hỏng hết cả học kỳ.")
        self.assertEqual(stage3.current_stage, "cbt_stage_3_distortions")
        stage4 = detect_stage("CBT", "cbt_stage_3_distortions", "Mình nghĩ lại thì thấy có lẽ mình đang phóng đại.")
        self.assertEqual(stage4.current_stage, "cbt_stage_4_socratic")
        self.assertEqual(yalom_factors_for_stage("CBT", stage4.current_stage), ["NONE"])
        self.assertEqual(allowed_yalom_factors_for_stage("CBT", stage4.current_stage), {"NONE"})

    def test_cbt_hopelessness_triggers_linh_hope_not_nam_universality(self) -> None:
        message = "Mình muốn bỏ cuộc. Không biết có ai từng rơi vào hoàn cảnh bi đát thế này mà vực dậy nổi không nữa. Mọi thứ đen tối quá."
        stage = detect_stage("CBT", None, message)
        self.assertEqual(stage.current_stage, "cbt_stage_1_venting")
        self.assertIn("Hope", allowed_yalom_factors_for_stage("CBT", stage.current_stage))
        self.assertEqual(yalom_factors_for_stage("CBT", stage.current_stage, message), ["Hope"])

    def test_mbi_stage_detector_keeps_grounding_and_decentering(self) -> None:
        grounding = detect_stage("MBI", None, "Mình thở gấp, tim đập nhanh và rất hoảng.")
        self.assertEqual(grounding.current_stage, "mbi_stage_1_grounding")
        decentering = detect_stage("MBI", "mbi_stage_1_grounding", "Mình đỡ hơn nhưng suy nghĩ vẫn chạy.")
        self.assertEqual(decentering.current_stage, "mbi_stage_2_decentering")
        self.assertEqual(yalom_factors_for_stage("MBI", decentering.current_stage), ["NONE"])

    def test_ba_stage_detector_tracks_action_flow(self) -> None:
        energy = detect_stage("BA", None, "Mình nằm lì cả ngày, thấy mình lười quá.")
        self.assertEqual(energy.current_stage, "ba_stage_1_energy_check")
        micro = detect_stage("BA", "ba_stage_1_energy_check", "Pin mình 2/10.")
        self.assertEqual(micro.current_stage, "ba_stage_2_micro_action")
        schedule = detect_stage("BA", "ba_stage_2_micro_action", "Mình chọn uống nước.")
        self.assertEqual(schedule.current_stage, "ba_stage_3_barrier_schedule")
        reward = detect_stage("BA", "ba_stage_3_barrier_schedule", "Xong rồi.")
        self.assertEqual(reward.current_stage, "ba_stage_4_momentum_reward")

    def test_cbt_stage_specific_fallback_blocks_generic_therapist_questions(self) -> None:
        state = {
            "current_stage": "cbt_stage_4_socratic",
            "user_message": "Mình nghĩ lại thì thấy có lẽ mình đang phóng đại.",
        }
        generic = "Hãy cho tôi biết thêm về những suy nghĩ và cảm xúc của bạn."
        self.assertTrue(_doctor_speech_misses_stage_goal(state, generic))
        fallback = _stage_specific_therapist_message(state)
        self.assertIn("bằng chứng", fallback.lower())

    def test_cbt_peer_gating_silences_socratic_and_peer_boundary_requests(self) -> None:
        self.assertEqual(
            _cbt_history_sensitive_yalom(
                "cbt_stage_4_socratic",
                "Có lẽ mình đang phóng đại, nhưng mình chưa chắc phần nào là thật.",
                "",
                ["Universality"],
            ),
            ["NONE"],
        )
        self.assertEqual(
            _cbt_history_sensitive_yalom(
                "cbt_stage_2_abc_model",
                "Nếu peer nói quá nhiều thì mình sẽ bị loãng.",
                "",
                ["Catharsis"],
            ),
            ["NONE"],
        )

    def test_cbt_stage_five_linh_cooldown_uses_peer_metadata_only(self) -> None:
        self.assertEqual(
            _cbt_state_sensitive_yalom(
                "cbt_stage_5_action",
                "Mình có thể thử một bước nhỏ trong hôm nay.",
                ["Hope", "Interpersonal Learning"],
                evidence=CBTEvidence(action_commitment=True),
                peer_state={"last_peer_sender": "veteran_peer_agent", "consecutive_peer_turns": 1},
            ),
            ["NONE"],
        )
        self.assertEqual(
            _cbt_state_sensitive_yalom(
                "cbt_stage_5_action",
                "Mình thử viết lại suy nghĩ thì thấy nhẹ hơn một chút.",
                ["Hope", "Interpersonal Learning"],
                evidence=CBTEvidence(action_commitment=True),
                peer_state={"last_peer_sender": "therapist_coordinator_agent", "consecutive_peer_turns": 0},
            ),
            ["Hope", "Interpersonal Learning"],
        )

    def test_therapist_bridge_fallback_does_not_name_absent_peer_pair(self) -> None:
        fallback = _therapist_bridge_fallback(
            {"current_stage": "cbt_stage_2_abc_model", "user_message": "Mình thấy áp lực."},
            included_peer_count=1,
        )
        self.assertNotIn("Nam/Linh", fallback)
        self.assertIn("bạn đồng hành", fallback)

    def test_guardrails_tracks_peer_cooldown_from_visible_output_metadata(self) -> None:
        state = {"last_peer_sender": "veteran_peer_agent", "consecutive_peer_turns": 1, "peer_silence_cooldown": 1}
        self.assertEqual(
            _next_peer_state(state, [{"sender": "Chị Linh", "text": "Một chia sẻ ngắn."}]),
            {"last_peer_sender": "veteran_peer_agent", "consecutive_peer_turns": 2, "peer_silence_cooldown": 1},
        )
        self.assertEqual(
            _next_peer_state(state, [{"sender": "Nhà trị liệu", "text": "Mình quay lại trọng tâm nhé."}]),
            {"last_peer_sender": "veteran_peer_agent", "consecutive_peer_turns": 0, "peer_silence_cooldown": 0},
        )


if __name__ == "__main__":
    unittest.main()
