# -*- coding: utf-8 -*-
"""OCR タブ。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
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
    """OCR 処理を別スレッドで実行する。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        recognizer: InvoiceRecognizer,
        llm_client: LLMClient,
        input_path: str,
        mode: str,
        use_api: bool,
    ):
        super().__init__()
        self.recognizer = recognizer
        self.llm_client = llm_client
        self.input_path = input_path
        self.mode = mode
        self.use_api = use_api

    def run(self):
        """OCR 本体を実行する。"""
        try:
            text = self.recognizer.image_to_text(self.input_path)
            invoice_info = self.recognizer.extract_invoice_info(self.input_path)
            analysis = self.recognizer.analyze_document(self.input_path)
            archive_info = None
            rpa_export = None

            if self.mode == "archive":
                archive_info = self.recognizer.archive_ocr_result(self.input_path)
            elif self.mode == "rpa":
                rpa_export = self.recognizer.export_rpa_payload(self.input_path)

            api_html = None
            api_error = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                prompt = (
                    "以下の OCR 結果を業務レポートとして整理してください。\n"
                    "抽出フィールド、確認ポイント、RPA に使える要点、注意点を短く分かりやすくまとめてください。\n\n"
                    f"抽出情報:\n{json.dumps(invoice_info, ensure_ascii=False, indent=2)}\n\n"
                    f"分析情報:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}\n\n"
                    f"OCR 原文:\n{text}"
                )
                try:
                    api_html = self.llm_client.summarize_to_html("OCR 分析結果", prompt)
                except Exception as error:  # pragma: no cover
                    api_error = str(error)

            self.finished.emit(
                {
                    "mode": self.mode,
                    "input_path": self.input_path,
                    "text": text,
                    "invoice_info": invoice_info,
                    "analysis": analysis,
                    "archive_info": archive_info,
                    "rpa_export": rpa_export,
                    "api_html": api_html,
                    "api_error": api_error,
                }
            )
        except Exception as error:  # pragma: no cover
            self.error.emit(str(error))


