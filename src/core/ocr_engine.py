# -*- coding: utf-8 -*-
"""OCR と帳票情報抽出を扱うモジュール。"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path


DEFAULT_TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


class InvoiceRecognizer:
    """OCR と帳票系ドキュメントの情報抽出を行う。"""

    DOCUMENT_KEYWORDS = {
        "請求書": ("請求書", "invoice"),
        "領収書": ("領収書", "receipt"),
        "見積書": ("見積書", "quotation", "quote"),
        "申請書": ("申請書", "application"),
        "契約書": ("契約書", "agreement", "contract"),
    }

    def __init__(self, lang: str = "jpn+eng"):
        self.lang = lang

    def image_to_text(self, image_path: str) -> str:
        """画像または PDF から最も扱いやすいテキストを返す。"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {image_path}")
        if path.suffix.lower() in PDF_SUFFIXES:
            return self._pdf_to_text(path)
        return self._image_path_to_text(path)

    def extract_invoice_info(self, image_path: str) -> dict[str, object]:
        """入力ファイルから主要な帳票情報を抽出する。"""
        full_text = self.image_to_text(image_path)
        normalized_text = self._normalize_search_text(full_text)
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        key_values = self._extract_key_value_candidates(lines)

        document_type = self._detect_document_type(full_text)
        invoice_no = self._extract_invoice_number(normalized_text, lines, key_values)
        amount = self._extract_amount(normalized_text, lines, key_values)
        date_value = self._extract_date(normalized_text, lines, key_values)
        seller = self._extract_party(normalized_text, lines, key_values, target="seller")
        buyer = self._extract_party(normalized_text, lines, key_values, target="buyer")

        result = {
            "document_type": document_type,
            "invoice_no": invoice_no,
            "amount": amount,
            "date": date_value,
            "seller": seller,
            "buyer": buyer,
            "full_text": full_text,
        }
        result["amount_normalized"] = self._normalize_amount(amount)
        result["layout_info"] = self._safe_layout_analysis(image_path)
        result["format_type"] = self._guess_format_type(result["layout_info"], full_text)
        result["document_kind"] = self._guess_document_kind(full_text, document_type)
        result["validation"] = self._validate_fields(result)
        return result

    def analyze_document(self, image_path: str) -> dict[str, object]:
        """非定型文書も含めた分析レポートを返す。"""
        invoice_info = self.extract_invoice_info(image_path)
        full_text = invoice_info.get("full_text") or ""
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        key_values = self._extract_key_value_candidates(lines)
        sections = self._extract_sections(lines)
        rpa_payload = self._build_rpa_payload(image_path, invoice_info, key_values)

        return {
            "format_type": invoice_info.get("format_type", "非定型"),
            "document_kind": invoice_info.get("document_kind", "一般文書"),
            "invoice_info": invoice_info,
            "key_values": key_values,
            "sections": sections,
            "rpa_payload": rpa_payload,
            "automation_points": self._build_automation_points(invoice_info, key_values),
        }

    def archive_ocr_result(self, image_path: str, base_output_dir: str | None = None) -> dict[str, str]:
        """OCR 結果を原本・テキスト・JSON で整理保存する。"""
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {image_path}")

        info = self.extract_invoice_info(str(source))
        seller = self._sanitize_name(info.get("seller") or "unknown_seller")
        date_value = self._sanitize_name(info.get("date") or datetime.now().strftime("%Y-%m-%d"))
        invoice_no = self._sanitize_name(info.get("invoice_no") or source.stem)

        root = Path(base_output_dir) if base_output_dir else Path.cwd() / "output" / "ocr_archive"
        target_dir = root / seller / date_value
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_source = target_dir / source.name
        if source.resolve() != copied_source.resolve():
            shutil.copy2(source, copied_source)

        text_path = target_dir / f"{invoice_no}.txt"
        json_path = target_dir / f"{invoice_no}.json"
        text_path.write_text(info.get("full_text") or "", encoding="utf-8")
        json_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "folder": str(target_dir),
            "image_path": str(copied_source),
            "text_path": str(text_path),
            "json_path": str(json_path),
        }

    def export_rpa_payload(self, image_path: str, base_output_dir: str | None = None) -> dict[str, str]:
        """RPA 連携用 JSON を出力する。"""
        analysis = self.analyze_document(image_path)
        root = Path(base_output_dir) if base_output_dir else Path.cwd() / "output" / "ocr_rpa"
        root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = root / f"rpa_payload_{timestamp}.json"
        json_path.write_text(json.dumps(analysis["rpa_payload"], ensure_ascii=False, indent=2), encoding="utf-8")
        return {"json_path": str(json_path)}

    def screenshot_ocr(self) -> str:
        """画面全体をキャプチャして OCR を行う。"""
        pytesseract, _image_module = self._load_ocr_dependencies()
        from PIL import ImageGrab

        self._setup_tesseract(pytesseract)
        screenshot = ImageGrab.grab()
        return self._image_object_to_text(screenshot, pytesseract)

    def _image_path_to_text(self, path: Path) -> str:
        """画像ファイルから OCR テキストを返す。"""
        pytesseract, image_module = self._load_ocr_dependencies()
        self._setup_tesseract(pytesseract)
        image = image_module.open(path)
        return self._image_object_to_text(image, pytesseract)

    def _image_object_to_text(self, image, pytesseract_module) -> str:
        """PIL 画像から最良の OCR テキストを返す。"""
        candidates: list[tuple[int, str]] = []
        for prepared in self._prepare_image_variants(image):
            for config in ("--psm 6", "--psm 4", "--psm 11", "--psm 3"):
                try:
                    text = pytesseract_module.image_to_string(prepared, lang=self.lang, config=config)
                except Exception:
                    continue
                normalized = self._normalize_text(text)
                if not normalized:
                    continue
                candidates.append((self._score_ocr_text(normalized), normalized))

        if not candidates:
            return ""
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _pdf_to_text(self, path: Path) -> str:
        """PDF からテキストを抽出し、必要ならページ OCR で補う。"""
        direct_text = self._extract_text_from_pdf(path)
        direct_score = self._score_ocr_text(direct_text) if direct_text else 0

        ocr_text = self._ocr_pdf_pages(path, max_pages=4)
        ocr_score = self._score_ocr_text(ocr_text) if ocr_text else 0

        if direct_score >= ocr_score and direct_text:
            return direct_text
        if ocr_text:
            return ocr_text
        return direct_text

    def _extract_text_from_pdf(self, path: Path) -> str:
        """PDF の埋め込みテキストを抽出する。"""
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError:
            return ""

        texts = []
        try:
            reader = PdfReader(str(path))
            for page in reader.pages[:6]:
                page_text = page.extract_text() or ""
                normalized = self._normalize_text(page_text)
                if normalized:
                    texts.append(normalized)
        except Exception:
            return ""
        return "\n".join(texts)

    def _ocr_pdf_pages(self, path: Path, max_pages: int = 4) -> str:
        """PDF ページを画像化して OCR を行う。"""
        pytesseract, _image_module = self._load_ocr_dependencies()
        self._setup_tesseract(pytesseract)

        texts = []
        for index, image in self._iter_pdf_page_images(path, max_pages=max_pages):
            page_text = self._image_object_to_text(image, pytesseract)
            if page_text:
                texts.append(f"[page {index + 1}]\n{page_text}")
        return "\n\n".join(texts)

    def _iter_pdf_page_images(self, path: Path, max_pages: int = 4):
        """PDF の先頭ページ群を PIL 画像へ変換する。"""
        try:
            import fitz
            from PIL import Image
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError("PDF OCR には PyMuPDF と Pillow が必要です。") from error

        document = fitz.open(str(path))
        try:
            for index in range(min(max_pages, document.page_count)):
                page = document.load_page(index)
                matrix = fitz.Matrix(2, 2)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                yield index, image
        finally:
            document.close()

    def _prepare_image_variants(self, image):
        """OCR 用に複数の前処理画像を返す。"""
        try:
            from PIL import ImageFilter, ImageOps
        except Exception:
            return [image]

        base = image.convert("L")
        auto = ImageOps.autocontrast(base)
        sharpened = auto.filter(ImageFilter.SHARPEN)
        binary = auto.point(lambda px: 255 if px > 180 else 0)
        denoised = sharpened.filter(ImageFilter.MedianFilter(size=3))
        return [auto, sharpened, binary, denoised]

    def _safe_layout_analysis(self, image_path: str) -> dict[str, object]:
        """レイアウト解析を安全に実行する。"""
        try:
            return self._analyze_layout(image_path)
        except Exception:
            return {
                "image_size": {"width": 0, "height": 0},
                "table_regions": [],
                "note": "レイアウト解析に失敗しました。OCR テキストのみを利用してください。",
            }

    def _setup_tesseract(self, pytesseract_module):
        """Tesseract 実行ファイルの設定を行う。"""
        if DEFAULT_TESSERACT_PATH.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(DEFAULT_TESSERACT_PATH)

    def _detect_document_type(self, text: str) -> str:
        """文書タイトルや本文から種類を推定する。"""
        lowered = self._normalize_search_text(text).lower()
        for label, keywords in self.DOCUMENT_KEYWORDS.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                return label
        if "invoice no" in lowered or "bill to" in lowered:
            return "請求書"
        return "一般文書"

    def _extract_invoice_number(self, text: str, lines: list[str], key_values: list[dict[str, str]]) -> str | None:
        """請求番号系の値を抽出する。"""
        patterns = (
            r"(?:請求書番号|請求番号|伝票番号|帳票番号|invoice\s*no\.?|no\.?)\s*[:：#\-]?\s*([A-Za-z0-9\-_\/]+)",
        )
        match = self._search_patterns(text, patterns)
        if match:
            return match
        return self._search_key_values(key_values, ("請求", "invoice", "番号", "no"))

    def _extract_amount(self, text: str, lines: list[str], key_values: list[dict[str, str]]) -> str | None:
        """金額を抽出する。"""
        patterns = (
            r"(?:合計金額|請求金額|金額|総額|amount|total)\s*[:：]?\s*[¥￥$]?\s*([\d,]+(?:\.\d+)?)",
            r"[¥￥$]\s*([\d,]+(?:\.\d+)?)",
        )
        match = self._search_patterns(text, patterns)
        if match:
            return match

        for line in lines:
            if any(keyword in line.lower() for keyword in ("amount", "total")) or any(
                keyword in line for keyword in ("金額", "合計", "総額")
            ):
                number = self._extract_first_number(line)
                if number:
                    return number
        return self._search_key_values(key_values, ("金額", "合計", "total", "amount"))

    def _extract_date(self, text: str, lines: list[str], key_values: list[dict[str, str]]) -> str | None:
        """日付を抽出する。"""
        patterns = (
            r"(?:請求日|発行日|日付|date|issued)\s*[:：]?\s*(\d{4}[./-]\d{1,2}[./-]\d{1,2})",
            r"(?:請求日|発行日|日付|date|issued)\s*[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            r"(令和\d+年\d+月\d+日)",
        )
        match = self._search_patterns(text, patterns)
        if match:
            return match
        return self._search_key_values(key_values, ("日付", "発行", "date", "issued"))

    def _extract_party(
        self,
        text: str,
        lines: list[str],
        key_values: list[dict[str, str]],
        target: str,
    ) -> str | None:
        """売り手または宛先を抽出する。"""
        if target == "seller":
            patterns = (r"(?:発行元|請求元|販売元|会社名|seller|company)\s*[:：]?\s*(.+)",)
            fallback_keywords = ("株式会社", "有限会社", "company", "corp", "inc")
        else:
            patterns = (r"(?:宛先|請求先|御中|様|buyer|bill to)\s*[:：]?\s*(.+)",)
            fallback_keywords = ("御中", "様", "bill to", "buyer")

        match = self._search_patterns(text, patterns, multiline=True)
        if match:
            return self._clean_party_name(match)

        key_value = self._search_key_values(
            key_values,
            ("会社", "発行", "seller", "company") if target == "seller" else ("宛先", "請求先", "buyer", "bill"),
        )
        if key_value:
            return self._clean_party_name(key_value)

        for line in lines:
            normalized = self._normalize_search_text(line).lower()
            if any(keyword.lower() in normalized for keyword in fallback_keywords):
                return self._clean_party_name(line)
        return None

    def _search_key_values(self, key_values: list[dict[str, str]], keywords: tuple[str, ...]) -> str | None:
        """キー候補から値を引く。"""
        for row in key_values:
            key = self._normalize_search_text(row.get("key", "")).lower()
            if any(keyword.lower() in key for keyword in keywords):
                value = row.get("value", "").strip()
                return value or None
        return None

    def _extract_first_number(self, text: str) -> str | None:
        """行内の最初の数値表現を返す。"""
        match = re.search(r"([\d,]+(?:\.\d+)?)", self._normalize_search_text(text))
        return match.group(1) if match else None

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
        """金額を表示しやすい形へ整える。"""
        if not amount:
            return None
        normalized = amount.replace(",", "").replace(" ", "")
        if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
            if "." in normalized:
                return f"¥{float(normalized):,.2f}"
            return f"¥{int(normalized):,}"
        return amount

    def _guess_document_kind(self, text: str, detected_type: str | None) -> str:
        """文書カテゴリをやや広めに推定する。"""
        lowered = self._normalize_search_text(text).lower()
        if detected_type and detected_type != "一般文書":
            return detected_type
        if any(keyword in lowered for keyword in ("メモ", "memo", "議事録")):
            return "メモ / 議事録"
        if any(keyword in lowered for keyword in ("report", "article", "news")):
            return "記事 / レポート"
        if any(keyword in lowered for keyword in ("agreement", "contract")):
            return "契約関連"
        return "一般文書"

    def _guess_format_type(self, layout_info: dict[str, object], full_text: str) -> str:
        """定型 / 非定型を推定する。"""
        table_regions = layout_info.get("table_regions") or []
        lowered = self._normalize_search_text(full_text).lower()
        if table_regions:
            return "定型"
        if any(keyword.lower() in lowered for keyword in ("請求書", "領収書", "invoice", "receipt", "見積書")):
            return "定型"
        return "非定型"

    def _normalize_text(self, text: str) -> str:
        """改行や空白を整理して OCR テキストを正規化する。"""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)

    def _normalize_search_text(self, text: str) -> str:
        """検索向けに全文字を整形する。"""
        return unicodedata.normalize("NFKC", text or "")

    def _score_ocr_text(self, text: str) -> int:
        """OCR 候補テキストの品質スコアを返す。"""
        score = len(text)
        score += len(re.findall(r"\d", text)) * 2
        score += len(re.findall(r"(請求書|領収書|invoice|receipt|金額|amount|date)", text, re.IGNORECASE)) * 20
        score += min(len(text.splitlines()), 20) * 3
        return score

    def _extract_key_value_candidates(self, lines: list[str]) -> list[dict[str, str]]:
        """非定型文書からキー / 値候補を抽出する。"""
        results: list[dict[str, str]] = []
        for line in lines:
            if len(results) >= 20:
                break
            match = re.match(r"^\s*([^:：]{1,24})\s*[:：]\s*(.+)$", line)
            if match:
                results.append({"key": match.group(1).strip(), "value": match.group(2).strip()})
                continue
            spaced = re.match(r"^\s*(\S.{0,20}?)\s{2,}(.+)$", line)
            if spaced:
                results.append({"key": spaced.group(1).strip(), "value": spaced.group(2).strip()})
        return results

    def _extract_sections(self, lines: list[str]) -> list[dict[str, str]]:
        """文書全体の簡易セクションを返す。"""
        sections: list[dict[str, str]] = []
        if not lines:
            return sections
        sections.append({"title": "冒頭", "content": lines[0][:120]})
        if len(lines) > 1:
            sections.append({"title": "本文要約", "content": " / ".join(lines[1:4])[:180]})
        if len(lines) > 4:
            sections.append({"title": "末尾要約", "content": " / ".join(lines[-3:])[:180]})
        return sections

    def _build_rpa_payload(
        self,
        image_path: str,
        invoice_info: dict[str, object],
        key_values: list[dict[str, str]],
    ) -> dict[str, object]:
        """RPA 連携向けの JSON を組み立てる。"""
        score = int((invoice_info.get("validation") or {}).get("score", 0))
        return {
            "source_image": str(Path(image_path).resolve()),
            "format_type": invoice_info.get("format_type", "非定型"),
            "document_kind": invoice_info.get("document_kind", "一般文書"),
            "fields": {
                "document_type": invoice_info.get("document_type"),
                "invoice_no": invoice_info.get("invoice_no"),
                "amount": invoice_info.get("amount_normalized") or invoice_info.get("amount"),
                "date": invoice_info.get("date"),
                "seller": invoice_info.get("seller"),
                "buyer": invoice_info.get("buyer"),
            },
            "key_values": key_values,
            "validation": invoice_info.get("validation", {}),
            "next_actions": self._build_validation_recommendation(score),
        }

    def _build_automation_points(
        self,
        invoice_info: dict[str, object],
        key_values: list[dict[str, str]],
    ) -> list[str]:
        """RPA 連携で使いやすいアクション案を返す。"""
        points = []
        if invoice_info.get("invoice_no"):
            points.append("請求番号を基幹システムの検索キーへ自動転記できます。")
        if invoice_info.get("amount_normalized") or invoice_info.get("amount"):
            points.append("金額を経費申請や請求管理フローへ自動入力できます。")
        if key_values:
            points.append("非定型文書でもキー / 値候補を RPA マッピングに活用できます。")
        points.append("確認スコアが低い場合は人手確認ステップを残す運用が安全です。")
        return points

    def _load_ocr_dependencies(self):
        """OCR 依存ライブラリを読み込む。"""
        try:
            import pytesseract
            from PIL import Image
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError("OCR 機能には pytesseract と Pillow が必要です。") from error
        return pytesseract, Image

    def _analyze_layout(self, image_path: str) -> dict[str, object]:
        """画像または PDF から表領域候補を抽出する。"""
        if Path(image_path).suffix.lower() in PDF_SUFFIXES:
            page_images = list(self._iter_pdf_page_images(Path(image_path), max_pages=1))
            if not page_images:
                return {
                    "image_size": {"width": 0, "height": 0},
                    "table_regions": [],
                    "note": "PDF ページを画像化できませんでした。",
                }
            return self._analyze_layout_image(page_images[0][1])

        pytesseract, image_module = self._load_ocr_dependencies()
        image = image_module.open(image_path)
        return self._analyze_layout_image(image, pytesseract_module=pytesseract)

    def _analyze_layout_image(self, image, pytesseract_module=None) -> dict[str, object]:
        """PIL 画像から表領域候補を抽出する。"""
        pytesseract = pytesseract_module
        if pytesseract is None:
            pytesseract, _image_module = self._load_ocr_dependencies()
        self._setup_tesseract(pytesseract)

        prepared = self._prepare_image_variants(image)[0]
        width, height = prepared.size
        output_dict = pytesseract.image_to_data(
            prepared,
            lang=self.lang,
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )

        row_map: dict[tuple[int, int, int], list[dict[str, int | str]]] = {}
        total_items = len(output_dict.get("text", []))
        for index in range(total_items):
            text = (output_dict["text"][index] or "").strip()
            if not text:
                continue
            try:
                confidence = float(output_dict["conf"][index])
            except (TypeError, ValueError):
                confidence = -1.0
            if confidence < 20:
                continue
            key = (
                int(output_dict["block_num"][index]),
                int(output_dict["par_num"][index]),
                int(output_dict["line_num"][index]),
            )
            row_map.setdefault(key, []).append(
                {
                    "text": text,
                    "x": int(output_dict["left"][index]),
                    "y": int(output_dict["top"][index]),
                    "w": int(output_dict["width"][index]),
                    "h": int(output_dict["height"][index]),
                }
            )

        row_candidates = []
        for words in row_map.values():
            if len(words) < 3:
                continue
            left = min(int(word["x"]) for word in words)
            right = max(int(word["x"]) + int(word["w"]) for word in words)
            top = min(int(word["y"]) for word in words)
            bottom = max(int(word["y"]) + int(word["h"]) for word in words)
            coverage = (right - left) / max(width, 1)
            if coverage < 0.35:
                continue
            row_candidates.append(
                {
                    "x": left,
                    "y": top,
                    "w": max(1, right - left),
                    "h": max(1, bottom - top),
                    "words": len(words),
                }
            )

        row_candidates.sort(key=lambda item: item["y"])
        merged_regions = []
        for row in row_candidates:
            if not merged_regions:
                merged_regions.append(
                    {
                        "x": row["x"],
                        "y": row["y"],
                        "w": row["w"],
                        "h": row["h"],
                        "line_count": 1,
                        "word_count": row["words"],
                    }
                )
                continue
            last = merged_regions[-1]
            same_column = abs(last["x"] - row["x"]) < 60 and abs((last["x"] + last["w"]) - (row["x"] + row["w"])) < 90
            near_line = row["y"] <= last["y"] + last["h"] + 35
            if same_column and near_line:
                x1 = min(last["x"], row["x"])
                y1 = min(last["y"], row["y"])
                x2 = max(last["x"] + last["w"], row["x"] + row["w"])
                y2 = max(last["y"] + last["h"], row["y"] + row["h"])
                last["x"], last["y"] = x1, y1
                last["w"], last["h"] = max(1, x2 - x1), max(1, y2 - y1)
                last["line_count"] += 1
                last["word_count"] += row["words"]
            else:
                merged_regions.append(
                    {
                        "x": row["x"],
                        "y": row["y"],
                        "w": row["w"],
                        "h": row["h"],
                        "line_count": 1,
                        "word_count": row["words"],
                    }
                )

        table_regions = [region for region in merged_regions if region["line_count"] >= 3 and region["word_count"] >= 10]
        table_regions = sorted(table_regions, key=lambda item: item["word_count"], reverse=True)[:4]
        note = "表形式の候補領域を検出しました。" if table_regions else "表形式の候補は検出できませんでした。"
        return {
            "image_size": {"width": width, "height": height},
            "table_regions": table_regions,
            "note": note,
        }

    def _validate_fields(self, result: dict[str, object]) -> dict[str, object]:
        """抽出フィールドの妥当性チェックを返す。"""
        checks = []

        invoice_no = result.get("invoice_no")
        checks.append(
            {
                "field": "請求番号",
                "status": "OK" if invoice_no and len(str(invoice_no)) >= 3 else "確認要",
                "message": f"請求番号: {invoice_no}" if invoice_no else "請求番号を検出できませんでした。",
            }
        )

        amount = result.get("amount_normalized") or result.get("amount")
        checks.append(
            {
                "field": "金額",
                "status": "OK" if amount and re.search(r"\d", str(amount)) else "確認要",
                "message": f"金額: {amount}" if amount else "金額を検出できませんでした。",
            }
        )

        date_value = result.get("date")
        checks.append(
            {
                "field": "日付",
                "status": "OK" if date_value and self._is_date_like(str(date_value)) else "確認要",
                "message": f"日付: {date_value}" if date_value else "日付形式の候補が見つかりませんでした。",
            }
        )

        seller = result.get("seller")
        checks.append(
            {
                "field": "発行元",
                "status": "OK" if seller else "確認要",
                "message": f"発行元: {seller}" if seller else "発行元を検出できませんでした。",
            }
        )

        buyer = result.get("buyer")
        checks.append(
            {
                "field": "宛先",
                "status": "OK" if buyer else "確認要",
                "message": f"宛先: {buyer}" if buyer else "宛先を検出できませんでした。",
            }
        )

        score = max(0, 100 - sum(18 for check in checks if check["status"] != "OK"))
        return {
            "score": score,
            "checks": checks,
            "recommendation": self._build_validation_recommendation(score),
        }

    def _is_date_like(self, value: str) -> bool:
        """日付らしい文字列かどうか判定する。"""
        patterns = (
            r"\d{4}[./-]\d{1,2}[./-]\d{1,2}",
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"令和\d+年\d+月\d+日",
        )
        return any(re.search(pattern, value) for pattern in patterns)

    def _build_validation_recommendation(self, score: int) -> str:
        """スコアから確認アクションを返す。"""
        if score >= 82:
            return "抽出精度は高めです。金額と日付を原本と照合してから登録してください。"
        if score >= 60:
            return "一部項目の確認が必要です。請求番号・発行元・宛先を重点確認してください。"
        return "抽出品質が不安定です。画像の再スキャンや手動確認を優先してください。"

    def _clean_party_name(self, value: str) -> str:
        """会社名や宛先の余分な記号を取り除く。"""
        cleaned = value.strip().strip(":：- ")
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        if cleaned.lower().startswith(("seller", "company", "buyer", "bill to")):
            parts = re.split(r"[:：]", cleaned, maxsplit=1)
            if len(parts) == 2:
                cleaned = parts[1].strip()
        cleaned = re.sub(r"^(発行元|会社名|請求元|販売元|宛先|請求先)\s*", "", cleaned)
        return cleaned.strip() or value.strip()

    def _sanitize_name(self, value: str) -> str:
        """保存先ファイル名に使える安全な文字列へ変換する。"""
        cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip()
        cleaned = cleaned.replace(" ", "_")
        return cleaned[:80] or "unknown"
