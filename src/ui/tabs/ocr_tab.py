# -*- coding: utf-8 -*-
"""
OCRタブ - 画像テキスト変換・請求書認識UI
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTextEdit, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from src.core.ocr_engine import InvoiceRecognizer


class OCRTab(QWidget):
    def __init__(self):
        super().__init__()
        self.ocr_engine = InvoiceRecognizer(lang='jpn+eng')
        self.current_image_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 画像選択エリア
        select_layout = QHBoxLayout()
        self.select_btn = QPushButton("画像を選択")
        self.select_btn.clicked.connect(self.select_image)
        self.image_label = QLabel("未選択")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; min-height: 100px;")
        select_layout.addWidget(self.select_btn)
        select_layout.addWidget(self.image_label)
        layout.addLayout(select_layout)

        # 認識ボタン
        self.ocr_btn = QPushButton("OCR実行 (全テキスト)")
        self.ocr_btn.clicked.connect(self.run_ocr)
        self.invoice_btn = QPushButton("請求書認識 (構造化)")
        self.invoice_btn.clicked.connect(self.run_invoice_recognition)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.ocr_btn)
        btn_layout.addWidget(self.invoice_btn)
        layout.addLayout(btn_layout)

        # 結果表示
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("認識結果がここに表示されます")
        layout.addWidget(self.result_text)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "画像を開く", "", "画像ファイル (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.current_image_path = path
            self.image_label.setText(path.split('/')[-1])

    def run_ocr(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "エラー", "画像を選択してください。")
            return
        text = self.ocr_engine.image_to_text(self.current_image_path)
        self.result_text.setText(text)

    def run_invoice_recognition(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "エラー", "画像を選択してください。")
            return
        info = self.ocr_engine.extract_invoice_info(self.current_image_path)
        output = f"【請求書認識結果】\n"
        output += f"番号: {info.get('invoice_no', '未検出')}\n"
        output += f"金額: {info.get('amount', '未検出')}\n"
        output += f"日付: {info.get('date', '未検出')}\n"
        output += f"売り手: {info.get('seller', '未検出')}\n"
        output += f"\n【全文】\n{info['full_text'][:500]}..."
        self.result_text.setText(output)