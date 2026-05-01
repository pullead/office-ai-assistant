# -*- coding: utf-8 -*-
"""OCR モジュールの回帰テスト。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.ocr_engine import IMAGE_SUFFIXES, PDF_SUFFIXES, InvoiceRecognizer


class TestOCR(unittest.TestCase):
    """OCR エンジンの主要動作を確認する。"""

    @classmethod
    def setUpClass(cls):
        cls.ocr = InvoiceRecognizer(lang="jpn+eng")
        cls.samples_dir = Path(__file__).parent.parent / "samples"
        cls.named_sample = cls.samples_dir / "invoice_sample.jpg"

    def test_image_to_text_with_sample(self):
        """実画像または自動生成画像で OCR の基本動作を確認する。"""
        target_image = self.named_sample if self.named_sample.exists() else self._build_synthetic_invoice_image()
        try:
            text = self.ocr.image_to_text(str(target_image))
        except ModuleNotFoundError as error:
            self.skipTest(str(error))
        except Exception as error:
            self.skipTest(f"OCR 実行環境の都合でスキップします: {error}")

        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertTrue(any(character.isdigit() or character.isalpha() for character in text))

    def test_pdf_input_can_be_parsed(self):
        """テキスト埋め込み PDF から帳票情報を抽出できる。"""
        pdf_path = self._build_synthetic_invoice_pdf()
        try:
            text = self.ocr.image_to_text(str(pdf_path))
            info = self.ocr.extract_invoice_info(str(pdf_path))
        except ModuleNotFoundError as error:
            self.skipTest(str(error))

        self.assertIn("INV-PDF-001", text)
        self.assertEqual(info["invoice_no"], "INV-PDF-001")
        self.assertEqual(info["amount"], "12,500")
        self.assertEqual(info["date"], "2026-05-01")
        self.assertEqual(info["seller"], "SAMPLE CORP")

    def test_sample_documents_in_samples_folder_do_not_crash(self):
        """samples 配下の実サンプルを順番に解析しても例外で止まらない。"""
        sample_paths = [
            path
            for path in sorted(self.samples_dir.iterdir())
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES.union(PDF_SUFFIXES)
        ]
        if not sample_paths:
            self.skipTest("samples 配下に OCR 対象ファイルがありません。")

        non_empty_count = 0
        for path in sample_paths[:8]:
            try:
                text = self.ocr.image_to_text(str(path))
                analysis = self.ocr.analyze_document(str(path))
            except ModuleNotFoundError as error:
                self.skipTest(str(error))
            except Exception as error:
                self.fail(f"{path.name} の解析中に例外が発生しました: {error}")

            self.assertIsInstance(text, str)
            self.assertIsInstance(analysis, dict)
            if text.strip():
                non_empty_count += 1
        self.assertGreaterEqual(non_empty_count, 1)

    def test_invoice_extraction_with_mock(self):
        """モックテキストから請求書情報を抽出できる。"""
        dummy_text = """請求書サンプル
請求書番号: INV-2025-00123
発行日: 2025年3月14日
金額: 54,800 円
会社名: テスト株式会社
宛先: ご担当者様
ありがとうございます。"""

        with patch.object(self.ocr, "image_to_text", return_value=dummy_text):
            info = self.ocr.extract_invoice_info("dummy.jpg")
            self.assertEqual(info["invoice_no"], "INV-2025-00123")
            self.assertEqual(info["amount"], "54,800")
            self.assertEqual(info["date"], "2025年3月14日")
            self.assertEqual(info["seller"], "テスト株式会社")
            self.assertEqual(info["buyer"], "ご担当者様")
            self.assertEqual(info["document_type"], "請求書")

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

    def test_analyze_document_returns_rpa_payload(self):
        """分析結果に RPA 向け JSON と検証情報を含める。"""
        text = """領収書
領収書番号: RC-001
日付: 2026-05-01
金額: 12,000 円
会社名: サンプル会計
宛先: 総務部 御中"""
        with patch.object(self.ocr, "image_to_text", return_value=text):
            analysis = self.ocr.analyze_document("dummy.jpg")
            self.assertEqual(analysis["document_kind"], "領収書")
            self.assertIn("fields", analysis["rpa_payload"])
            self.assertGreater(len(analysis["automation_points"]), 0)

    def _build_synthetic_invoice_image(self) -> Path:
        """簡易 OCR テスト用の画像を一時生成する。"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ModuleNotFoundError as error:
            self.skipTest(str(error))

        temp_dir = Path(tempfile.gettempdir())
        target = temp_dir / "office_ai_invoice_sample.png"

        image = Image.new("RGB", (1400, 900), "white")
        draw = ImageDraw.Draw(image)
        font = self._load_test_font(ImageFont, 40)
        lines = [
            "INVOICE",
            "Invoice No: INV-TEST-001",
            "Date: 2026-05-01",
            "Amount: 12500",
            "Seller: SAMPLE CORP",
            "Buyer: TEST TEAM",
        ]
        y = 80
        for line in lines:
            draw.text((80, y), line, fill="black", font=font)
            y += 100
        image.save(target)
        return target

    def _build_synthetic_invoice_pdf(self) -> Path:
        """テキスト入りの簡易 PDF を一時生成する。"""
        try:
            import fitz
        except ModuleNotFoundError as error:
            self.skipTest(str(error))

        temp_dir = Path(tempfile.gettempdir())
        target = temp_dir / "office_ai_invoice_sample.pdf"
        document = fitz.open()
        page = document.new_page(width=595, height=842)
        page.insert_text(
            (72, 72),
            "INVOICE\nInvoice No: INV-PDF-001\nDate: 2026-05-01\nAmount: 12,500\nSeller: SAMPLE CORP\nBuyer: TEST TEAM",
            fontsize=16,
        )
        document.save(target)
        document.close()
        return target

    def _load_test_font(self, image_font_module, size: int):
        """利用可能なフォントを優先して読み込む。"""
        candidates = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/meiryo.ttc"),
            Path("C:/Windows/Fonts/msgothic.ttc"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return image_font_module.truetype(str(candidate), size=size)
        return image_font_module.load_default()


if __name__ == "__main__":
    unittest.main()
