# -*- coding: utf-8 -*-
"""OCR と帳票情報抽出を行うモジュール。"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class InvoiceRecognizer:
    """OCR と請求書系の基本抽出を担当する。"""

    def __init__(self, lang: str = "jpn+eng"):
        self.lang = lang

    def image_to_text(self, image_path: str) -> str:
        """画像からテキストを抽出する。"""
        pytesseract, image_module = self._load_ocr_dependencies()
        self._setup_tesseract(pytesseract)

        image = image_module.open(image_path)
        prepared_image = self._prepare_image(image)
        text = pytesseract.image_to_string(prepared_image, lang=self.lang, config="--psm 6")
        return self._normalize_text(text)

    def extract_invoice_info(self, image_path: str) -> dict[str, str | None]:
        """請求書や領収書風の画像から重要項目を抽出する。"""
        full_text = self.image_to_text(image_path)
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        invoice_keywords = (
            "請求書",
            "請求番号",
            "invoice",
            "invoice no",
            "receipt",
            "領収書",
            "精算",
            "支払",
            "合計",
        )
        document_type = next((line for line in lines[:8] if any(key in line.lower() for key in invoice_keywords)), None)

        result = {
            "document_type": document_type or self._guess_document_type(full_text),
            "invoice_no": self._search_patterns(
                full_text,
                (
                    r"(?:請求書番号|請求番号|伝票番号|Invoice\s*No\.?|No\.?)\s*[:：#\-]?\s*([A-Za-z0-9\-_\/]+)",
                ),
            ),
            "amount": self._search_patterns(
                full_text,
                (
                    r"(?:合計金額|請求金額|支払金額|税込合計|金額|Amount|Total)\s*[:：]?\s*[¥￥$]?\s*([\d,]+(?:\.\d+)?)",
                    r"[¥￥]\s*([\d,]+)",
                ),
            ),
            "date": self._search_patterns(
                full_text,
                (
                    r"(?:請求日|発行日|日付|Date|Issued)\s*[:：]?\s*(\d{4}[./-]\d{1,2}[./-]\d{1,2})",
                    r"(?:請求日|発行日|日付|Date|Issued)\s*[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                    r"(令和\d+年\d+月\d+日)",
                ),
            ),
            "seller": self._search_patterns(
                full_text,
                (
                    r"(?:発行者|請求元|販売元|会社名|店舗名|差出人|Seller|Company)\s*[:：]?\s*(.+)",
                ),
                multiline=True,
            ),
            "buyer": self._search_patterns(
                full_text,
                (
                    r"(?:請求先|宛先|取引先|Buyer|Bill To)\s*[:：]?\s*(.+)",
                ),
                multiline=True,
            ),
            "full_text": full_text,
        }
        result["amount_normalized"] = self._normalize_amount(result["amount"])
        return result

    def archive_ocr_result(self, image_path: str, base_output_dir: str | None = None) -> dict[str, str]:
        """OCR 結果をテキストと JSON で整理保存する。"""
        image = Path(image_path)
        if not image.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

        info = self.extract_invoice_info(str(image))
        seller = self._sanitize_name(info.get("seller") or "unknown_seller")
        date_value = self._sanitize_name(info.get("date") or datetime.now().strftime("%Y-%m-%d"))
        invoice_no = self._sanitize_name(info.get("invoice_no") or image.stem)

        root = Path(base_output_dir) if base_output_dir else Path.cwd() / "output" / "ocr_archive"
        target_dir = root / seller / date_value
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_image = target_dir / image.name
        if image.resolve() != copied_image.resolve():
            shutil.copy2(image, copied_image)

        text_path = target_dir / f"{invoice_no}.txt"
        json_path = target_dir / f"{invoice_no}.json"

        text_path.write_text(info.get("full_text") or "", encoding="utf-8")
        json_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "folder": str(target_dir),
            "image_path": str(copied_image),
            "text_path": str(text_path),
            "json_path": str(json_path),
        }

    def screenshot_ocr(self) -> str:
        """画面全体をキャプチャして OCR を行う。"""
        pytesseract, _image_module = self._load_ocr_dependencies()
        from PIL import ImageGrab

        self._setup_tesseract(pytesseract)
        screenshot = ImageGrab.grab()
        prepared = self._prepare_image(screenshot)
        return self._normalize_text(pytesseract.image_to_string(prepared, lang=self.lang, config="--psm 6"))

    def _prepare_image(self, image):
        """OCR しやすいように画像を前処理する。"""
        try:
            from PIL import ImageOps

            grayscale = image.convert("L")
            enhanced = ImageOps.autocontrast(grayscale)
            return enhanced
        except Exception:
            return image

    def _setup_tesseract(self, pytesseract_module):
        """Tesseract 実行ファイルの位置を反映する。"""
        if DEFAULT_TESSERACT_PATH.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(DEFAULT_TESSERACT_PATH)

    def _search_patterns(self, text: str, patterns: tuple[str, ...], multiline: bool = False) -> str | None:
        """複数パターンから最初に見つかった値を返す。"""
        flags = re.IGNORECASE | (re.MULTILINE if multiline else 0)
        for pattern in patterns:
            match = re.search(pattern, text, flags)
            if match:
                value = match.group(1).strip()
                return value.splitlines()[0].strip()
        return None

    def _normalize_amount(self, amount: str | None) -> str | None:
        """金額を表示しやすい形に整える。"""
        if not amount:
            return None
        normalized = amount.replace(",", "").replace(" ", "")
        if normalized.isdigit():
            return f"¥{int(normalized):,}"
        return amount

    def _guess_document_type(self, text: str) -> str:
        """本文から帳票種別を推定する。"""
        lowered = text.lower()
        if "領収書" in text or "receipt" in lowered:
            return "領収書"
        if "精算" in text or "経費" in text:
            return "精算書"
        if "請求" in text or "invoice" in lowered:
            return "請求書"
        return "帳票"

    def _normalize_text(self, text: str) -> str:
        """改行と空白を整えて返す。"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)

    def _load_ocr_dependencies(self):
        """OCR に必要なライブラリを読み込む。"""
        try:
            import pytesseract
            from PIL import Image
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "OCR 機能には pytesseract と Pillow が必要です。"
            ) from error
        return pytesseract, Image

    def _sanitize_name(self, value: str) -> str:
        """保存先フォルダで使える安全な文字列に変換する。"""
        cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip()
        cleaned = cleaned.replace(" ", "_")
        return cleaned[:80] or "unknown"
