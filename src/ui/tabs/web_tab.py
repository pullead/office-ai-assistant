# -*- coding: utf-8 -*-
"""
Web抽出タブ - URLからテキスト抽出・PDF保存
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QLabel, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from src.core.web_extractor import WebExtractor


class WebTab(QWidget):
    def __init__(self):
        super().__init__()
        self.extractor = WebExtractor(output_dir="web_output")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # URL入力
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # 機能ボタン
        btn_layout = QHBoxLayout()
        self.text_btn = QPushButton("テキスト抽出")
        self.text_btn.clicked.connect(self.extract_text)
        self.pdf_btn = QPushButton("PDF保存")
        self.pdf_btn.clicked.connect(self.save_pdf)
        self.epub_btn = QPushButton("電子書籍保存（テキスト）")
        self.epub_btn.clicked.connect(self.save_epub)
        btn_layout.addWidget(self.text_btn)
        btn_layout.addWidget(self.pdf_btn)
        btn_layout.addWidget(self.epub_btn)
        layout.addLayout(btn_layout)

        # 結果表示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("抽出されたテキストや処理結果が表示されます")
        layout.addWidget(self.result_text)

    def extract_text(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "URLを入力してください。")
            return
        try:
            text = self.extractor.extract_text(url)
            self.result_text.setText(text[:5000] + ("..." if len(text) > 5000 else ""))
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"抽出失敗:\n{str(e)}")

    def save_pdf(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "URLを入力してください。")
            return
        try:
            out = self.extractor.save_as_pdf(url)
            self.result_text.setText(f"PDF保存完了: {out}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"PDF保存失敗:\n{str(e)}")

    def save_epub(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "URLを入力してください。")
            return
        try:
            out = self.extractor.save_as_epub(url)
            self.result_text.setText(f"電子書籍保存完了: {out}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存失敗:\n{str(e)}")