# -*- coding: utf-8 -*-
"""
データ可視化タブ - グラフ・ワードクラウド生成
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QFileDialog, QLabel, QMessageBox, QComboBox)
from PySide6.QtCore import Qt
from src.core.visualization import DataVisualizer
import pandas as pd


class VizTab(QWidget):
    def __init__(self):
        super().__init__()
        self.visualizer = DataVisualizer(output_dir="output")
        self.current_file = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ファイル選択
        file_layout = QHBoxLayout()
        self.select_btn = QPushButton("Excel/テキストファイルを選択")
        self.select_btn.clicked.connect(self.select_file)
        self.file_label = QLabel("未選択")
        file_layout.addWidget(self.select_btn)
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        # 機能選択コンボボックス
        self.func_combo = QComboBox()
        self.func_combo.addItems(["Excel → 棒グラフ", "テキスト → ワードクラウド"])
        layout.addWidget(self.func_combo)

        # 実行ボタン
        self.run_btn = QPushButton("生成")
        self.run_btn.clicked.connect(self.generate)
        layout.addWidget(self.run_btn)

        # 結果表示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("生成結果のパスなどが表示されます")
        layout.addWidget(self.result_text)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "ファイルを開く", "",
            "対応ファイル (*.xlsx *.xls *.txt *.csv)"
        )
        if path:
            self.current_file = path
            self.file_label.setText(path.split('/')[-1])

    def generate(self):
        if not self.current_file:
            QMessageBox.warning(self, "エラー", "ファイルを選択してください。")
            return

        func = self.func_combo.currentText()
        try:
            if func == "Excel → 棒グラフ":
                output = self.visualizer.excel_to_chart(self.current_file)
                self.result_text.setText(f"棒グラフを生成しました。\n保存先: {output}")
            else:  # ワードクラウド
                if self.current_file.endswith('.txt'):
                    output = self.visualizer.textfile_to_wordcloud(self.current_file)
                else:
                    # CSVなどもテキストとして読み込む簡易対応
                    df = pd.read_csv(self.current_file)
                    text = " ".join(df.astype(str).values.flatten())
                    output = self.visualizer.generate_wordcloud(text)
                self.result_text.setText(f"ワードクラウドを生成しました。\n保存先: {output}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"生成に失敗しました:\n{str(e)}")