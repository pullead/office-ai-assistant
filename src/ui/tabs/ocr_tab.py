# -*- coding: utf-8 -*-
"""OCR タブ。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.llm_client import LLMClient
from src.core.ocr_engine import InvoiceRecognizer
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.ui.widgets.api_settings import show_api_settings_dialog
from src.ui.widgets.rich_result_panel import RichResultPanel
from src.utils.i18n import I18n


class OCRWorker(QThread):
    """OCR 処理ワーカー。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, recognizer: InvoiceRecognizer, llm_client: LLMClient, image_path: str, mode: str, use_api: bool):
        super().__init__()
        self.recognizer = recognizer
        self.llm_client = llm_client
        self.image_path = image_path
        self.mode = mode
        self.use_api = use_api

    def run(self):
        try:
            text = self.recognizer.image_to_text(self.image_path)
            invoice_info = self.recognizer.extract_invoice_info(self.image_path)
            document_analysis = self.recognizer.analyze_document(self.image_path)
            archive_info = None
            rpa_export = None
            if self.mode == "archive":
                archive_info = self.recognizer.archive_ocr_result(self.image_path)
            elif self.mode == "rpa":
                rpa_export = self.recognizer.export_rpa_payload(self.image_path)

            api_html = None
            api_error = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                prompt = (
                    "以下の OCR 結果を、帳票レビュー向けに整理してください。"
                    "抽出値の妥当性チェック、確認ポイント、次アクションを含めてください。\n\n"
                    f"抽出項目:\n{json.dumps(invoice_info, ensure_ascii=False, indent=2)}\n\n"
                    f"文書解析:\n{json.dumps(document_analysis, ensure_ascii=False, indent=2)}\n\n"
                    f"OCR 全文:\n{text}"
                )
                try:
                    api_html = self.llm_client.summarize_to_html("OCR 解析結果", prompt)
                except Exception as error:
                    api_error = str(error)

            self.finished.emit(
                {
                    "mode": self.mode,
                    "image_path": self.image_path,
                    "text": text,
                    "invoice_info": invoice_info,
                    "document_analysis": document_analysis,
                    "archive_info": archive_info,
                    "rpa_export": rpa_export,
                    "api_html": api_html,
                    "api_error": api_error,
                }
            )
        except Exception as error:
            self.error.emit(str(error))


