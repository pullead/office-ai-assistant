# -*- coding: utf-8 -*-
"""OCRタブ - 画像テキスト変換・請求書認識"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTextEdit, QFileDialog, QMessageBox,
                               QProgressBar, QFrame, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.core.ocr_engine import InvoiceRecognizer


class OCRWorker(QThread):
    text_done = Signal(str)
    invoice_done = Signal(dict)
    error = Signal(str)

    def __init__(self, ocr, path, mode):
        super().__init__()
        self.ocr = ocr
        self.path = path
        self.mode = mode

    def run(self):
        try:
            if self.mode == "text":
                self.text_done.emit(self.ocr.image_to_text(self.path))
            else:
                self.invoice_done.emit(self.ocr.extract_invoice_info(self.path))
        except Exception as e:
            self.error.emit(str(e))


class DropZoneLabel(QLabel):
    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(130)
        self.setWordWrap(True)
        self._set_idle()

    def _set_idle(self):
        self.setText("📁\n\nここに画像をドロップ\n.png / .jpg / .jpeg / .bmp")
        self.setFont(QFont("Meiryo", 11))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setObjectName("DropZoneActive")
            self._refresh_style()

    def dragLeaveEvent(self, e):
        self.setObjectName("DropZone")
        self._refresh_style()

    def dropEvent(self, e):
        self.setObjectName("DropZone")
        self._refresh_style()
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
                self.fileDropped.emit(path)
            else:
                QMessageBox.warning(self.parent(), "形式エラー",
                                    "対応形式: png / jpg / jpeg / bmp / tif")

    def set_done(self, name: str):
        self.setObjectName("DropZoneDone")
        self.setText(f"✅  {name}")
        self._refresh_style()

    def _refresh_style(self):
        self.style().unpolish(self)
        self.style().polish(self)


class OCRTab(BaseTab):
    def __init__(self):
        super().__init__(
            title="OCR 認識",
            subtitle="画像からテキストを抽出・請求書を自動解析します",
            icon="📄"
        )
        self.ocr_engine = InvoiceRecognizer(lang='jpn+eng')
        self.current_path = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        cl = self.card_layout

        # ── ドロップゾーン ──
        self.drop_zone = DropZoneLabel(self)
        self.drop_zone.fileDropped.connect(self._set_image)
        cl.addWidget(self.drop_zone)

        # ── ファイル選択行 ──
        row = QHBoxLayout()
        self.select_btn = QPushButton("📂  画像を選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(38)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_image)
        row.addWidget(self.select_btn)

        self.file_label = QLabel("未選択")
        self.file_label.setObjectName("PageSubtitle")
        self.file_label.setFont(QFont("Meiryo", 10))
        row.addWidget(self.file_label, 1)
        cl.addLayout(row)

        # ── 実行ボタン ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.ocr_btn = QPushButton("🔍  OCR（全テキスト）")
        self.ocr_btn.setObjectName("PrimaryButton")
        self.ocr_btn.setMinimumHeight(40)
        self.ocr_btn.setCursor(Qt.PointingHandCursor)
        self.ocr_btn.clicked.connect(lambda: self._start("text"))

        self.invoice_btn = QPushButton("🧾  請求書認識（構造化）")
        self.invoice_btn.setObjectName("SecondaryButton")
        self.invoice_btn.setMinimumHeight(40)
        self.invoice_btn.setCursor(Qt.PointingHandCursor)
        self.invoice_btn.clicked.connect(lambda: self._start("invoice"))

        self.copy_btn = QPushButton("📋  結果をコピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.setMinimumHeight(40)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_result)

        btn_row.addWidget(self.ocr_btn)
        btn_row.addWidget(self.invoice_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.copy_btn)
        cl.addLayout(btn_row)

        # ── プログレスバー ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        cl.addWidget(self.progress_bar)

        # ── 結果 ──
        cl.addWidget(make_section_label("認識結果"))
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("認識結果がここに表示されます...")
        self.result_text.setMinimumHeight(240)
        self.result_text.setFont(QFont("Meiryo", 11))
        cl.addWidget(self.result_text, 1)

    def _set_image(self, path: str):
        self.current_path = path
        name = path.split('/')[-1].split('\\')[-1]
        self.file_label.setText(name)
        self.drop_zone.set_done(name)

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "画像を選択", "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if path:
            self._set_image(path)

    def _start(self, mode: str):
        if not self.current_path:
            QMessageBox.warning(self, "エラー", "まず画像を選択してください。")
            return

        self._set_buttons(False)
        self.progress_bar.setVisible(True)
        self.result_text.clear()

        self.worker = OCRWorker(self.ocr_engine, self.current_path, mode)
        self.worker.text_done.connect(self._on_text)
        self.worker.invoice_done.connect(self._on_invoice)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.start()

    def _on_text(self, text: str):
        self.result_text.setPlainText(text)

    def _on_invoice(self, info: dict):
        lines = [
            "【請求書認識結果】",
            f"番号  : {info.get('invoice_no') or '未検出'}",
            f"金額  : {info.get('amount') or '未検出'}",
            f"日付  : {info.get('date') or '未検出'}",
            f"発行者: {info.get('seller') or '未検出'}",
            "",
            "【全文（先頭500文字）】",
            (info.get('full_text') or '')[:500],
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "エラー", f"OCR処理に失敗しました:\n{msg}")
        self.result_text.setPlainText(f"エラー: {msg}")

    def _copy_result(self):
        text = self.result_text.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)

    def _reset_ui(self):
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _set_buttons(self, enabled: bool):
        for btn in (self.ocr_btn, self.invoice_btn, self.select_btn):
            btn.setEnabled(enabled)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
