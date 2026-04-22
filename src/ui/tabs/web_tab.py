# -*- coding: utf-8 -*-
"""Web 抽出タブ。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.llm_client import LLMClient
from src.core.web_extractor import WebExtractor
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.ui.widgets.api_settings import show_api_settings_dialog
from src.ui.widgets.rich_result_panel import RichResultPanel


class WebWorker(QThread):
    """Web 抽出処理ワーカー。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, extractor: WebExtractor, llm_client: LLMClient, url: str, mode: str, use_api: bool):
        super().__init__()
        self.extractor = extractor
        self.llm_client = llm_client
        self.url = url
        self.mode = mode
        self.use_api = use_api

    def run(self):
        try:
            text = self.extractor.extract_text(self.url)
            saved_path = None
            if self.mode == "pdf":
                saved_path = self.extractor.save_as_pdf(self.url)
            elif self.mode == "epub":
                saved_path = self.extractor.save_as_epub(self.url)

            api_html = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                api_html = self.llm_client.summarize_to_html(
                    "Web 抽出レポート",
                    f"URL: {self.url}\n\n{text}",
                )

            self.finished.emit(
                {
                    "url": self.url,
                    "mode": self.mode,
                    "text": text,
                    "saved_path": saved_path,
                    "api_html": api_html,
                }
            )
        except Exception as error:
            self.error.emit(str(error))


class WebTab(BaseTab):
    """URL 抽出と要約を行うタブ。"""

    def __init__(self):
        super().__init__(
            title="Web 抽出",
            subtitle="URL から本文を抽出し、AI 要約や保存まで見やすいレポート形式で扱えます。",
            icon="WEB",
        )
        self.extractor = WebExtractor(output_dir="web_output")
        self.llm_client = LLMClient()
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label("URL"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setMinimumHeight(42)
        self.url_input.returnPressed.connect(lambda: self._start("text"))
        controls_layout.addWidget(self.url_input)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox("Web 抽出結果を AI API で整理する")
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton("API 設定")
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        controls_layout.addWidget(make_section_label("実行"))
        self.text_btn = QPushButton("本文を抽出")
        self.text_btn.setObjectName("PrimaryButton")
        self.text_btn.setMinimumHeight(42)
        self.text_btn.clicked.connect(lambda: self._start("text"))
        controls_layout.addWidget(self.text_btn)

        self.pdf_btn = QPushButton("PDF 保存")
        self.pdf_btn.setObjectName("SecondaryButton")
        self.pdf_btn.setMinimumHeight(42)
        self.pdf_btn.clicked.connect(lambda: self._start("pdf"))
        controls_layout.addWidget(self.pdf_btn)

        self.epub_btn = QPushButton("テキスト保存")
        self.epub_btn.setObjectName("ToolButton")
        self.epub_btn.setMinimumHeight(42)
        self.epub_btn.clicked.connect(lambda: self._start("epub"))
        controls_layout.addWidget(self.epub_btn)

        self.copy_btn = QPushButton("結果をコピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.clicked.connect(self._copy_result)
        controls_layout.addWidget(self.copy_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)

        hint = QWidget()
        hint_layout = QVBoxLayout(hint)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.addWidget(make_section_label("ヒント"))
        tip = QPushButton("URL は省略して入力しても自動で https:// を補完します。")
        tip.setObjectName("InfoPanel")
        tip.setEnabled(False)
        hint_layout.addWidget(tip)
        controls_layout.addWidget(hint)
        controls_layout.addStretch()

        result_wrapper = QWidget()
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)
        result_layout.addWidget(make_section_label("抽出レポート"))

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([360, 940])
        self.card_layout.addWidget(splitter, 1)

    def _start(self, mode: str):
        """Web 抽出を開始する。"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "入力確認", "URL を入力してください。")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_input.setText(url)

        self._set_buttons(False)
        self.progress_bar.setVisible(True)
        self.worker = WebWorker(self.extractor, self.llm_client, url, mode, self.use_api_box.isChecked())
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, payload: dict):
        """抽出結果を表示する。"""
        html = payload.get("api_html") or self._build_report_html(payload)
        self.result_panel.set_report_html(html)
        self.result_panel.show_text_preview(payload["text"][:20000])

    def _on_error(self, message: str):
        """エラーを表示する。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{message}</p>")
        self.result_panel.clear_preview()

    def _build_report_html(self, payload: dict) -> str:
        """ローカル抽出結果を HTML 化する。"""
        save_info = ""
        if payload.get("saved_path"):
            save_info = f"<p><b>保存先:</b> {self._escape_html(payload['saved_path'])}</p>"
        preview = self._escape_html(payload["text"][:1200]).replace("\n", "<br>")
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>Web 抽出レポート</h2>"
            f"<p><b>URL:</b> {self._escape_html(payload['url'])}</p>"
            f"<p><b>本文文字数:</b> {len(payload['text'])}</p>"
            f"{save_info}"
            "<h3>プレビュー</h3>"
            f"<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:16px;line-height:1.7;'>{preview}</div>"
            "</div>"
        )

    def _copy_result(self):
        """結果をコピーする。"""
        text = self.result_panel.summary_browser.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)

    def _set_buttons(self, enabled: bool):
        """ボタン状態を切り替える。"""
        for button in (self.text_btn, self.pdf_btn, self.epub_btn, self.api_settings_btn):
            button.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """処理終了後の後始末を行う。"""
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
