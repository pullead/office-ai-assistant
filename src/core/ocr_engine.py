# -*- coding: utf-8 -*-
"""
OCRエンジン - 画像テキスト変換 + 請求書自動認識
日本語・英語対応（Tesseract使用）
"""
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import pytesseract
from PIL import Image
import re
from typing import Dict, Optional


class InvoiceRecognizer:
    """請求書認識クラス（面接アピールポイント）"""

    def __init__(self, lang: str = 'jpn+eng'):
        """
        Args:
            lang: Tesseract言語パック（例: 'jpn', 'eng', 'jpn+eng'）
        """
        self.lang = lang

    def image_to_text(self, image_path: str) -> str:
        """画像からテキストを抽出（基本OCR）"""
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=self.lang)
        return text.strip()

    def extract_invoice_info(self, image_path: str) -> Dict[str, Optional[str]]:
        """
        請求書から構造化情報を抽出
        戻り値: {
            'invoice_no': 番号,
            'amount': 金額,
            'date': 日付,
            'seller': 売り手,
            'full_text': 全文
        }
        """
        full_text = self.image_to_text(image_path)

        # 正規表現パターン（日本語・中国語・英語対応）
        patterns = {
            'invoice_no': r'(?:請求書番号|伝票番号|番号|Invoice\s*No\.?|No\.?)\s*[：:]\s*(\S+)',
            'amount': r'(?:合計|総額|金額|Amount|Total)\s*[：:]\s*([\d,]+\.?\d*)\s*(?:円|元|JPY|CNY)?',
            'date': r'(?:日付|発行日|Date|Issued)\s*[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})',
            'seller': r'(?:販売者|売主|会社名|Seller|Company)\s*[：:]\s*(.+?)[\n\r]'
        }

        result = {'full_text': full_text}
        for key, pattern in patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            result[key] = match.group(1).strip() if match else None

        return result

    def screenshot_ocr(self) -> str:
        """スクリーンショットをOCR（拡張機能）"""
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        text = pytesseract.image_to_string(screenshot, lang=self.lang)
        return text