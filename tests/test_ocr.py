# -*- coding: utf-8 -*-
"""
OCR モジュールの単体テスト。
モックを使って請求書情報の抽出ロジックを確認する。
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.ocr_engine import InvoiceRecognizer


class TestOCR(unittest.TestCase):
    """OCR エンジンのテスト。"""

    @classmethod
    def setUpClass(cls):
        cls.ocr = InvoiceRecognizer(lang="jpn+eng")
        cls.sample_image = Path(__file__).parent.parent / "samples" / "invoice_sample.jpg"
        cls.has_sample = cls.sample_image.exists()

    def test_image_to_text_with_sample(self):
        """サンプル画像が存在する場合のみ OCR を確認する。"""
        if not self.has_sample:
            self.skipTest("サンプル画像がありません。samples/invoice_sample.jpg を配置してください。")

        text = self.ocr.image_to_text(str(self.sample_image))
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertTrue(
            any(character.isdigit() or ord(character) > 0x3000 for character in text),
            "OCR 結果に数字または日本語が含まれているはずです。",
        )

    def test_invoice_extraction_with_mock(self):
        """モックテキストから請求書情報を抽出できることを確認する。"""
        dummy_text = """請求書サンプル
請求書番号: INV-2025-00123
発行日: 2025年3月5日
金額: 54,800 円
会社名: テスト株式会社
ありがとうございます。"""

        with patch.object(self.ocr, "image_to_text", return_value=dummy_text):
            info = self.ocr.extract_invoice_info("dummy.jpg")
            self.assertEqual(info["invoice_no"], "INV-2025-00123")
            self.assertEqual(info["amount"], "54,800")
            self.assertEqual(info["date"], "2025年3月5日")
            self.assertEqual(info["seller"], "テスト株式会社")
            self.assertIn("請求書番号", info["full_text"])

    def test_invoice_extraction_edge_cases(self):
        """英語や別表記でも抽出できるかを確認する。"""
        test_cases = [
            (
                "Invoice No.: ABC123\nTotal: $1,234.56\nDate: 2024-12-01\nSeller: XYZ Corp",
                "ABC123",
                "1,234.56",
                "2024-12-01",
                "XYZ Corp",
            ),
            (
                "請求番号 987654\n金額 3,200 円\n日付 2023/01/15\n会社名 サンプル商事",
                "987654",
                "3,200",
                "2023/01/15",
                "サンプル商事",
            ),
            (
                "No. INV-999\nAmount 7,500 JPY\nIssued 2022-10-20\nCompany: A&B Co.",
                "INV-999",
                "7,500",
                "2022-10-20",
                "A&B Co.",
            ),
        ]

        for text, expected_no, expected_amount, expected_date, expected_seller in test_cases:
            with patch.object(self.ocr, "image_to_text", return_value=text):
                info = self.ocr.extract_invoice_info("dummy.jpg")
                self.assertEqual(info["invoice_no"], expected_no)
                self.assertEqual(info["amount"], expected_amount)
                self.assertEqual(info["date"], expected_date)
                self.assertEqual(info["seller"], expected_seller)

    def test_invoice_extraction_missing_fields(self):
        """項目が存在しない場合は None を返す。"""
        text = "この文章には請求書情報が含まれていません。"
        with patch.object(self.ocr, "image_to_text", return_value=text):
            info = self.ocr.extract_invoice_info("dummy.jpg")
            self.assertIsNone(info["invoice_no"])
            self.assertIsNone(info["amount"])
            self.assertIsNone(info["date"])
            self.assertIsNone(info["seller"])
            self.assertEqual(info["full_text"], text)


if __name__ == "__main__":
    unittest.main()
