# -*- coding: utf-8 -*-
"""AI 補助機能の単体テスト。"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.core.ai_assistant import TaskAssistant


class TestTaskAssistant(unittest.TestCase):
    """TaskAssistant の主要機能を確認する。"""

    def setUp(self):
        self.assistant = TaskAssistant()

    def test_generate_meeting_report(self):
        """議事録から進捗レポートを生成できる。"""
        text = (
            "進捗として API 接続の実装が完了した。"
            "決定事項として OCR 保存形式は JSON を採用する。"
            "課題としてメール送信の設定確認が残っている。"
            "明日までに UI を修正する。"
        )
        report = self.assistant.generate_meeting_report(text)
        self.assertIn("進捗レポート", report)
        self.assertIn("決定事項", report)
        self.assertIn("次アクション", report)

    def test_detect_anomalies(self):
        """異常値検出で列サマリーを返せる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            dataframe = pd.DataFrame({"value": [10, 11, 12, 13, 200]})
            dataframe.to_csv(csv_path, index=False)

            result = self.assistant.detect_anomalies(str(csv_path))
            self.assertIn("異常値検出", result)
            self.assertIn("value", result)


if __name__ == "__main__":
    unittest.main()
