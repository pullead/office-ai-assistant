# -*- coding: utf-8 -*-
"""LLMClient の診断機能テスト。"""

import unittest
from unittest.mock import Mock, patch

from src.core.llm_client import LLMClient


class TestLLMClient(unittest.TestCase):
    """接続診断まわりを確認する。"""

    def setUp(self):
        self.client = LLMClient()

    def test_normalize_chat_completions_url(self):
        """ルート URL から chat/completions を補完できる。"""
        self.assertEqual(
            self.client._normalize_chat_completions_url("https://api.siliconflow.com/v1"),
            "https://api.siliconflow.com/v1/chat/completions",
        )
        self.assertEqual(
            self.client._normalize_chat_completions_url("https://api.minimax.chat/v1/text/chatcompletion_v2"),
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
        )

    def test_diagnose_connection_without_key(self):
        """API Key 未入力ならローカル診断で止まる。"""
        result = self.client.diagnose_connection(
            provider="siliconflow",
            base_url="https://api.siliconflow.com/v1",
            model="Qwen/Qwen2.5-7B-Instruct",
            api_key="",
            timeout=15,
        )
        self.assertFalse(result["success"])
        self.assertTrue(any(item["name"] == "API Key" and item["status"] == "error" for item in result["items"]))

    @patch("src.core.llm_client.requests.post")
    @patch("src.core.llm_client.requests.get")
    def test_diagnose_connection_success(self, mock_get, mock_post):
        """モデル一覧取得と推論テスト成功を扱える。"""
        get_response = Mock()
        get_response.raise_for_status.return_value = None
        get_response.json.return_value = {
            "data": [
                {"id": "Qwen/Qwen2.5-7B-Instruct"},
                {"id": "tencent/Hunyuan-MT-7B"},
            ]
        }
        mock_get.return_value = get_response

        post_response = Mock()
        post_response.raise_for_status.return_value = None
        post_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "OK",
                    }
                }
            ]
        }
        mock_post.return_value = post_response

        result = self.client.diagnose_connection(
            provider="siliconflow",
            base_url="https://api.siliconflow.com/v1",
            model="Qwen/Qwen2.5-7B-Instruct",
            api_key="sk-test-1234567890",
            timeout=15,
        )
        self.assertTrue(result["success"])
        self.assertIn("OK", result["preview"])
        self.assertIn("Qwen/Qwen2.5-7B-Instruct", result["available_models"])


if __name__ == "__main__":
    unittest.main()
