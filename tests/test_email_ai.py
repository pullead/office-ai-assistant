# -*- coding: utf-8 -*-
"""AI メールアシスタントの単体テスト。"""

import unittest

from src.core.email_ai_assistant import EmailAIAssistant


class TestEmailAIAssistant(unittest.TestCase):
    """メール解析と返信草案生成を確認する。"""

    def setUp(self):
        self.assistant = EmailAIAssistant()

    def test_parse_email_text(self):
        """貼り付けメールから主要項目を抽出できる。"""
        raw_text = (
            "Subject: お打ち合わせ日程の確認\n"
            "From: sample@example.com\n"
            "To: team@example.co.jp\n"
            "\n"
            "来週の打ち合わせ候補日をご確認ください。\n"
            "ご都合の良い日時をご連絡いただけますと幸いです。"
        )
        parsed = self.assistant.parse_email_text(raw_text)
        self.assertEqual(parsed["subject"], "お打ち合わせ日程の確認")
        self.assertIn("sample@example.com", parsed["sender"])
        self.assertIn("ご連絡", parsed["action_items"])

    def test_build_local_reply(self):
        """ローカル返信草案を生成できる。"""
        parsed = {
            "subject": "資料送付のお願い",
            "sender": "営業部",
            "recipient": "support@example.com",
            "body": "資料の送付をお願いします。",
            "keywords": "資料 / 送付",
            "action_items": "資料の送付をお願いします。",
            "tone": "丁寧",
        }
        reply = self.assistant.build_local_reply(parsed, "reply", "formal", "")
        self.assertIn("Re:", reply["subject"])
        self.assertIn("ご連絡ありがとうございます", reply["body"])


if __name__ == "__main__":
    unittest.main()
