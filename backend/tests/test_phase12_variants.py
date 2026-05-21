from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from ai_engine.graph.builder import build_graph
from ai_engine.graph.nodes import crisis_node, single_agent_plain_node
from ai_engine.graph.variants import SystemVariant, normalize_system_variant, variant_flags
from api.schemas.chat import ChatRequest
from api.services.chat_service import chat_service
from api.services.sse import graph_update_payload


class Phase12VariantTests(unittest.TestCase):
    def test_chat_request_accepts_new_defaults(self) -> None:
        req = ChatRequest(user_message="xin chào")
        self.assertEqual(req.user_id, "default_user")
        self.assertEqual(req.system_variant, SystemVariant.OURS_FULL)

    def test_unknown_variant_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(user_message="xin chào", system_variant="unknown_variant")

        with self.assertRaises(ValueError):
            normalize_system_variant("unknown_variant")

    def test_variant_flags_are_explicit(self) -> None:
        no_peer = variant_flags(SystemVariant.OURS_NO_PEER)
        self.assertFalse(no_peer["peer_enabled"])
        self.assertTrue(no_peer["validator_enabled"])
        self.assertTrue(no_peer["safety_critic_enabled"])

        no_validator = variant_flags(SystemVariant.OURS_NO_VALIDATOR)
        self.assertTrue(no_validator["peer_enabled"])
        self.assertFalse(no_validator["validator_enabled"])

        no_safety_critic = variant_flags(SystemVariant.OURS_NO_SAFETY_CRITIC)
        self.assertTrue(no_safety_critic["peer_enabled"])
        self.assertFalse(no_safety_critic["safety_critic_enabled"])

        single_plain = variant_flags(SystemVariant.SINGLE_AGENT_PLAIN)
        self.assertFalse(single_plain["peer_enabled"])
        self.assertFalse(single_plain["validator_enabled"])

    def test_graph_builder_compiles_all_variants(self) -> None:
        for variant in SystemVariant:
            with self.subTest(variant=variant.value):
                app = build_graph(variant).compile()
                self.assertIsNotNone(app)

    def test_chat_service_build_input_state_carries_user_and_variant(self) -> None:
        req = ChatRequest(
            user_message="mình thấy áp lực",
            user_id="student-a",
            user_name="An",
            selected_model="groq",
            system_variant=SystemVariant.OURS_NO_PEER,
        )
        state = chat_service.build_input_state(req)
        self.assertEqual(state["user_id"], "student-a")
        self.assertEqual(state["user_name"], "An")
        self.assertEqual(state["selected_model"], "groq")
        self.assertEqual(state["system_variant"], "ours_no_peer")
        self.assertFalse(state["peer_enabled"])

    def test_save_metadata_uses_request_user_id(self) -> None:
        with patch("api.services.chat_service.save_or_update_conversation") as mocked:
            chat_service.save_metadata(
                thread_id="thread-1",
                user_id="student-a",
                user_message="mình thấy rất áp lực với kỳ thi cuối kỳ",
            )

        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["thread_id"], "thread-1")
        self.assertEqual(mocked.call_args.kwargs["user_id"], "student-a")

    def test_sse_emits_onboarding_final_reply(self) -> None:
        payload = graph_update_payload(
            {
                "Onboarding": {
                    "ui_action": "SHOW_DASS21",
                    "final_reply": "Form DASS-21 cần 21 lựa chọn hợp lệ. Vui lòng thử lại.",
                }
            }
        )
        self.assertEqual(payload["node"], "Onboarding")
        self.assertEqual(payload["ui_action"], "SHOW_DASS21")
        self.assertEqual(
            payload["final_output"][0]["text"],
            "Form DASS-21 cần 21 lựa chọn hợp lệ. Vui lòng thử lại.",
        )

    def test_sse_done_merges_metadata(self) -> None:
        payload = graph_update_payload(
            {
                "__done__": True,
                "__metadata__": {
                    "system_variant": "ours_no_peer",
                    "route": "CBT",
                    "stage": "cbt_stage_1_venting",
                    "peer_used": False,
                    "fallback_used": False,
                    "latency_ms": 12.5,
                },
            }
        )
        self.assertTrue(payload["done"])
        self.assertEqual(payload["system_variant"], "ours_no_peer")
        self.assertEqual(payload["route"], "CBT")

    def test_crisis_node_bypasses_peer_for_variant(self) -> None:
        output = asyncio.run(
            crisis_node(
                {
                    "user_message": "tôi muốn tự tử",
                    "system_variant": "ours_no_peer",
                    "validator_enabled": True,
                    "safety_critic_enabled": True,
                }
            )
        )
        self.assertEqual(output["system_variant"], "ours_no_peer")
        self.assertFalse(output["peer_used"])
        self.assertEqual(output["peer_drafts"], "CLEAR")
        self.assertEqual(output["therapy_route"], "CRISIS")

    def test_single_agent_plain_returns_shared_schema_without_peer(self) -> None:
        async def fake_generate_text_async(*args, **kwargs) -> str:
            return "Mình nghe thấy áp lực của bạn. Điều nặng nhất lúc này là gì?"

        state = {
            "user_message": "mình rất áp lực",
            "chat_history": "",
            "selected_model": "gemini",
            **variant_flags(SystemVariant.SINGLE_AGENT_PLAIN),
        }

        with patch("ai_engine.graph.nodes.generate_text_async", fake_generate_text_async):
            output = asyncio.run(single_agent_plain_node(state))

        self.assertEqual(output["system_variant"], "single_agent_plain")
        self.assertFalse(output["peer_used"])
        self.assertFalse(output["validator_enabled"])
        self.assertEqual(output["peer_drafts"], "CLEAR")
        self.assertIn("final_output", output)


if __name__ == "__main__":
    unittest.main()
