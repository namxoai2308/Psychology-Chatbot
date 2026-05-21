from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.vsm.adapters.remote_chatbots import (
    RemoteChatbotUnavailable,
    build_remote_prompt,
    call_remote_chatbot,
)


class VSMRemoteChatbotTests(unittest.TestCase):
    def test_kaggle_notebooks_are_valid_json_and_standalone(self) -> None:
        for path in (
            Path("backend/ai_engine/agents/mindchat_kaggle.ipynb"),
            Path("backend/ai_engine/agents/soulchat_kaggle.ipynb"),
            Path("backend/ai_engine/agents/seallm_kaggle.ipynb"),
            Path("backend/ai_engine/agents/camel_kaggle.ipynb"),
        ):
            with self.subTest(path=str(path)):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                text = json.dumps(notebook, ensure_ascii=False)
                self.assertIn("/v1/generate", text)
                self.assertIn("/health", text)
                self.assertNotIn("ai_engine", text)
                self.assertNotIn("hospital_graph", text)
                self.assertNotIn("blackboard", text)
                self.assertNotIn("DEEPSEEK_API_KEY", text)

    def test_mindchat_notebook_has_kaggle_safe_fallbacks(self) -> None:
        path = Path("backend/ai_engine/agents/mindchat_kaggle.ipynb")
        notebook = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(notebook, ensure_ascii=False)

        self.assertIn("get_secret_or_env", text)
        self.assertIn("UserSecretsClient", text)
        self.assertIn("parse_benchmark_prompt", text)
        self.assertIn("hasattr(model, \\\"chat\\\")", text)
        self.assertIn("LlamaTokenizer", text)
        self.assertIn("load_mindchat_tokenizer", text)
        self.assertIn("AutoModelForCausalLM", text)
        self.assertIn("AutoModel fp16", text)
        self.assertIn("MINDCHAT_VISIBLE_DEVICES", text)
        self.assertIn("build_max_memory_map", text)
        self.assertIn("gpu_count", text)
        self.assertIn("hf_device_map", text)
        self.assertIn("HF_HUB_DISABLE_XET", text)
        self.assertIn("transformers==4.30.2", text)

    def test_new_kaggle_baseline_notebooks_are_benchmark_compatible(self) -> None:
        notebooks = {
            "seallm": (
                Path("backend/ai_engine/agents/seallm_kaggle.ipynb"),
                "SeaLLMs/SeaLLMs-v3-7B-Chat",
                "SEALLM_NGROK_URL",
            ),
            "camel_cbt": (
                Path("backend/ai_engine/agents/camel_kaggle.ipynb"),
                "cactus-camel/camel-llama3",
                "CAMEL_NGROK_URL",
            ),
        }
        for system_name, (path, model_name, env_name) in notebooks.items():
            with self.subTest(system=system_name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                text = json.dumps(notebook, ensure_ascii=False)
                self.assertIn(model_name, text)
                self.assertIn(env_name, text)
                self.assertIn("/v1/generate", text)
                self.assertIn("/health", text)
                self.assertIn("MINDCHAT_VISIBLE_DEVICES".replace("MINDCHAT", env_name.split("_")[0]), text)
                self.assertIn("build_max_memory_map", text)
                self.assertIn("hf_device_map", text)
                self.assertIn("NGROK_AUTH_TOKEN", text)

    def test_mindchat_notebook_does_not_hardcode_ngrok_token(self) -> None:
        path = Path("backend/ai_engine/agents/mindchat_kaggle.ipynb")
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

        self.assertIn('NGROK_AUTH_TOKEN = get_secret_or_env("NGROK_AUTH_TOKEN")', source)
        self.assertIsNone(re.search(r"NGROK_AUTH_TOKEN\\s*=\\s*[A-Za-z0-9_\\-]{20,}", source))

    def test_remote_prompt_is_plain_baseline_prompt(self) -> None:
        prompt = build_remote_prompt("User: cũ\nAssistant: trả lời", "Mình rất mệt.", "MindChat")
        self.assertIn("Lịch sử:", prompt)
        self.assertIn("User: Mình rất mệt.", prompt)
        self.assertIn("MindChat:", prompt)
        self.assertNotIn("DASS21_SUBMIT", prompt)
        self.assertNotIn("blackboard", prompt.lower())

    def test_remote_chatbot_requires_ngrok_url(self) -> None:
        with patch.dict("os.environ", {"MINDCHAT_NGROK_URL": ""}, clear=False):
            with self.assertRaises(RemoteChatbotUnavailable):
                call_remote_chatbot("mindchat", "", "hello")

    def test_remote_chatbot_calls_ngrok_endpoint_only(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"text": "remote reply"}

        with patch.dict("os.environ", {"SOULCHAT_NGROK_URL": "https://abc.ngrok-free.app"}, clear=False):
            with patch("benchmarks.vsm.adapters.remote_chatbots.requests.post", return_value=FakeResponse()) as post:
                result = call_remote_chatbot("soulchat", "history", "xin chào")
                self.assertEqual(result, "remote reply")
                url = post.call_args.args[0]
                self.assertEqual(url, "https://abc.ngrok-free.app/v1/generate")

    def test_new_remote_chatbot_configs_use_own_env_vars(self) -> None:
        from benchmarks.vsm.adapters.remote_chatbots import REMOTE_CHATBOTS

        self.assertEqual(REMOTE_CHATBOTS["seallm"].env_var, "SEALLM_NGROK_URL")
        self.assertEqual(REMOTE_CHATBOTS["seallm"].prompt_label, "SeaLLM")
        self.assertEqual(REMOTE_CHATBOTS["camel_cbt"].env_var, "CAMEL_NGROK_URL")
        self.assertEqual(REMOTE_CHATBOTS["camel_cbt"].prompt_label, "CAMEL")


if __name__ == "__main__":
    unittest.main()
