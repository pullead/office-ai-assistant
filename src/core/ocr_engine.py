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
        candidates = []
        for config in ("--psm 6", "--psm 4", "--psm 11", "--psm 3"):
            try:
                text = pytesseract.image_to_string(prepared_image, lang=self.lang, config=config)
                normalized = self._normalize_text(text)
                if normalized:
                    score = self._score_ocr_text(normalized)
                    candidates.append((score, normalized))
            except Exception:
                continue
        if not candidates:
            return ""
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def extract_invoice_info(self, image_path: str) -> dict[str, object]:
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
        try:
            result["layout_info"] = self._analyze_layout(image_path)
        except Exception:
            result["layout_info"] = {
                "image_size": {"width": 0, "height": 0},
                "table_regions": [],
                "note": "版面解析に失敗しました。ファイル存在と画像形式を確認してください。",
            }
        result["format_type"] = self._guess_format_type(result["layout_info"], full_text)
        result["document_kind"] = self._guess_document_kind(full_text, result["document_type"])
        result["validation"] = self._validate_fields(result)
        return result

    def analyze_document(self, image_path: str) -> dict[str, object]:
        """定型・非定型を含む文書全体を解析する。"""
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

    def export_rpa_payload(self, image_path: str, base_output_dir: str | None = None) -> dict[str, str]:
        """RPA 連携向け JSON を保存する。"""
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

    def _guess_document_kind(self, text: str, detected_type: str | None) -> str:
        """文書種別を広めに推定する。"""
        lowered = text.lower()
        if detected_type and detected_type != "帳票":
            return detected_type
        if any(keyword in text for keyword in ("申込書", "申請書", "注文書", "納品書")):
            return "業務帳票"
        if any(keyword in text for keyword in ("手書き", "メモ", "打合せ", "議事録")):
            return "メモ/記録"
        if any(keyword in text for keyword in ("契約", "agreement", "契約書")):
            return "契約関連"
        if any(keyword in lowered for keyword in ("article", "report", "news")):
            return "記事/レポート"
        return "一般文書"

    def _guess_format_type(self, layout_info: dict, full_text: str) -> str:
        """定型/非定型を判定する。"""
        table_regions = layout_info.get("table_regions") or []
        structured_keywords = ("請求書", "領収書", "申込書", "注文書", "invoice", "receipt")
        if table_regions or any(keyword.lower() in full_text.lower() for keyword in structured_keywords):
            return "定型"
        return "非定型"

    def _normalize_text(self, text: str) -> str:
        """改行と空白を整えて返す。"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)

    def _score_ocr_text(self, text: str) -> int:
        """OCR テキストの簡易品質スコアを返す。"""
        score = len(text)
        score += len(re.findall(r"\d", text)) * 2
        score += len(re.findall(r"(請求|領収|金額|合計|invoice|receipt)", text, re.IGNORECASE)) * 20
        return score

    def _extract_key_value_candidates(self, lines: list[str]) -> list[dict[str, str]]:
        """非定型文書からキー/値候補を抽出する。"""
        results: list[dict[str, str]] = []
        for line in lines:
            if len(results) >= 16:
                break
            match = re.match(r"^\s*([^:：]{1,24})\s*[:：]\s*(.+)$", line)
            if match:
                results.append({"key": match.group(1).strip(), "value": match.group(2).strip()})
                continue
            spaced = re.match(r"^\s*([^\s]{1,20})\s{2,}(.+)$", line)
            if spaced:
                results.append({"key": spaced.group(1).strip(), "value": spaced.group(2).strip()})
        return results

    def _extract_sections(self, lines: list[str]) -> list[dict[str, str]]:
        """文書冒頭の要点ブロックを作る。"""
        sections: list[dict[str, str]] = []
        if not lines:
            return sections
        sections.append({"title": "冒頭", "content": lines[0][:120]})
        if len(lines) > 1:
            sections.append({"title": "本文候補", "content": " / ".join(lines[1:4])[:180]})
        if len(lines) > 4:
            sections.append({"title": "後半候補", "content": " / ".join(lines[-3:])[:180]})
        return sections

    def _build_rpa_payload(
        self,
        image_path: str,
        invoice_info: dict[str, object],
        key_values: list[dict[str, str]],
    ) -> dict[str, object]:
        """RPA 連携向けの正規化 JSON を返す。"""
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
            "next_actions": self._build_validation_recommendation(
                int((invoice_info.get("validation") or {}).get("score", 0))
            ),
        }

    def _build_automation_points(
        self,
        invoice_info: dict[str, object],
        key_values: list[dict[str, str]],
    ) -> list[str]:
        """RPA 連携時の自動化ポイントを返す。"""
        points = []
        if invoice_info.get("invoice_no"):
            points.append("請求番号を業務システムのキー項目へ自動入力できます。")
        if invoice_info.get("amount_normalized") or invoice_info.get("amount"):
            points.append("金額を精算・会計フローへ引き渡す候補があります。")
        if key_values:
            points.append("非定型文書でもキー/値候補を RPA マッピングに利用できます。")
        points.append("検証スコアが低い場合は人手確認ステップを残す構成を推奨します。")
        return points

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

    def _analyze_layout(self, image_path: str) -> dict:
        """画像の版面情報を解析し、表領域候補を返す。"""
        pytesseract, image_module = self._load_ocr_dependencies()
        self._setup_tesseract(pytesseract)
        image = image_module.open(image_path)
        prepared = self._prepare_image(image)
        width, height = prepared.size
        output_dict = pytesseract.image_to_data(
            prepared,
            lang=self.lang,
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )

        row_candidates = []
        row_map: dict[tuple[int, int, int], list[dict]] = {}
        total_items = len(output_dict.get("text", []))
        for index in range(total_items):
            text = (output_dict["text"][index] or "").strip()
            if not text:
                continue
            try:
                conf = float(output_dict["conf"][index])
            except (TypeError, ValueError):
                conf = -1.0
            if conf < 20:
                continue
            block_num = int(output_dict["block_num"][index])
            par_num = int(output_dict["par_num"][index])
            line_num = int(output_dict["line_num"][index])
            key = (block_num, par_num, line_num)
            row_map.setdefault(key, []).append(
                {
                    "text": text,
                    "x": int(output_dict["left"][index]),
                    "y": int(output_dict["top"][index]),
                    "w": int(output_dict["width"][index]),
                    "h": int(output_dict["height"][index]),
                }
            )

        for words in row_map.values():
            if len(words) < 3:
                continue
            left = min(word["x"] for word in words)
            right = max(word["x"] + word["w"] for word in words)
            top = min(word["y"] for word in words)
            bottom = max(word["y"] + word["h"] for word in words)
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
        layout_note = (
            "表形式の領域を検出しました。"
            if table_regions
            else "明確な表形式領域は検出できませんでした。"
        )
        return {
            "image_size": {"width": width, "height": height},
            "table_regions": table_regions,
            "note": layout_note,
        }

    def _validate_fields(self, result: dict) -> dict:
        """抽出フィールドの妥当性を評価する。"""
        checks = []

        invoice_no = result.get("invoice_no")
        if invoice_no and len(str(invoice_no)) >= 3:
            checks.append({"field": "請求番号", "status": "OK", "message": "請求番号を抽出しました。"})
        else:
            checks.append({"field": "請求番号", "status": "要確認", "message": "請求番号が不明です。"})

        amount = result.get("amount_normalized") or result.get("amount")
        if amount and re.search(r"\d", str(amount)):
            checks.append({"field": "金額", "status": "OK", "message": f"金額候補: {amount}"})
        else:
            checks.append({"field": "金額", "status": "要確認", "message": "金額を抽出できませんでした。"})

        date_value = result.get("date")
        if date_value and self._is_date_like(str(date_value)):
            checks.append({"field": "日付", "status": "OK", "message": f"日付候補: {date_value}"})
        else:
            checks.append({"field": "日付", "status": "要確認", "message": "日付形式の候補が不足しています。"})

        seller = result.get("seller")
        checks.append(
            {
                "field": "発行元",
                "status": "OK" if seller else "要確認",
                "message": f"発行元: {seller}" if seller else "発行元が抽出できませんでした。",
            }
        )

        buyer = result.get("buyer")
        checks.append(
            {
                "field": "宛先",
                "status": "OK" if buyer else "要確認",
                "message": f"宛先: {buyer}" if buyer else "宛先が抽出できませんでした。",
            }
        )

        score = 100
        for check in checks:
            if check["status"] != "OK":
                score -= 18
        score = max(0, score)
        return {
            "score": score,
            "checks": checks,
            "recommendation": self._build_validation_recommendation(score),
        }

    def _is_date_like(self, value: str) -> bool:
        """日付らしい文字列かを判定する。"""
        patterns = (
            r"\d{4}[./-]\d{1,2}[./-]\d{1,2}",
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"令和\d+年\d+月\d+日",
        )
        return any(re.search(pattern, value) for pattern in patterns)

    def _build_validation_recommendation(self, score: int) -> str:
        """検証スコアから推奨アクションを返す。"""
        if score >= 82:
            return "抽出精度は高めです。金額と日付のみ原本照合すれば保存可能です。"
        if score >= 60:
            return "一部項目の再確認が必要です。請求番号・発行元を重点チェックしてください。"
        return "抽出品質が低い可能性があります。解像度の高い画像で再OCRし、手動補正を推奨します。"

    def _sanitize_name(self, value: str) -> str:
        """保存先フォルダで使える安全な文字列に変換する。"""
        cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip()
        cleaned = cleaned.replace(" ", "_")
        return cleaned[:80] or "unknown"
