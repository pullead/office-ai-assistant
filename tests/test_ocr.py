# -*- coding: utf-8 -*-
"""
OCRモジュールの単体テスト（改善版）
- 実際の画像を使ったOCRテスト（画像があれば実行）
- 正規表現による請求書情報抽出のテスト（モック使用）
"""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.ocr_engine import InvoiceRecognizer


class TestOCR(unittest.TestCase):
    """OCRエンジンのテスト"""

    @classmethod
    def setUpClass(cls):
        cls.ocr = InvoiceRecognizer(lang='jpn+eng')
        cls.sample_image = Path(__file__).parent.parent / "samples" / "invoice_sample.jpg"
        cls.has_sample = cls.sample_image.exists()

    def test_image_to_text_with_sample(self):
        """サンプル画像が存在する場合のみOCRをテスト"""
        if not self.has_sample:
            self.skipTest("サンプル画像がありません。samples/invoice_sample.jpg を配置してください。")
        text = self.ocr.image_to_text(str(self.sample_image))
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0, "OCR結果が空です")
        # 最低限、日本語または数字が含まれていることを確認
        self.assertTrue(any(c.isdigit() or ord(c) > 0x3000 for c in text),
                        "OCR結果に数字または日本語が含まれていません")

    def test_invoice_extraction_with_mock(self):
        """モックを使って正規表現の抽出ロジックをテスト"""
        # モック：image_to_text が特定のテキストを返すようにする
        dummy_text = """株式会社サンプル
請求書番号: INV-2025-00123
発行日: 2025年3月15日
合計金額: 54,800円
売主: テスト商事株式会社
ありがとうございました。"""

        with patch.object(self.ocr, 'image_to_text', return_value=dummy_text):
            info = self.ocr.extract_invoice_info("dummy.jpg")
            self.assertEqual(info['invoice_no'], "INV-2025-00123")
            self.assertEqual(info['amount'], "54,800")
            self.assertEqual(info['date'], "2025年3月15日")
            self.assertEqual(info['seller'], "テスト商事株式会社")
            self.assertIn("請求書番号", info['full_text'])

    def test_invoice_extraction_edge_cases(self):
        """エッジケース：フォーマットが異なる場合も柔軟に抽出できるか"""
        test_cases = [
            # (入力テキスト, 期待される番号, 金額, 日付, 売手)
            (
                "Invoice No.: ABC123\nTotal: $1,234.56\nDate: 2024-12-01\nSeller: XYZ Corp",
                "ABC123", "1,234.56", "2024-12-01", "XYZ Corp"
            ),
            (
                "伝票番号 987654\n合計 3,200 円\n日付 2023/01/15\n販売者 株式会社鈴木商店",
                "987654", "3,200", "2023/01/15", "株式会社鈴木商店"
            ),
            (
                "No. INV-999\nAmount 7,500 JPY\nIssued 2022.10.20\nCompany: A&B Co.",
                "INV-999", "7,500", "2022.10.20", "A&B Co."
            ),
        ]

        for text, expected_no, expected_amt, expected_date, expected_seller in test_cases:
            with patch.object(self.ocr, 'image_to_text', return_value=text):
                info = self.ocr.extract_invoice_info("dummy.jpg")
                self.assertEqual(info['invoice_no'], expected_no)
                self.assertEqual(info['amount'], expected_amt)
                self.assertEqual(info['date'], expected_date)
                self.assertEqual(info['seller'], expected_seller)

    def test_invoice_extraction_missing_fields(self):
        """必須フィールドが欠けている場合、None を返すべき"""
        text = "ただのテキストで請求書情報はありません"
        with patch.object(self.ocr, 'image_to_text', return_value=text):
            info = self.ocr.extract_invoice_info("dummy.jpg")
            self.assertIsNone(info['invoice_no'])
            self.assertIsNone(info['amount'])
            self.assertIsNone(info['date'])
            self.assertIsNone(info['seller'])
            self.assertEqual(info['full_text'], text)


if __name__ == '__main__':
    unittest.main()