# -*- coding: utf-8 -*-
"""OCR タブ。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
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


class OCRWorker(QThread):
    """OCR 処理用ワーカー。"""

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
            archive_info = None
            if self.mode == "archive":
                archive_info = self.recognizer.archive_ocr_result(self.image_path)

            api_html = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                prompt = (
                    "OCR テキストと抽出項目をもとに、帳票の種類、重要項目、確認ポイント、次アクションを"
                    "見やすい HTML レポートにしてください。\n\n"
                    f"抽出項目:\n{json.dumps(invoice_info, ensure_ascii=False, indent=2)}\n\n"
                    f"OCR 全文:\n{text}"
                )
                api_html = self.llm_client.summarize_to_html("OCR 解析結果", prompt)

            self.finished.emit(
                {
                    "mode": self.mode,
                    "image_path": self.image_path,
                    "text": text,
                    "invoice_info": invoice_info,
                    "archive_info": archive_info,
                    "api_html": api_html,
                }
            )
        except Exception as error:
            self.error.emit(str(error))


class OCRTab(BaseTab):
    """OCR と帳票解析を行うタブ。"""

    def __init__(self):
        super().__init__(
            title="OCR 認識",
            subtitle="画像からの全文 OCR、請求書系の情報抽出、整理保存までを見やすいレポートで表示します。",
            icon="OCR",
        )
        self.ocr_engine = InvoiceRecognizer(lang="jpn+eng")
        self.llm_client = LLMClient()
        self.current_path = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label("画像ファイル"))
        row = QHBoxLayout()
        self.select_btn = QPushButton("画像を選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self._select_image)
        row.addWidget(self.select_btn)

        self.file_label = QLabel("未選択")
        self.file_label.setObjectName("PageSubtitle")
        row.addWidget(self.file_label, 1)
        controls_layout.addLayout(row)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox("OCR 結果を AI API で再分析する")
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton("API 設定")
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        controls_layout.addWidget(make_section_label("実行メニュー"))
        self.ocr_btn = QPushButton("全文 OCR")
        self.ocr_btn.setObjectName("PrimaryButton")
        self.ocr_btn.setMinimumHeight(42)
        self.ocr_btn.clicked.connect(lambda: self._start("text"))
        controls_layout.addWidget(self.ocr_btn)

        self.invoice_btn = QPushButton("請求書 / 領収書 解析")
        self.invoice_btn.setObjectName("SecondaryButton")
        self.invoice_btn.setMinimumHeight(42)
        self.invoice_btn.clicked.connect(lambda: self._start("invoice"))
        controls_layout.addWidget(self.invoice_btn)

        self.archive_btn = QPushButton("OCR 結果を整理保存")
        self.archive_btn.setObjectName("ToolButton")
        self.archive_btn.setMinimumHeight(42)
        self.archive_btn.clicked.connect(lambda: self._start("archive"))
        controls_layout.addWidget(self.archive_btn)

        self.copy_btn = QPushButton("結果をコピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.clicked.connect(self._copy_result)
        controls_layout.addWidget(self.copy_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)

        info = QLabel("帳票解析では、帳票種別、請求番号、金額、日付、発行元などを抽出します。")
        info.setObjectName("InfoPanel")
        info.setWordWrap(True)
        controls_layout.addWidget(info)
        controls_layout.addStretch()

        result_wrapper = QWidget()
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)
        result_layout.addWidget(make_section_label("OCR レポート"))

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([380, 900])
        self.card_layout.addWidget(splitter, 1)

    def _select_image(self):
        """画像ファイルを選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
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
            QMessageBox.warning(self, "入力確認", "先に画像ファイルを選択してください。")
            return

        self._set_buttons(False)
        self.progress_bar.setVisible(True)
        self.worker = OCRWorker(self.ocr_engine, self.llm_client, self.current_path, mode, self.use_api_box.isChecked())
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, payload: dict):
        """処理結果を表示する。"""
        html = payload.get("api_html") or self._build_report_html(payload)
        self.result_panel.set_report_html(html)
        if payload.get("archive_info"):
            archive_info = payload["archive_info"]
            self.result_panel.show_files(
                [
                    archive_info["image_path"],
                    archive_info["text_path"],
                    archive_info["json_path"],
                ]
            )
        else:
            self.result_panel.show_image(payload["image_path"])

    def _on_error(self, message: str):
        """エラー表示を行う。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{message}</p>")
        self.result_panel.clear_preview()

    def _build_report_html(self, payload: dict) -> str:
        """OCR 結果を HTML に整形する。"""
        info = payload["invoice_info"]
        text = self._escape_html(payload["text"]).replace("\n", "<br>")
        archive_html = ""
        if payload.get("archive_info"):
            saved = payload["archive_info"]
            archive_html = (
                "<h3>保存結果</h3>"
                f"<p>保存先: {self._escape_html(saved['folder'])}</p>"
                f"<p>画像: {self._escape_html(saved['image_path'])}</p>"
                f"<p>テキスト: {self._escape_html(saved['text_path'])}</p>"
                f"<p>JSON: {self._escape_html(saved['json_path'])}</p>"
            )

        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>OCR 解析結果</h2>"
            "<div style='display:grid;grid-template-columns:repeat(2,minmax(180px,1fr));gap:12px;'>"
            f"{self._info_card('帳票種別', info.get('document_type') or '未判定')}"
            f"{self._info_card('請求番号', info.get('invoice_no') or '未抽出')}"
            f"{self._info_card('金額', info.get('amount_normalized') or info.get('amount') or '未抽出')}"
            f"{self._info_card('日付', info.get('date') or '未抽出')}"
            f"{self._info_card('発行元', info.get('seller') or '未抽出')}"
            f"{self._info_card('宛先', info.get('buyer') or '未抽出')}"
            "</div>"
            "<h3 style='margin-top:18px;'>確認ポイント</h3>"
            "<ul>"
            "<li>OCR は画像品質の影響を受けます。金額と日付は原本と照合してください。</li>"
            "<li>請求書・領収書・精算書の自動判定結果を右側で確認できます。</li>"
            "</ul>"
            f"{archive_html}"
            "<h3>OCR 全文</h3>"
            f"<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:16px;line-height:1.7;'>{text}</div>"
            "</div>"
        )

    def _info_card(self, title: str, value: str) -> str:
        """小さな情報カードを返す。"""
        return (
            "<div style='background:#ffffff;border:1px solid #e7dcc7;border-radius:16px;padding:14px;'>"
            f"<div style='font-size:12px;color:#64748b;'>{self._escape_html(title)}</div>"
            f"<div style='font-size:16px;font-weight:700;margin-top:6px;'>{self._escape_html(value)}</div>"
            "</div>"
        )

    def _copy_result(self):
        """レポートをコピーする。"""
        text = self.result_panel.summary_browser.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)

    def _set_buttons(self, enabled: bool):
        """ボタン状態を切り替える。"""
        for button in (self.select_btn, self.ocr_btn, self.invoice_btn, self.archive_btn, self.api_settings_btn):
            button.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """実行後に UI を戻す。"""
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