class OCRTab(BaseTab):
    """OCR と帳票解析を扱うタブ。"""

    STRINGS = {
        "ja": {
            "title": "AI-OCR ワークスペース",
            "subtitle": "定型帳票と非定型文書の両方を読み取り、検証・保存・RPA 連携まで一画面で扱います。",
            "header_tag": "帳票 / 非定型 / RPA",
            "image_section": "入力イメージ",
            "select_image": "画像を選択",
            "select_pdf": "PDF を選択",
            "select_image_dialog": "画像ファイルを選択",
            "select_pdf_dialog": "PDF ファイルを選択",
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
            "report_section": "OCR レポート",
            "info_panel": "AI-OCR は複数パターンの文字認識、表領域候補の検出、フィールド検証、RPA 連携用 JSON の生成まで行います。",
            "input_check": "入力確認",
            "need_image": "画像または PDF を選択してください。",
            "error_title": "エラー",
            "copy_done": "結果をクリップボードへコピーしました。",
            "copy_empty": "コピーできる結果がまだありません。",
            "pdf_saved": "PDF レポートを保存しました。",
            "pdf_failed": "PDF レポートの保存に失敗しました。",
            "status_ready": "OCR 準備完了",
            "status_running": "OCR を実行中です...",
            "status_done": "OCR を完了しました。",
            "status_error": "OCR でエラーが発生しました。",
            "summary_title": "OCR 解析結果",
            "preview_placeholder": "ここに詳細プレビューが表示されます。",
            "report_saved": "保存先",
            "report_json": "JSON",
            "report_text": "OCR 全文",
            "report_validation": "確認ポイント",
            "report_automation": "自動化ポイント",
            "report_api_warning": "AI API 追記に失敗しましたが、OCR 本体の結果は表示しています。",
        },
        "en": {
            "title": "AI-OCR Workspace",
            "subtitle": "Read fixed forms and free-form documents in one workspace, then validate, save, and export for RPA.",
            "header_tag": "Forms / Free-form / RPA",
            "image_section": "Input",
            "select_image": "Select Image",
            "select_pdf": "Select PDF",
            "select_image_dialog": "Select an image file",
            "select_pdf_dialog": "Select a PDF file",
            "not_selected": "Not selected",
            "use_api": "Re-analyze OCR results with AI API",
            "api_settings": "API Settings",
            "flow_section": "Flow",
            "full_ocr": "Full OCR",
            "fixed_form": "Analyze Fixed Form",
            "flex_form": "Analyze Free-form",
            "archive": "Archive OCR Result",
            "rpa_export": "Export RPA JSON",
            "copy": "Copy Result",
            "open_pdf": "Open PDF Report",
            "report_section": "OCR Report",
            "info_panel": "AI-OCR handles multiple OCR passes, table-region hints, field validation, and RPA-ready JSON output.",
            "input_check": "Input Check",
            "need_image": "Please select an image or PDF.",
            "error_title": "Error",
            "copy_done": "Copied the result to the clipboard.",
            "copy_empty": "No OCR result to copy yet.",
            "pdf_saved": "Saved the PDF report.",
            "pdf_failed": "Failed to save the PDF report.",
            "status_ready": "OCR ready",
            "status_running": "Running OCR...",
            "status_done": "OCR completed.",
            "status_error": "OCR failed.",
            "summary_title": "OCR Analysis Result",
            "preview_placeholder": "Detailed preview will appear here.",
            "report_saved": "Saved Output",
            "report_json": "JSON",
            "report_text": "OCR Text",
            "report_validation": "Validation",
            "report_automation": "Automation",
            "report_api_warning": "AI API enrichment failed, but the base OCR result is still available.",
        },
        "zh": {
            "title": "AI-OCR 工作台",
            "subtitle": "统一处理定型票据与非定型文档，支持校验、归档和 RPA JSON 导出。",
            "header_tag": "票据 / 非定型 / RPA",
            "image_section": "输入文件",
            "select_image": "选择图片",
            "select_pdf": "选择 PDF",
            "select_image_dialog": "选择图片文件",
            "select_pdf_dialog": "选择 PDF 文件",
            "not_selected": "未选择",
            "use_api": "用 AI API 重新分析 OCR 结果",
            "api_settings": "API 设置",
            "flow_section": "解析流程",
            "full_ocr": "全文 OCR",
            "fixed_form": "解析定型票据",
            "flex_form": "解析非定型文档",
            "archive": "整理保存 OCR 结果",
            "rpa_export": "导出 RPA JSON",
            "copy": "复制结果",
            "open_pdf": "打开 PDF 报告",
            "report_section": "OCR 报告",
            "info_panel": "AI-OCR 支持多轮识别、表格区域候选、字段校验与 RPA 用 JSON 输出。",
            "input_check": "输入检查",
            "need_image": "请选择图片或 PDF。",
            "error_title": "错误",
            "copy_done": "已复制结果到剪贴板。",
            "copy_empty": "暂无可复制结果。",
            "pdf_saved": "已保存 PDF 报告。",
            "pdf_failed": "保存 PDF 报告失败。",
            "status_ready": "OCR 准备完成",
            "status_running": "正在执行 OCR...",
            "status_done": "OCR 已完成。",
            "status_error": "OCR 发生错误。",
            "summary_title": "OCR 分析结果",
            "preview_placeholder": "这里会显示详细预览。",
            "report_saved": "保存输出",
            "report_json": "JSON",
            "report_text": "OCR 全文",
            "report_validation": "校验提示",
            "report_automation": "自动化要点",
            "report_api_warning": "AI API 增强失败，但 OCR 基础结果仍可使用。",
        },
    }

    def __init__(self):
        self.i18n = I18n()
        super().__init__(
            title=self._text("title"),
            subtitle=self._text("subtitle"),
            icon="ocr",
        )
        self.ocr_engine = InvoiceRecognizer(lang="jpn+eng")
        self.llm_client = LLMClient()
        self.current_path: str | None = None
        self.last_pdf_path: str | None = None
        self.last_report_html = ""
        self.last_plain_text = ""
        self.worker: OCRWorker | None = None
        self._setup_content()
        self.set_header_tag(self._text("header_tag"))

    def _setup_content(self):
        """UI を構築する。"""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label(self._text("image_section")))
        row = QHBoxLayout()

        self.select_btn = QPushButton(self._text("select_image"))
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self._select_image)
        row.addWidget(self.select_btn)

        self.select_pdf_btn = QPushButton(self._text("select_pdf"))
        self.select_pdf_btn.setObjectName("ToolButton")
        self.select_pdf_btn.setMinimumHeight(40)
        self.select_pdf_btn.clicked.connect(self._select_pdf)
        row.addWidget(self.select_pdf_btn)

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

        controls_layout.addWidget(make_section_label(self._text("flow_section")))

        self.ocr_btn = self._make_button(self._text("full_ocr"), "PrimaryButton", lambda: self._start("text"))
        self.invoice_btn = self._make_button(self._text("fixed_form"), "SecondaryButton", lambda: self._start("invoice"))
        self.flex_btn = self._make_button(self._text("flex_form"), "SecondaryButton", lambda: self._start("flex"))
        self.archive_btn = self._make_button(self._text("archive"), "ToolButton", lambda: self._start("archive"))
        self.rpa_btn = self._make_button(self._text("rpa_export"), "ToolButton", lambda: self._start("rpa"))
        self.copy_btn = self._make_button(self._text("copy"), "ToolButton", self._copy_result)

        self.open_pdf_btn = self._make_button(self._text("open_pdf"), "ToolButton", self._open_pdf)
        self.open_pdf_btn.setEnabled(False)

        for button in (
            self.ocr_btn,
            self.invoice_btn,
            self.flex_btn,
            self.archive_btn,
            self.rpa_btn,
            self.copy_btn,
            self.open_pdf_btn,
        ):
            controls_layout.addWidget(button)

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
        result_layout.addWidget(make_section_label(self._text("report_section")))

        self.result_panel = RichResultPanel()
        self.result_panel.set_plain_report(self._text("preview_placeholder"))
        self.result_panel.clear_preview()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([400, 920])
        self.card_layout.addWidget(splitter, 1)

    def _make_button(self, text: str, object_name: str, callback) -> QPushButton:
        """共通ボタンを作る。"""
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setMinimumHeight(42)
        button.clicked.connect(callback)
        return button

    def _select_image(self):
        """画像ファイルを選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("select_image_dialog"),
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)",
        )
        if path:
            self.current_path = path
            self.file_label.setText(Path(path).name)
            self.result_panel.show_image(path)

    def _select_pdf(self):
        """PDF ファイルを選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("select_pdf_dialog"),
            "",
            "PDF ファイル (*.pdf)",
        )
        if path:
            self.current_path = path
            self.file_label.setText(Path(path).name)
            self.result_panel.show_files([path])

    def _start(self, mode: str):
        """OCR 処理を開始する。"""
        if not self.current_path:
            QMessageBox.warning(self, self._text("input_check"), self._text("need_image"))
            return

        self._set_buttons(False)
        self.progress_bar.setVisible(True)
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.window().statusBar().showMessage(self._text("status_running"))

        self.worker = OCRWorker(
            self.ocr_engine,
            self.llm_client,
            self.current_path,
            mode,
            self.use_api_box.isChecked(),
        )
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, payload: dict):
        """処理完了時の表示を更新する。"""
        report_html = self._build_report_html(payload)
        if payload.get("api_html"):
            report_html = payload["api_html"] + report_html
        if payload.get("api_error"):
            report_html = self._append_api_warning(report_html, payload["api_error"])

        self.last_report_html = report_html
        self.last_plain_text = payload.get("text", "")
        self.result_panel.set_report_html(report_html)

        path = Path(payload["input_path"])
        if path.suffix.lower() == ".pdf":
            self.result_panel.show_files([str(path)])
        else:
            self.result_panel.show_image(str(path))

        self.last_pdf_path = self._export_pdf_report(payload, report_html)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))
        self.window().statusBar().showMessage(self._text("status_done"))

    def _on_error(self, message: str):
        """エラー時の UI を更新する。"""
        QMessageBox.critical(self, self._text("error_title"), message)
        self.window().statusBar().showMessage(self._text("status_error"))

    def _build_report_html(self, payload: dict) -> str:
        """表示用 HTML を組み立てる。"""
        invoice_info = payload.get("invoice_info") or {}
        analysis = payload.get("analysis") or {}
        validation = invoice_info.get("validation") or {}
        automation_points = analysis.get("automation_points") or []
        archive_info = payload.get("archive_info") or {}
        rpa_export = payload.get("rpa_export") or {}
        full_text = payload.get("text") or ""

        rows = [
            self._table_row("文書種別", invoice_info.get("document_kind") or "-"),
            self._table_row("フォーマット", invoice_info.get("format_type") or "-"),
            self._table_row("帳票タイプ", invoice_info.get("document_type") or "-"),
            self._table_row("番号", invoice_info.get("invoice_no") or "-"),
            self._table_row("金額", invoice_info.get("amount") or "-"),
            self._table_row("日付", invoice_info.get("date") or "-"),
            self._table_row("発行元", invoice_info.get("seller") or "-"),
            self._table_row("宛先", invoice_info.get("buyer") or "-"),
        ]

        validation_items = []
        for key, value in validation.items():
            validation_items.append(f"<li><b>{self._escape_html(str(key))}</b>: {self._escape_html(str(value))}</li>")
        if not validation_items:
            validation_items.append("<li>検証結果はありません。</li>")

        automation_items = [
            f"<li>{self._escape_html(str(item))}</li>"
            for item in automation_points
            if str(item).strip()
        ] or ["<li>自動化ポイントはありません。</li>"]

        export_lines = []
        if archive_info.get("folder"):
            export_lines.append(
                f"<li>{self._escape_html(self._text('report_saved'))}: {self._escape_html(archive_info['folder'])}</li>"
            )
        if archive_info.get("json_path"):
            export_lines.append(
                f"<li>{self._escape_html(self._text('report_json'))}: {self._escape_html(archive_info['json_path'])}</li>"
            )
        if rpa_export.get("json_path"):
            export_lines.append(
                f"<li>RPA JSON: {self._escape_html(rpa_export['json_path'])}</li>"
            )
        if not export_lines:
            export_lines.append("<li>追加の保存ファイルはありません。</li>")

        escaped_text = self._escape_html(full_text)
        return f"""
<div style="font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#17324a;">
  <h2 style="margin:0 0 12px 0;">{self._escape_html(self._text('summary_title'))}</h2>
  <table style="width:100%;border-collapse:collapse;margin-bottom:14px;">
    {''.join(rows)}
  </table>
  <h3 style="margin:16px 0 8px 0;">{self._escape_html(self._text('report_validation'))}</h3>
  <ul style="margin-top:0;">{''.join(validation_items)}</ul>
  <h3 style="margin:16px 0 8px 0;">{self._escape_html(self._text('report_automation'))}</h3>
  <ul style="margin-top:0;">{''.join(automation_items)}</ul>
  <h3 style="margin:16px 0 8px 0;">保存出力</h3>
  <ul style="margin-top:0;">{''.join(export_lines)}</ul>
  <h3 style="margin:16px 0 8px 0;">{self._escape_html(self._text('report_text'))}</h3>
  <pre style="white-space:pre-wrap;line-height:1.65;background:#f8fbff;border:1px solid #d5e6ff;border-radius:12px;padding:12px;">{escaped_text}</pre>
</div>
"""

    def _table_row(self, label: str, value: str) -> str:
        """HTML テーブル行を返す。"""
        return (
            "<tr>"
            f"<th style='text-align:left;padding:8px 10px;border:1px solid #d5e6ff;background:#f8fbff;width:180px;'>{self._escape_html(label)}</th>"
            f"<td style='padding:8px 10px;border:1px solid #d5e6ff;'>{self._escape_html(str(value))}</td>"
            "</tr>"
        )

    def _append_api_warning(self, html: str, message: str) -> str:
        """AI API 失敗時の注意を追記する。"""
        warning_html = (
            "<div style='margin:0 0 12px 0;padding:10px 12px;border-radius:12px;"
            "background:#fff7ed;border:1px solid #fdba74;color:#9a3412;'>"
            f"<b>{self._escape_html(self._text('report_api_warning'))}</b><br>"
            f"{self._escape_html(message)}"
            "</div>"
        )
        return warning_html + html

    def _copy_result(self):
        """現在の結果をコピーする。"""
        text = self.last_plain_text or self.result_panel.summary_browser.toPlainText().strip()
        if not text:
            QMessageBox.information(self, self._text("info_panel"), self._text("copy_empty"))
            return
        QApplication.clipboard().setText(text)
        self.window().statusBar().showMessage(self._text("copy_done"))

    def _set_buttons(self, enabled: bool):
        """実行中はボタンを止める。"""
        for button in (
            self.select_btn,
            self.select_pdf_btn,
            self.api_settings_btn,
            self.ocr_btn,
            self.invoice_btn,
            self.flex_btn,
            self.archive_btn,
            self.rpa_btn,
            self.copy_btn,
        ):
            button.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """UI を復帰させる。"""
        self._set_buttons(True)
        self.progress_bar.setVisible(False)

    def _export_pdf_report(self, payload: dict, html_report: str) -> str | None:
        """HTML レポートを PDF に保存する。"""
        output_dir = Path.cwd() / "output" / "ocr_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(payload["input_path"]).stem
        pdf_path = output_dir / f"{stem}_{timestamp}.pdf"

        try:
            writer = QPdfWriter(str(pdf_path))
            writer.setPageSize(QPageSize(QPageSize.A4))
            document = QTextDocument()
            document.setHtml(html_report)
            document.print_(writer)
            return str(pdf_path)
        except Exception:
            return None

    def _open_pdf(self):
        """保存済み PDF を開く。"""
        if self.last_pdf_path and Path(self.last_pdf_path).exists():
            Path(self.last_pdf_path).resolve()
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl

            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_pdf_path))

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def closeEvent(self, event):
        """終了時にワーカーを停止する。"""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        super().closeEvent(event)

    def _text(self, key: str) -> str:
        """現在言語の文言を返す。"""
        lang = self.i18n.get_current_language()
        return self.STRINGS.get(lang, self.STRINGS["ja"]).get(key, self.STRINGS["ja"].get(key, key))
