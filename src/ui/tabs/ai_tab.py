# -*- coding: utf-8 -*-
"""
AIアシスタントタブ - 自然言語でタスク実行
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QLabel, QMessageBox)
from PySide6.QtCore import Qt
from src.core.ai_assistant import TaskAssistant
from src.core.file_manager import FileManager


class AITab(QWidget):
    def __init__(self):
        super().__init__()
        self.file_manager = FileManager()
        self.assistant = TaskAssistant(file_manager=self.file_manager)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 説明ラベル
        info_label = QLabel("自然言語で指示を入力してください。例：「デスクトップを整理して」「スクリーンショットをOCR」")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 入力エリア
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("コマンドを入力...")
        self.command_input.returnPressed.connect(self.execute_command)
        layout.addWidget(self.command_input)

        # 実行ボタン
        self.run_btn = QPushButton("実行")
        self.run_btn.clicked.connect(self.execute_command)
        layout.addWidget(self.run_btn)

        # 出力エリア
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("実行結果がここに表示されます")
        layout.addWidget(self.output_text)

        # クリアボタン
        clear_btn = QPushButton("クリア")
        clear_btn.clicked.connect(self.output_text.clear)
        layout.addWidget(clear_btn)

    def execute_command(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            QMessageBox.warning(self, "エラー", "コマンドを入力してください。")
            return
        self.output_text.append(f">>> {cmd}")
        result = self.assistant.execute_command(cmd)
        self.output_text.append(result)
        self.output_text.append("")
        self.command_input.clear()