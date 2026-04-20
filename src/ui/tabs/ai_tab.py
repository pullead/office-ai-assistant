# -*- coding: utf-8 -*-
"""AIアシスタントタブ"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QLabel, QProgressBar,
                               QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.core.ai_assistant import TaskAssistant
from src.core.file_manager import FileManager


class AIWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, assistant, command):
        super().__init__()
        self.assistant = assistant
        self.command = command

    def run(self):
        try:
            result = self.assistant.execute_command(self.command)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AITab(BaseTab):
    def __init__(self):
        super().__init__(
            title="AI アシスタント",
            subtitle="自然言語で指示を入力するとタスクを自動実行します",
            icon="🤖"
        )
        self.file_manager = FileManager()
        self.assistant = TaskAssistant(file_manager=self.file_manager)
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        cl = self.card_layout

        # ── ヒントラベル ──
        hint = QLabel("💡  例：「デスクトップを整理して」「スクリーンショットをOCR」「ファイルを検索」")
        hint.setObjectName("PageSubtitle")
        hint.setWordWrap(True)
        hint.setFont(QFont("Meiryo", 10))
        cl.addWidget(hint)

        # ── 入力エリア ──
        cl.addWidget(make_section_label("コマンドを入力"))
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("例：デスクトップを整理して")
        self.command_input.setMinimumHeight(42)
        self.command_input.returnPressed.connect(self.execute_command)
        input_row.addWidget(self.command_input, 1)

        self.run_btn = QPushButton("▶  実行")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(42)
        self.run_btn.setMinimumWidth(100)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.execute_command)
        input_row.addWidget(self.run_btn)

        cl.addLayout(input_row)

        # ── プログレスバー ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        cl.addWidget(self.progress_bar)

        # ── 出力エリア ──
        cl.addWidget(make_section_label("実行ログ"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("実行結果がここに表示されます...")
        self.output_text.setMinimumHeight(300)
        self.output_text.setFont(QFont("Consolas", 11))
        cl.addWidget(self.output_text, 1)

        # ── フッターボタン ──
        footer = QHBoxLayout()
        footer.addStretch()
        clear_btn = QPushButton("🗑  ログをクリア")
        clear_btn.setObjectName("ToolButton")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.output_text.clear)
        footer.addWidget(clear_btn)
        cl.addLayout(footer)

    def execute_command(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            return

        self.output_text.append(f"<span style='color:#64748b'>>>> </span>"
                                 f"<b>{cmd}</b>")
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = AIWorker(self.assistant, cmd)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, result):
        self.output_text.append(f"<span style='color:#059669'>{result}</span><br>")
        self.command_input.clear()
        self._reset_ui()

    def _on_error(self, msg):
        self.output_text.append(f"<span style='color:#dc2626'>エラー: {msg}</span><br>")
        self._reset_ui()

    def _reset_ui(self):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
