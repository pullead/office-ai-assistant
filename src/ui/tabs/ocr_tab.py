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
            archive_info = None
            if self.mode == "archive":
                archive_info = self.recognizer.archive_ocr_result(self.image_path)

            api_html = None
            api_error = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                prompt = (
                    "以下の OCR 結果を、帳票レビュー向けに整理してください。"
                    "抽出値の妥当性チェック、確認ポイント、次アクションを含めてください。\n\n"
                    f"抽出項目:\n{json.dumps(invoice_info, ensure_ascii=False, indent=2)}\n\n"
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
                    "archive_info": archive_info,
                    "api_html": api_html,
                    "api_error": api_error,
                }
            )
        except Exception as error:
            self.error.emit(str(error))


class OCRTab(BaseTab):
    """OCR と帳票解析を行うタブ。"""

    def __init__(self):
        super().__init__(
            title="OCR 認識",
            subtitle="全文 OCR、請求書/領収書解析、整理保存までを見やすいレポートで表示します。",
            icon="ocr",
        )
        self.ocr_engine = InvoiceRecognizer(lang="jpn+eng")
        self.llm_client = LLMClient()
        self.current_path = None
        self.last_pdf_path = None
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

        self.open_pdf_btn = QPushButton("PDF レポートを開く")
        self.open_pdf_btn.setObjectName("ToolButton")
        self.open_pdf_btn.setEnabled(False)
        self.open_pdf_btn.clicked.connect(self._open_pdf)
        controls_layout.addWidget(self.open_pdf_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)

        info = QLabel("OCR は複数パターンで認識し、帳票解析では請求番号、金額、日付、発行元、宛先を抽出します。")
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
        splitter.setSizes([390, 900])
        self.card_layout.addWidget(splitter, 1)

    def _select_image(self):
        """画像を選択する。"""
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
        """エラーを表示する。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{self._escape_html(message)}</p>")
        self.result_panel.clear_preview()
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)

    def _build_report_html(self, payload: dict) -> str:
        """OCR 結果を HTML レポート化する。"""
        info = payload["invoice_info"] or {}
        validation = info.get("validation") or {}
        checks = validation.get("checks") or []
        layout_info = info.get("layout_info") or {}
        table_regions = layout_info.get("table_regions") or []

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

        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>OCR 解析結果</h2>"
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
            self.archive_btn,
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
