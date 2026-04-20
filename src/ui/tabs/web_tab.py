# -*- coding: utf-8 -*-
"""Web抽出タブ"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QMessageBox, QProgressBar,
                               QLabel, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.core.web_extractor import WebExtractor


class WebWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, extractor, url, mode):
        super().__init__()
        self.extractor = extractor
        self.url = url
        self.mode = mode

    def run(self):
        try:
            if self.mode == 'text':
                result = self.extractor.extract_text(self.url)
                self.finished.emit(result[:8000] + ("..." if len(result) > 8000 else ""))
            elif self.mode == 'pdf':
                path = self.extractor.save_as_pdf(self.url)
                self.finished.emit(f"✅ PDF保存完了:\n{path}")
            elif self.mode == 'epub':
                path = self.extractor.save_as_epub(self.url)
                self.finished.emit(f"✅ 電子書籍保存完了:\n{path}")
            else:
                self.error.emit("不明なモード")
        except Exception as e:
            self.error.emit(str(e))


class WebTab(BaseTab):
    def __init__(self):
        super().__init__(
            title="Web 抽出",
            subtitle="URLからテキスト・PDF・電子書籍を生成します",
            icon="🌐"
        )
        self.extractor = WebExtractor(output_dir="web_output")
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        cl = self.card_layout

        # ── URL入力 ──
        cl.addWidget(make_section_label("URL を入力"))
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setMinimumHeight(42)
        self.url_input.returnPressed.connect(lambda: self._start('text'))
        url_row.addWidget(self.url_input, 1)
        cl.addLayout(url_row)

        # ── ボタン行 ──
        cl.addWidget(make_section_label("操作"))
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.text_btn = QPushButton("📝  テキスト抽出")
        self.text_btn.setObjectName("PrimaryButton")
        self.text_btn.setMinimumHeight(40)
        self.text_btn.setCursor(Qt.PointingHandCursor)
        self.text_btn.clicked.connect(lambda: self._start('text'))

        self.pdf_btn = QPushButton("📄  PDF保存")
        self.pdf_btn.setObjectName("SecondaryButton")
        self.pdf_btn.setMinimumHeight(40)
        self.pdf_btn.setCursor(Qt.PointingHandCursor)
        self.pdf_btn.clicked.connect(lambda: self._start('pdf'))

        self.epub_btn = QPushButton("📚  電子書籍")
        self.epub_btn.setObjectName("ToolButton")
        self.epub_btn.setMinimumHeight(40)
        self.epub_btn.setCursor(Qt.PointingHandCursor)
        self.epub_btn.clicked.connect(lambda: self._start('epub'))

        self.copy_btn = QPushButton("📋  コピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.setMinimumHeight(40)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_result)

        btn_row.addWidget(self.text_btn)
        btn_row.addWidget(self.pdf_btn)
        btn_row.addWidget(self.epub_btn)
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
        cl.addWidget(make_section_label("抽出結果"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("抽出されたテキストや処理結果が表示されます...")
        self.result_text.setMinimumHeight(280)
        self.result_text.setFont(QFont("Meiryo", 11))
        cl.addWidget(self.result_text, 1)

    def _start(self, mode: str):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "URLを入力してください。")
            return
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_input.setText(url)

        self._set_buttons(False)
        self.progress_bar.setVisible(True)
        self.result_text.clear()

        self.worker = WebWorker(self.extractor, url, mode)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, result: str):
        self.result_text.setPlainText(result)

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "エラー", f"処理失敗:\n{msg}")
        self.result_text.setPlainText(f"❌ エラー: {msg}")

    def _copy_result(self):
        text = self.result_text.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)

    def _reset_ui(self, *args):
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _set_buttons(self, enabled: bool):
        for btn in (self.text_btn, self.pdf_btn, self.epub_btn):
            btn.setEnabled(enabled)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
