# -*- coding: utf-8 -*-
"""
ファイル管理タブ - 整理・リネーム・検索
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QLabel, QFileDialog, QTextEdit, QMessageBox)
from PySide6.QtCore import Qt
from src.core.file_manager import FileManager


class FileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.file_manager = FileManager()
        self.current_dir = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ディレクトリ選択
        dir_layout = QHBoxLayout()
        self.select_btn = QPushButton("対象ディレクトリ選択")
        self.select_btn.clicked.connect(self.select_directory)
        self.dir_label = QLabel("未選択")
        dir_layout.addWidget(self.select_btn)
        dir_layout.addWidget(self.dir_label)
        layout.addLayout(dir_layout)

        # 機能ボタン
        self.organize_btn = QPushButton("拡張子別に整理")
        self.organize_btn.clicked.connect(self.organize_files)
        layout.addWidget(self.organize_btn)

        # リネーム用
        rename_layout = QHBoxLayout()
        self.rename_pattern = QLineEdit()
        self.rename_pattern.setPlaceholderText("置換前の文字列")
        self.rename_replacement = QLineEdit()
        self.rename_replacement.setPlaceholderText("置換後の文字列")
        self.rename_btn = QPushButton("一括リネーム")
        self.rename_btn.clicked.connect(self.batch_rename)
        rename_layout.addWidget(self.rename_pattern)
        rename_layout.addWidget(self.rename_replacement)
        rename_layout.addWidget(self.rename_btn)
        layout.addLayout(rename_layout)

        # 検索
        search_layout = QHBoxLayout()
        self.search_keyword = QLineEdit()
        self.search_keyword.setPlaceholderText("検索キーワード")
        self.search_btn = QPushButton("内容検索")
        self.search_btn.clicked.connect(self.search_content)
        search_layout.addWidget(self.search_keyword)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # 結果表示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("処理結果が表示されます")
        layout.addWidget(self.result_text)

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "ディレクトリを選択")
        if path:
            self.current_dir = path
            self.dir_label.setText(path)

    def organize_files(self):
        if not self.current_dir:
            QMessageBox.warning(self, "エラー", "ディレクトリを選択してください。")
            return
        msg = self.file_manager.organize_by_extension(self.current_dir)
        self.result_text.append(msg)

    def batch_rename(self):
        if not self.current_dir:
            QMessageBox.warning(self, "エラー", "ディレクトリを選択してください。")
            return
        pattern = self.rename_pattern.text()
        replacement = self.rename_replacement.text()
        if not pattern:
            QMessageBox.warning(self, "エラー", "置換前の文字列を入力してください。")
            return
        msg = self.file_manager.batch_rename(self.current_dir, pattern, replacement)
        self.result_text.append(msg)

    def search_content(self):
        if not self.current_dir:
            QMessageBox.warning(self, "エラー", "ディレクトリを選択してください。")
            return
        keyword = self.search_keyword.text()
        if not keyword:
            QMessageBox.warning(self, "エラー", "検索キーワードを入力してください。")
            return
        results = self.file_manager.search_content(self.current_dir, keyword)
        if results:
            self.result_text.append(f"検索結果 ({len(results)}件):\n" + "\n".join(results))
        else:
            self.result_text.append(f"キーワード「{keyword}」は見つかりませんでした。")