class OCRTab(BaseTab):
    """OCR と帳票解析を行うタブ。"""

    def __init__(self):
        self.i18n = I18n()
        super().__init__(
            title=self._text("title"),
            subtitle=self._text("subtitle"),
            icon="ocr",
        )
        self.ocr_engine = InvoiceRecognizer(lang="jpn+eng")
        self.llm_client = LLMClient()
        self.current_path = None
        self.last_pdf_path = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        self.set_header_tag(self._text("header_tag"))
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        self.image_section_label = make_section_label(self._text("image_section"))
        controls_layout.addWidget(self.image_section_label)
        row = QHBoxLayout()
        self.select_btn = QPushButton(self._text("select_image"))
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self._select_image)
        row.addWidget(self.select_btn)

        self.file_label = QLabel(self._text("not_selected"))
        self.file_label.setObjectName("PageSubtitle")
        row.addWidget(self.file_label, 1)
        controls_layout.addLayout(row)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox(self._text("use_api"))
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton(self._text("api_settings"))
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        self.flow_section_label = make_section_label(self._text("flow_section"))
        controls_layout.addWidget(self.flow_section_label)
        self.ocr_btn = QPushButton(self._text("full_ocr"))
        self.ocr_btn.setObjectName("PrimaryButton")
        self.ocr_btn.setMinimumHeight(42)
        self.ocr_btn.clicked.connect(lambda: self._start("text"))
        controls_layout.addWidget(self.ocr_btn)

        self.invoice_btn = QPushButton(self._text("fixed_form"))
        self.invoice_btn.setObjectName("SecondaryButton")
        self.invoice_btn.setMinimumHeight(42)
        self.invoice_btn.clicked.connect(lambda: self._start("invoice"))
        controls_layout.addWidget(self.invoice_btn)

        self.flex_btn = QPushButton(self._text("flex_form"))
        self.flex_btn.setObjectName("SecondaryButton")
        self.flex_btn.setMinimumHeight(42)
        self.flex_btn.clicked.connect(lambda: self._start("flex"))
        controls_layout.addWidget(self.flex_btn)

        self.archive_btn = QPushButton(self._text("archive"))
        self.archive_btn.setObjectName("ToolButton")
        self.archive_btn.setMinimumHeight(42)
        self.archive_btn.clicked.connect(lambda: self._start("archive"))
        controls_layout.addWidget(self.archive_btn)

        self.rpa_btn = QPushButton(self._text("rpa_export"))
        self.rpa_btn.setObjectName("ToolButton")
        self.rpa_btn.setMinimumHeight(42)
        self.rpa_btn.clicked.connect(lambda: self._start("rpa"))
        controls_layout.addWidget(self.rpa_btn)

        self.copy_btn = QPushButton(self._text("copy"))
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.clicked.connect(self._copy_result)
        controls_layout.addWidget(self.copy_btn)

        self.open_pdf_btn = QPushButton(self._text("open_pdf"))
        self.open_pdf_btn.setObjectName("ToolButton")
        self.open_pdf_btn.setEnabled(False)
        self.open_pdf_btn.clicked.connect(self._open_pdf)
        controls_layout.addWidget(self.open_pdf_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)

        info = QLabel(self._text("info_panel"))
        info.setObjectName("InfoPanel")
        info.setWordWrap(True)
        controls_layout.addWidget(info)
        controls_layout.addStretch()

        result_wrapper = QWidget()
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)
        self.report_section_label = make_section_label(self._text("report_section"))
        result_layout.addWidget(self.report_section_label)

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([390, 900])
        self.card_layout.addWidget(splitter, 1)

    def _select_image(self):
        """画像を選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("select_image_dialog"),
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if path:
            self.current_path = path
            self.file_label.setText(Path(path).name)
            self.result_panel.show_image(path)

    def _start(self, mode: str):
        """OCR 処理を開始する。"""
        if not self.current_path:
            QMessageBox.warning(self, self._text("input_check"), self._text("need_image"))
            return

        self._set_buttons(False)
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.worker = OCRWorker(self.ocr_engine, self.llm_client, self.current_path, mode, self.use_api_box.isChecked())
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, payload: dict):
        """結果を表示する。"""
        html = payload.get("api_html") or self._build_report_html(payload)
        if payload.get("api_error"):
            html = self._append_api_warning(html, payload["api_error"])
        self.result_panel.set_report_html(html)
        self.last_pdf_path = self._export_pdf_report(payload, html)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))

        file_preview_paths = []
        if payload.get("archive_info"):
            archive_info = payload["archive_info"]
            file_preview_paths.extend(
                [archive_info["image_path"], archive_info["text_path"], archive_info["json_path"]]
            )
        if payload.get("rpa_export"):
            file_preview_paths.append(payload["rpa_export"]["json_path"])
        if file_preview_paths:
            self.result_panel.show_files(file_preview_paths)
        else:
            self.result_panel.show_image(payload["image_path"])

    def _on_error(self, message: str):
        """エラーを表示する。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{self._escape_html(message)}</p>")
        self.result_panel.clear_preview()
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)

    def _build_report_html(self, payload: dict) -> str:
        """OCR 結果を HTML レポート化する。"""
        info = payload["invoice_info"] or {}
        document_analysis = payload.get("document_analysis") or {}
        validation = info.get("validation") or {}
        checks = validation.get("checks") or []
        layout_info = info.get("layout_info") or {}
        table_regions = layout_info.get("table_regions") or []
        automation_points = document_analysis.get("automation_points") or []
        key_values = document_analysis.get("key_values") or []

        text = self._escape_html(payload["text"]).replace("\n", "<br>")
        archive_html = ""
        if payload.get("archive_info"):
            saved = payload["archive_info"]
            archive_html = (
                "<h3>保存結果</h3>"
                "<table style='width:100%;border-collapse:collapse;margin-bottom:8px;'>"
                f"{self._table_row('保存先', saved['folder'])}"
                f"{self._table_row('画像', saved['image_path'])}"
                f"{self._table_row('全文テキスト', saved['text_path'])}"
                f"{self._table_row('解析 JSON', saved['json_path'])}"
                "</table>"
            )
        if payload.get("rpa_export"):
            archive_html += (
                "<h3>RPA 連携 JSON</h3>"
                "<table style='width:100%;border-collapse:collapse;margin-bottom:8px;'>"
                f"{self._table_row('JSON 保存先', payload['rpa_export']['json_path'])}"
                "</table>"
            )

        table_region_lines = []
        for index, region in enumerate(table_regions, start=1):
            table_region_lines.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>候補 {index}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>"
                f"x={region.get('x')}, y={region.get('y')}, w={region.get('w')}, h={region.get('h')}, "
                f"行={region.get('line_count')}, 単語={region.get('word_count')}"
                "</td>"
                "</tr>"
            )
        if not table_region_lines:
            table_region_lines.append(
                "<tr><td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>候補</td>"
                "<td style='border:1px solid #e7dcc7;padding:6px;'>検出なし</td></tr>"
            )

        check_lines = []
        for check in checks:
            status = check.get("status", "要確認")
            color = "#065f46" if status == "OK" else "#9a3412"
            check_lines.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(str(check.get('field', '項目')))}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;color:{color};'>{self._escape_html(str(status))}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(str(check.get('message', '')))}</td>"
                "</tr>"
            )
        if not check_lines:
            check_lines.append(
                "<tr><td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>検証</td>"
                "<td style='border:1px solid #e7dcc7;padding:6px;color:#9a3412;'>要確認</td>"
                "<td style='border:1px solid #e7dcc7;padding:6px;'>検証情報がありません。</td></tr>"
            )

        key_value_lines = []
        for row in key_values[:8]:
            key_value_lines.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(row.get('key', ''))}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(row.get('value', ''))}</td>"
                "</tr>"
            )
        if not key_value_lines:
            key_value_lines.append(
                "<tr><td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>項目</td>"
                "<td style='border:1px solid #e7dcc7;padding:6px;'>候補なし</td></tr>"
            )

        automation_html = "".join(
            f"<li>{self._escape_html(point)}</li>" for point in automation_points
        ) or "<li>自動化候補はありません。</li>"

        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>OCR 解析結果</h2>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('帳票形式', document_analysis.get('format_type') or info.get('format_type') or '未判定')}"
            f"{self._table_row('文書カテゴリ', document_analysis.get('document_kind') or info.get('document_kind') or '一般文書')}"
            "</table>"
            "<h3>抽出フィールド</h3>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('帳票種別', info.get('document_type') or '未判定')}"
            f"{self._table_row('請求番号', info.get('invoice_no') or '未抽出')}"
            f"{self._table_row('金額', info.get('amount_normalized') or info.get('amount') or '未抽出')}"
            f"{self._table_row('日付', info.get('date') or '未抽出')}"
            f"{self._table_row('発行元', info.get('seller') or '未抽出')}"
            f"{self._table_row('宛先', info.get('buyer') or '未抽出')}"
            "</table>"
            "<h3>版面検出（表領域候補）</h3>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:8px;'>"
            f"{self._table_row('解析メモ', layout_info.get('note') or '情報なし')}"
            "</table>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:12px;'>"
            + "".join(table_region_lines) +
            "</table>"
            "<h3>フィールド検証</h3>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:8px;'>"
            f"{self._table_row('検証スコア', str(validation.get('score', 'N/A')))}"
            f"{self._table_row('推奨アクション', validation.get('recommendation') or '手動確認してください。')}"
            "</table>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:12px;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>項目</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>状態</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>メッセージ</b></td>"
            "</tr>"
            + "".join(check_lines) +
            "</table>"
            "<h3>非定型文書のキー/値候補</h3>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:12px;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>キー</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>値</b></td>"
            "</tr>"
            + "".join(key_value_lines) +
            "</table>"
            "<h3>RPA 連携ポイント</h3>"
            f"<ul>{automation_html}</ul>"
            f"{archive_html}"
            "<h3>OCR 全文</h3>"
            f"<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:16px;line-height:1.7;'>{text}</div>"
            "</div>"
        )

    def _table_row(self, label: str, value: str) -> str:
        """2列テーブル行を生成する。"""
        return (
            "<tr>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;width:22%;'>{self._escape_html(str(label))}</td>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(str(value))}</td>"
            "</tr>"
        )

    def _append_api_warning(self, html: str, message: str) -> str:
        """API 失敗時の警告を本文へ追記する。"""
        warning = (
            "<div style='margin-bottom:10px;padding:10px 12px;border-radius:10px;"
            "background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;'>"
            "<b>AI API 連携は失敗しました。</b><br>"
            f"{self._escape_html(message)}<br>"
            "ローカル OCR 解析結果でレポートを継続表示しています。"
            "</div>"
        )
        return warning + html

    def _copy_result(self):
        """結果をクリップボードにコピーする。"""
        text = self.result_panel.summary_browser.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)

    def _set_buttons(self, enabled: bool):
        """ボタン状態を切り替える。"""
        for button in (
            self.select_btn,
            self.ocr_btn,
            self.invoice_btn,
            self.flex_btn,
            self.archive_btn,
            self.rpa_btn,
            self.api_settings_btn,
            self.open_pdf_btn,
        ):
            button.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """実行後に UI 状態を戻す。"""
        self._set_buttons(True)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))
        self.progress_bar.setVisible(False)
        self.worker = None

    def _export_pdf_report(self, payload: dict, html_report: str) -> str | None:
        """OCR レポートを PDF へ保存する。"""
        try:
            output_dir = Path("output") / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_path = output_dir / f"ocr_report_{timestamp}.pdf"
            content = (
                "<html><head><meta charset='utf-8'>"
                "<style>"
                "body{font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#1f2937;line-height:1.7;padding:24px;}"
                "h1{font-size:24px;margin-bottom:8px;} .meta{font-size:12px;color:#475569;}"
                ".box{border:1px solid #e7dcc7;border-radius:14px;padding:14px;background:#fffdf8;margin-top:12px;}"
                "</style></head><body>"
                "<h1>OCR PDF レポート</h1>"
                f"<p class='meta'>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} / "
                f"画像: {self._escape_html(payload.get('image_path', ''))}</p>"
                f"<div class='box'>{html_report}</div>"
                "</body></html>"
            )
            writer = QPdfWriter(str(pdf_path))
            writer.setPageSize(QPageSize(QPageSize.A4))
            writer.setResolution(96)
            document = QTextDocument()
            document.setHtml(content)
            document.print_(writer)
            return str(pdf_path)
        except Exception:
            return None

    def _open_pdf(self):
        """最新 PDF を開く。"""
        if not self.last_pdf_path:
            return
        path = Path(self.last_pdf_path)
        if not path.exists():
            return
        import os

        os.startfile(str(path))

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

    def _text(self, key: str) -> str:
        """現在言語向けの文言を返す。"""
        lang = self.i18n.get_current_language()
        texts = {
            "ja": {
                "title": "AI-OCR ワークスペース",
                "subtitle": "定型帳票と非定型文書の両方を読み取り、検証・保存・RPA 連携まで一画面で扱います。",
                "header_tag": "帳票 / 非定型 / RPA",
                "image_section": "入力イメージ",
                "select_image": "画像を選択",
                "not_selected": "未選択",
                "use_api": "OCR 結果を AI API で再分析する",
                "api_settings": "API 設定",
                "flow_section": "解析フロー",
                "full_ocr": "全文 OCR",
                "fixed_form": "定型帳票を解析",
                "flex_form": "非定型文書を解析",
                "archive": "OCR 結果を整理保存",
                "rpa_export": "RPA JSON を出力",
                "copy": "結果をコピー",
                "open_pdf": "PDF レポートを開く",
                "info_panel": "AI-OCR は複数パターンの文字認識、表領域候補の検出、フィールド検証、RPA 連携用 JSON の生成まで行います。",
                "report_section": "OCR レポート",
                "select_image_dialog": "画像を選択",
                "input_check": "入力確認",
                "need_image": "先に画像ファイルを選択してください。",
            },
            "en": {
                "title": "AI OCR Workspace",
                "subtitle": "Read both structured forms and unstructured documents, then validate, archive, and hand off to RPA in one screen.",
                "header_tag": "Forms / Flex / RPA",
                "image_section": "Input Image",
                "select_image": "Select Image",
                "not_selected": "No file selected",
                "use_api": "Enhance OCR results with AI API",
                "api_settings": "API Settings",
                "flow_section": "Processing Flow",
                "full_ocr": "Full OCR",
                "fixed_form": "Analyze Structured Form",
                "flex_form": "Analyze Unstructured Document",
                "archive": "Archive OCR Result",
                "rpa_export": "Export RPA JSON",
                "copy": "Copy Result",
                "open_pdf": "Open PDF Report",
                "info_panel": "AI OCR runs multi-pass recognition, detects table regions, validates fields, and prepares JSON for RPA automation.",
                "report_section": "OCR Report",
                "select_image_dialog": "Select Image",
                "input_check": "Input Check",
                "need_image": "Please select an image first.",
            },
            "zh": {
                "title": "AI-OCR 工作台",
                "subtitle": "同时支持定型单据与非定型文档识别，并在同一界面完成校验、归档和 RPA 交接。",
                "header_tag": "单据 / 非定型 / RPA",
                "image_section": "输入图像",
                "select_image": "选择图片",
                "not_selected": "未选择",
                "use_api": "使用 AI API 深度分析 OCR 结果",
                "api_settings": "API 设置",
                "flow_section": "处理流程",
                "full_ocr": "全文 OCR",
                "fixed_form": "解析定型单据",
                "flex_form": "解析非定型文档",
                "archive": "整理保存 OCR 结果",
                "rpa_export": "导出 RPA JSON",
                "copy": "复制结果",
                "open_pdf": "打开 PDF 报告",
                "info_panel": "AI-OCR 会进行多轮识别、表格区域检测、字段校验，并生成可供 RPA 接管的 JSON 数据。",
                "report_section": "OCR 报告",
                "select_image_dialog": "选择图片",
                "input_check": "输入检查",
                "need_image": "请先选择图片文件。",
            },
        }
        return texts.get(lang, texts["ja"]).get(key, texts["ja"][key])
