# -*- coding: utf-8 -*-
"""ローカルで使える AI 補助処理をまとめたモジュール。"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from src.core.file_manager import FileManager
from src.core.ocr_engine import InvoiceRecognizer
from src.core.web_extractor import WebExtractor


class TaskAssistant:
    """ローカル処理中心の補助タスクを担当する。"""

    def __init__(self, file_manager: FileManager | None = None):
        self.file_manager = file_manager or FileManager()
        self.web_extractor = WebExtractor()

    def execute_command(self, command_text: str) -> str:
        """簡易コマンド文から処理を選ぶ。"""
        cmd = command_text.lower()

        if ("整理" in command_text or "organize" in cmd) and ("desktop" in cmd or "デスクトップ" in command_text):
            return self._organize_desktop()
        if ("ocr" in cmd or "文字認識" in command_text) and ("スクリーン" in command_text or "screenshot" in cmd):
            return self._screenshot_ocr()
        if "分析" in command_text or "workspace" in cmd:
            return self.analyze_workspace(Path.cwd())
        if "todo" in cmd or "タスク" in command_text:
            return self.extract_action_items(command_text)
        if "メール" in command_text or "mail" in cmd:
            return self.draft_email(command_text)

        return (
            f"次の指示はローカル補助として解釈できませんでした: {command_text}\n\n"
            "利用例\n"
            "- デスクトップを整理して\n"
            "- スクリーンショットを OCR\n"
            "- ワークスペースを分析して\n"
            "- TODO を抽出して\n"
            "- メール案を作って"
        )

    def run_smart_task(
        self,
        mode: str,
        text: str = "",
        file_path: str | None = None,
        url: str | None = None,
    ) -> str:
        """モード別の補助処理を実行する。"""
        if mode == "workspace":
            target = Path(file_path) if file_path else Path.cwd()
            return self.analyze_workspace(target)
        if mode == "summary":
            content = self._resolve_text_input(text=text, file_path=file_path, url=url)
            return self.summarize_text(content)
        if mode == "todo":
            content = self._resolve_text_input(text=text, file_path=file_path, url=url)
            return self.extract_action_items(content)
        if mode == "mail":
            content = self._resolve_text_input(text=text, file_path=file_path, url=url)
            return self.draft_email(content)
        if mode == "meeting_report":
            content = self._resolve_text_input(text=text, file_path=file_path, url=url)
            return self.generate_meeting_report(content)
        if mode == "file":
            if not file_path:
                raise ValueError("ファイル分析では対象ファイルを選択してください。")
            return self.analyze_file(file_path)
        if mode == "anomaly":
            if not file_path:
                raise ValueError("異常値検出では CSV または Excel ファイルを選択してください。")
            return self.detect_anomalies(file_path)
        if mode == "ocr_archive":
            if not file_path:
                raise ValueError("OCR 保存では画像ファイルを選択してください。")
            return self.archive_ocr_result(file_path)
        if mode == "web":
            target_url = url or text.strip()
            if not target_url:
                raise ValueError("Web 抽出では URL を入力してください。")
            if not target_url.startswith(("http://", "https://")):
                target_url = "https://" + target_url
            content = self.web_extractor.extract_text(target_url)
            summary = self.summarize_text(content)
            return f"Web 抽出結果\nURL: {target_url}\n\n{summary}"
        if mode == "ideas":
            content = self._resolve_text_input(text=text, file_path=file_path, url=url)
            return self.generate_practical_ideas(content, file_path=file_path)

        raise ValueError("未対応の AI モードです。")

    def analyze_workspace(self, root: Path) -> str:
        """ワークスペース全体の概要を返す。"""
        root = Path(root)
        if not root.exists():
            raise FileNotFoundError(f"対象パスが見つかりません: {root}")

        report = self.file_manager.build_directory_report(str(root))
        lines = [
            "ワークスペース分析",
            f"対象: {report['directory']}",
            f"ファイル数: {report['file_count']}",
            f"フォルダ数: {report['folder_count']}",
            f"総サイズ: {self._format_size(report['total_size'])}",
            "",
            "拡張子トップ",
        ]
        lines.extend(f"- {ext}: {count}" for ext, count in report["extensions"][:8])
        lines.append("")
        lines.append("大きいファイル")
        for item in report["largest_files"][:5]:
            lines.append(f"- {item['path']} ({self._format_size(item['size'])})")
        return "\n".join(lines)

    def summarize_text(self, text: str, max_sentences: int = 4) -> str:
        """テキストを要約する。"""
        normalized = self._normalize_text(text)
        if not normalized:
            raise ValueError("要約対象のテキストが空です。")

        sentences = self._split_sentences(normalized)
        if len(sentences) <= max_sentences:
            return "要約\n\n" + "\n".join(f"- {sentence}" for sentence in sentences)

        keywords = self._keyword_scores(normalized)
        scored_sentences: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            tokens = self._tokenize(sentence)
            if not tokens:
                continue
            score = sum(keywords.get(token, 0.0) for token in tokens) / math.sqrt(len(tokens))
            scored_sentences.append((score, index, sentence))

        top_sentences = sorted(scored_sentences, reverse=True)[:max_sentences]
        ordered = [sentence for _score, _index, sentence in sorted(top_sentences, key=lambda item: item[1])]
        return "要約\n\n" + "\n".join(f"- {sentence}" for sentence in ordered)

    def extract_action_items(self, text: str) -> str:
        """文章から TODO 候補を抽出する。"""
        normalized = self._normalize_text(text)
        if not normalized:
            raise ValueError("TODO を抽出するテキストが空です。")

        sentences = self._split_sentences(normalized)
        action_markers = (
            "する",
            "対応",
            "確認",
            "依頼",
            "提出",
            "作成",
            "修正",
            "共有",
            "review",
            "fix",
            "check",
            "update",
            "send",
        )

        candidates = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(marker in sentence or marker in lowered for marker in action_markers):
                candidates.append(sentence)

        if not candidates:
            candidates = sentences[:5]

        unique_items = []
        seen = set()
        for sentence in candidates:
            item = sentence.strip("- ")
            if item and item not in seen:
                seen.add(item)
                unique_items.append(item)

        lines = ["TODO 抽出", ""]
        for index, item in enumerate(unique_items[:8], start=1):
            lines.append(f"{index}. {item}")
        return "\n".join(lines)

    def draft_email(self, text: str) -> str:
        """入力内容からメール草案を作る。"""
        normalized = self._normalize_text(text)
        if not normalized:
            raise ValueError("メール草案の元になる内容を入力してください。")

        summary = self.summarize_text(normalized, max_sentences=3)
        bullets = [line[2:].strip() for line in summary.splitlines() if line.startswith("- ")]

        lines = [
            "メール草案",
            "",
            "件名: ご連絡",
            "",
            "お世話になっております。",
            "",
            "以下の件につきましてご連絡いたします。",
            "",
        ]
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.extend(
            [
                "",
                "ご確認のほど、よろしくお願いいたします。",
                "",
                "以上、よろしくお願いいたします。",
            ]
        )
        return "\n".join(lines)

    def generate_meeting_report(self, text: str) -> str:
        """議事録から進捗レポートを作る。"""
        normalized = self._normalize_text(text)
        if not normalized:
            raise ValueError("議事録テキストが空です。")

        sentences = self._split_sentences(normalized)
        summary = self.summarize_text(normalized, max_sentences=4)

        progress_keywords = ("進捗", "完了", "開始", "対応", "共有", "作業")
        decision_keywords = ("決定", "採用", "承認", "方針", "結論")
        risk_keywords = ("課題", "懸念", "リスク", "遅延", "問題", "未対応")

        progress = [s for s in sentences if any(k in s for k in progress_keywords)]
        decisions = [s for s in sentences if any(k in s for k in decision_keywords)]
        risks = [s for s in sentences if any(k in s for k in risk_keywords)]
        actions = self.extract_action_items(normalized).splitlines()[2:]

        lines = ["進捗レポート", "", summary, ""]
        lines.append("進捗")
        lines.extend(self._as_bullets(progress[:5], fallback="進捗として抽出できる記述は見つかりませんでした。"))
        lines.append("")
        lines.append("決定事項")
        lines.extend(self._as_bullets(decisions[:5], fallback="明確な決定事項は見つかりませんでした。"))
        lines.append("")
        lines.append("リスク・課題")
        lines.extend(self._as_bullets(risks[:5], fallback="大きなリスク記述は見つかりませんでした。"))
        lines.append("")
        lines.append("次アクション")
        lines.extend(actions or ["1. 次アクションは抽出できませんでした。"])
        return "\n".join(lines)

    def detect_anomalies(self, file_path: str) -> str:
        """CSV / Excel の異常値と品質を確認する。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        dataframe = self._load_table(path)
        if dataframe.empty:
            return "異常値検出\n\n入力データが空です。"

        numeric_columns = [col for col in dataframe.columns if pd.api.types.is_numeric_dtype(dataframe[col])]
        if not numeric_columns:
            return "異常値検出\n\n数値列が見つからないため、異常値を判定できません。"

        lines = [
            "異常値検出",
            f"対象ファイル: {path}",
            f"行数: {len(dataframe)}",
            "",
            "列ごとの結果",
        ]

        for column in numeric_columns[:10]:
            series = dataframe[column].dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                outliers = pd.Series(dtype=series.dtype)
            else:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = series[(series < lower) | (series > upper)]

            lines.append(
                f"- {column}: 平均 {series.mean():.3f}, 最小 {series.min():.3f}, 最大 {series.max():.3f}, "
                f"欠損 {int(dataframe[column].isna().sum())}, 異常候補 {len(outliers)}"
            )
            for index, value in outliers.head(5).items():
                lines.append(f"  行 {index}: {value}")

        lines.append("")
        lines.append(self.check_data_quality(file_path))
        return "\n".join(lines)

    def check_data_quality(self, file_path: str) -> str:
        """データ品質チェック結果を返す。"""
        path = Path(file_path)
        dataframe = self._load_table(path)

        duplicate_count = int(dataframe.duplicated().sum())
        missing_total = int(dataframe.isna().sum().sum())
        column_messages = []
        for column in dataframe.columns[:10]:
            missing = int(dataframe[column].isna().sum())
            ratio = (missing / len(dataframe) * 100) if len(dataframe) else 0
            if missing:
                column_messages.append(f"- {column}: 欠損 {missing} 件 ({ratio:.1f}%)")

        lines = [
            "データ品質チェック",
            f"重複行数: {duplicate_count}",
            f"欠損セル総数: {missing_total}",
        ]
        if column_messages:
            lines.append("欠損の多い列")
            lines.extend(column_messages[:8])
        else:
            lines.append("目立つ欠損は見つかりませんでした。")
        return "\n".join(lines)

    def archive_ocr_result(self, image_path: str) -> str:
        """OCR 結果を整理保存する。"""
        recognizer = InvoiceRecognizer(lang="jpn+eng")
        saved = recognizer.archive_ocr_result(image_path)
        return (
            "OCR 自動保存\n\n"
            f"画像: {saved['image_path']}\n"
            f"全文: {saved['text_path']}\n"
            f"情報 JSON: {saved['json_path']}\n"
            f"保存先フォルダ: {saved['folder']}"
        )

    def generate_practical_ideas(self, text: str, file_path: str | None = None) -> str:
        """実務向けの改善アイデアを提案する。"""
        base_text = self._normalize_text(text)
        source_name = Path(file_path).name if file_path else "現在の入力"

        ideas = [
            "議事録から担当者別 TODO を自動抽出して、そのまま進捗レポートへ反映する",
            "CSV 読み込み時に欠損・重複・異常値・推奨グラフを同時に提案する",
            "OCR 結果から帳票種別を推定し、請求書・領収書・精算書ごとに自動保存する",
            "Web 抽出結果を調査メモ形式と役員向け要約形式の 2 種で出力する",
            "メール草案に添付候補と次アクションを合わせて表示する",
            "プロジェクト全体の大容量ファイルや重複ファイルを定期診断する",
        ]

        if base_text:
            keywords = self._tokenize(base_text)[:8]
            if keywords:
                ideas.insert(0, f"「{', '.join(keywords[:4])}」に関連する専用テンプレートを追加する")

        lines = [f"改善アイデア ({source_name})", ""]
        for index, idea in enumerate(ideas[:8], start=1):
            lines.append(f"{index}. {idea}")
        return "\n".join(lines)

    def analyze_file(self, file_path: str) -> str:
        """ファイルの内容や形式を要約する。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return (
                "ファイル分析\n"
                "種類: 画像\n"
                f"パス: {path}\n"
                f"サイズ: {self._format_size(path.stat().st_size)}\n"
                "この画像は OCR や帳票解析モードでも扱えます。"
            )
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            preview = json.dumps(data, ensure_ascii=False, indent=2)[:1200]
            return (
                "ファイル分析\n"
                "種類: JSON\n"
                f"パス: {path}\n"
                f"サイズ: {self._format_size(path.stat().st_size)}\n\n"
                "プレビュー\n"
                f"{preview}"
            )
        if suffix == ".csv":
            dataframe = pd.read_csv(path)
            return self._summarize_dataframe(path, dataframe)
        if suffix in {".xlsx", ".xls"}:
            dataframe = pd.read_excel(path)
            return self._summarize_dataframe(path, dataframe)
        if suffix in {".txt", ".md", ".py"}:
            content = path.read_text(encoding="utf-8")
            summary = self.summarize_text(content, max_sentences=4)
            return (
                "ファイル分析\n"
                "種類: テキスト\n"
                f"パス: {path}\n"
                f"文字数: {len(content)}\n\n"
                f"{summary}"
            )
        return (
            "ファイル分析\n"
            f"パス: {path}\n"
            f"種類: {suffix or '不明'}\n"
            f"サイズ: {self._format_size(path.stat().st_size)}\n"
            "この形式の詳細分析は簡易表示のみ対応しています。"
        )

    def _summarize_dataframe(self, path: Path, dataframe: pd.DataFrame) -> str:
        """表データの概要を返す。"""
        lines = [
            "ファイル分析",
            "種類: 表データ",
            f"パス: {path}",
            f"行数: {len(dataframe)}",
            f"列数: {len(dataframe.columns)}",
            "",
            "列一覧",
        ]
        for column in dataframe.columns[:10]:
            lines.append(f"- {column}")
        if not dataframe.empty:
            lines.append("")
            lines.append("先頭 5 行")
            lines.append(dataframe.head().to_string(index=False))
        return "\n".join(lines)

    def _organize_desktop(self) -> str:
        """デスクトップを種別ごとに整理する。"""
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            return "デスクトップフォルダが見つかりませんでした。"

        categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
            "Archives": [".zip", ".tar", ".gz", ".7z"],
            "Programs": [".exe", ".msi", ".dmg", ".app"],
        }

        moved_count = 0
        for file in desktop.iterdir():
            if not file.is_file():
                continue
            target_name = "Others"
            for category, extensions in categories.items():
                if file.suffix.lower() in extensions:
                    target_name = category
                    break
            destination = desktop / target_name
            destination.mkdir(exist_ok=True)
            file.rename(destination / file.name)
            moved_count += 1
        return f"デスクトップ整理を完了しました。移動したファイル数: {moved_count}"

    def _screenshot_ocr(self) -> str:
        """スクリーンショット OCR を実行する。"""
        try:
            recognizer = InvoiceRecognizer(lang="jpn+eng")
            text = recognizer.screenshot_ocr()
            preview = text[:500] if text else "文字を抽出できませんでした。"
            return f"スクリーンショット OCR 結果\n\n{preview}"
        except Exception as error:
            return f"スクリーンショット OCR に失敗しました: {error}"

    def _resolve_text_input(self, text: str = "", file_path: str | None = None, url: str | None = None) -> str:
        """入力元に応じてテキストを解決する。"""
        if file_path:
            path = Path(file_path)
            suffix = path.suffix.lower()
            if suffix == ".csv":
                return pd.read_csv(path).to_string(index=False)
            if suffix in {".xlsx", ".xls"}:
                return pd.read_excel(path).to_string(index=False)
            if suffix == ".json":
                return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
            if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
                recognizer = InvoiceRecognizer(lang="jpn+eng")
                return recognizer.image_to_text(str(path))
            return path.read_text(encoding="utf-8")
        if url:
            target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
            return self.web_extractor.extract_text(target_url)
        return text

    def _load_table(self, path: Path) -> pd.DataFrame:
        """CSV / Excel を DataFrame として読み込む。"""
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        raise ValueError("表データとして読み込めるのは CSV / Excel のみです。")

    def _normalize_text(self, text: str) -> str:
        """改行と空白を整える。"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line).strip()

    def _split_sentences(self, text: str) -> list[str]:
        """文単位へ分割する。"""
        prepared = text.replace("\n", "。")
        raw = re.split(r"(?<=[。！？.!?])\s*", prepared)
        sentences = [item.strip() for item in raw if item.strip()]
        return sentences or [text]

    def _tokenize(self, text: str) -> list[str]:
        """簡易トークン抽出を行う。"""
        return re.findall(r"[A-Za-z0-9_\u3041-\u30ff\u4e00-\u9fff]{2,}", text)

    def _keyword_scores(self, text: str) -> dict[str, float]:
        """頻度ベースのキーワード重みを返す。"""
        tokens = [token.lower() for token in self._tokenize(text)]
        counter = Counter(tokens)
        stopwords = {"です", "ます", "した", "して", "こと", "ため", "これ", "それ", "with", "from", "this"}
        return {token: score for token, score in counter.items() if token not in stopwords and len(token) >= 2}

    def _as_bullets(self, items: list[str], fallback: str) -> list[str]:
        """箇条書き形式へ変換する。"""
        if not items:
            return [f"- {fallback}"]
        return [f"- {item}" for item in items]

    def _format_size(self, size: int) -> str:
        """サイズを見やすい単位に変換する。"""
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
