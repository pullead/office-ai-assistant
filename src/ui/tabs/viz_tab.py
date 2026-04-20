# -*- coding: utf-8 -*-
"""データ可視化タブ"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QFileDialog, QLabel, QMessageBox,
                               QComboBox, QProgressBar, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.core.visualization import DataVisualizer
import pandas as pd
import os


class VizWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, visualizer, func, file_path):
        super().__init__()
        self.viz = visualizer
        self.func = func
        self.file_path = file_path

    def run(self):
        try:
            if self.func == "excel_chart":
                output = self.viz.excel_to_chart(self.file_path)
            elif self.func == "wordcloud_from_text":
                output = self.viz.textfile_to_wordcloud(self.file_path)
            elif self.func == "wordcloud_from_csv":
                df = pd.read_csv(self.file_path)
                text = " ".join(df.astype(str).values.flatten())
                output = self.viz.generate_wordcloud(text)
            elif self.func == "line_chart":
                output = self.viz.excel_to_line_chart(self.file_path)
            elif self.func == "pie_chart":
                output = self.viz.excel_to_pie_chart(self.file_path)
            else:
                output = "不明な機能"
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))


class VizTab(BaseTab):
    def __init__(self):
        super().__init__(
            title="データ可視化",
            subtitle="Excel・テキストファイルからグラフ・ワードクラウドを生成します",
            icon="📊"
        )
        self.visualizer = DataVisualizer(output_dir="output")
        self.current_file = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        cl = self.card_layout

        # ── ファイル選択 ──
        cl.addWidget(make_section_label("入力ファイル"))
        file_row = QHBoxLayout()
        self.select_btn = QPushButton("📂  ファイルを選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_file)
        self.file_label = QLabel("未選択")
        self.file_label.setObjectName("PageSubtitle")
        file_row.addWidget(self.select_btn)
        file_row.addWidget(self.file_label, 1)
        cl.addLayout(file_row)

        # ── チャート種別 ──
        cl.addWidget(make_section_label("グラフの種類"))
        self.func_combo = QComboBox()
        self.func_combo.setMinimumHeight(40)
        self.func_combo.addItems([
            "📊  Excel → 棒グラフ",
            "📈  Excel → 折れ線グラフ",
            "🥧  Excel → 円グラフ",
            "☁  テキスト → ワードクラウド",
        ])
        cl.addWidget(self.func_combo)

        # ── 実行ボタン ──
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("▶  生成する")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(42)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._generate)

        self.open_btn = QPushButton("🖼  出力を開く")
        self.open_btn.setObjectName("ToolButton")
        self.open_btn.setMinimumHeight(42)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output)

        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.open_btn)
        cl.addLayout(btn_row)

        # ── プログレスバー ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        cl.addWidget(self.progress_bar)

        # ── ログ ──
        cl.addWidget(make_section_label("処理ログ"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("処理結果のパスなどが表示されます...")
        self.result_text.setMinimumHeight(180)
        self.result_text.setFont(QFont("Meiryo", 11))
        cl.addWidget(self.result_text, 1)

        self.last_output = None

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "ファイルを選択", "",
            "対応ファイル (*.xlsx *.xls *.txt *.csv)"
        )
        if path:
            self.current_file = path
            self.file_label.setText(path.split('/')[-1].split('\\')[-1])

    def _generate(self):
        if not self.current_file:
            QMessageBox.warning(self, "エラー", "ファイルを選択してください。")
            return

        text = self.func_combo.currentText()
        if "棒グラフ" in text:
            func = "excel_chart"
        elif "折れ線" in text:
            func = "line_chart"
        elif "円グラフ" in text:
            func = "pie_chart"
        else:
            func = ("wordcloud_from_text" if self.current_file.endswith('.txt')
                    else "wordcloud_from_csv")

        self.run_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.result_text.append("⏳ 処理中...")

        self.worker = VizWorker(self.visualizer, func, self.current_file)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, path: str):
        self.last_output = path
        self.result_text.append(f"✅ 生成完了:\n   {path}\n")
        self.open_btn.setEnabled(True)
        self._reset_ui()

    def _on_error(self, msg: str):
        self.result_text.append(f"❌ エラー: {msg}\n")
        self._reset_ui()

    def _open_output(self):
        if self.last_output and os.path.exists(self.last_output):
            os.startfile(self.last_output)

    def _reset_ui(self):
        self.run_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
