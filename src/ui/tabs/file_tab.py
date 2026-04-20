# -*- coding: utf-8 -*-
"""ファイル管理タブ"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QLabel, QFileDialog, QTextEdit,
                               QMessageBox, QProgressBar, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.core.file_manager import FileManager


class FileWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, fm, op, **kwargs):
        super().__init__()
        self.fm = fm
        self.op = op
        self.kwargs = kwargs

    def run(self):
        try:
            if self.op == "organize":
                result = self.fm.organize_by_extension(self.kwargs['directory'])
            elif self.op == "rename":
                result = self.fm.batch_rename(
                    self.kwargs['directory'],
                    self.kwargs['pattern'],
                    self.kwargs['replacement']
                )
            elif self.op == "search":
                hits = self.fm.search_content(
                    self.kwargs['directory'],
                    self.kwargs['keyword']
                )
                result = (
                    f"✅ {len(hits)} 件見つかりました:\n" + "\n".join(hits)
                    if hits else f"「{self.kwargs['keyword']}」は見つかりませんでした。"
                )
            else:
                result = "不明な操作"
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FileTab(BaseTab):
    def __init__(self):
        super().__init__(
            title="ファイル管理",
            subtitle="フォルダの自動整理・一括リネーム・内容検索を行います",
            icon="📁"
        )
        self.fm = FileManager()
        self.current_dir = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        cl = self.card_layout

        # ── フォルダ選択 ──
        cl.addWidget(make_section_label("対象フォルダ"))
        dir_row = QHBoxLayout()
        self.select_btn = QPushButton("📂  フォルダを選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_dir)

        self.dir_label = QLabel("未選択")
        self.dir_label.setObjectName("PageSubtitle")
        self.dir_label.setFont(QFont("Meiryo", 10))

        dir_row.addWidget(self.select_btn)
        dir_row.addWidget(self.dir_label, 1)
        cl.addLayout(dir_row)

        # ── 拡張子別整理 ──
        cl.addWidget(make_section_label("拡張子別に自動整理"))
        self.organize_btn = QPushButton("🗂  整理を実行")
        self.organize_btn.setObjectName("PrimaryButton")
        self.organize_btn.setMinimumHeight(40)
        self.organize_btn.setCursor(Qt.PointingHandCursor)
        self.organize_btn.clicked.connect(self._organize)
        cl.addWidget(self.organize_btn)

        # ── 区切り ──
        div = QFrame()
        div.setObjectName("SidebarDivider")
        div.setFixedHeight(1)
        cl.addWidget(div)

        # ── 一括リネーム ──
        cl.addWidget(make_section_label("一括リネーム（文字列置換）"))
        rename_row = QHBoxLayout()
        rename_row.setSpacing(8)
        self.rename_from = QLineEdit()
        self.rename_from.setPlaceholderText("置換前の文字列")
        self.rename_from.setMinimumHeight(38)
        self.rename_to = QLineEdit()
        self.rename_to.setPlaceholderText("置換後の文字列")
        self.rename_to.setMinimumHeight(38)
        self.rename_btn = QPushButton("✏  リネーム実行")
        self.rename_btn.setObjectName("SecondaryButton")
        self.rename_btn.setMinimumHeight(38)
        self.rename_btn.setCursor(Qt.PointingHandCursor)
        self.rename_btn.clicked.connect(self._rename)
        rename_row.addWidget(self.rename_from, 1)
        rename_row.addWidget(QLabel("→"))
        rename_row.addWidget(self.rename_to, 1)
        rename_row.addWidget(self.rename_btn)
        cl.addLayout(rename_row)

        # ── 区切り ──
        div2 = QFrame()
        div2.setObjectName("SidebarDivider")
        div2.setFixedHeight(1)
        cl.addWidget(div2)

        # ── 内容検索 ──
        cl.addWidget(make_section_label("テキストファイル内容検索"))
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_kw = QLineEdit()
        self.search_kw.setPlaceholderText("検索キーワード")
        self.search_kw.setMinimumHeight(38)
        self.search_kw.returnPressed.connect(self._search)
        self.search_btn = QPushButton("🔍  検索")
        self.search_btn.setObjectName("PrimaryButton")
        self.search_btn.setMinimumHeight(38)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_kw, 1)
        search_row.addWidget(self.search_btn)
        cl.addLayout(search_row)

        # ── プログレスバー ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        cl.addWidget(self.progress_bar)

        # ── 結果 ──
        cl.addWidget(make_section_label("処理結果"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("処理結果がここに表示されます...")
        self.result_text.setMinimumHeight(180)
        self.result_text.setFont(QFont("Meiryo", 11))

        clear_btn = QPushButton("🗑  クリア")
        clear_btn.setObjectName("ToolButton")
        clear_btn.setMinimumHeight(30)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.result_text.clear)

        cl.addWidget(self.result_text, 1)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(clear_btn)
        cl.addLayout(footer)

    def _select_dir(self):
        path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if path:
            self.current_dir = path
            self.dir_label.setText(path)

    def _check_dir(self) -> bool:
        if not self.current_dir:
            QMessageBox.warning(self, "エラー", "対象フォルダを選択してください。")
            return False
        return True

    def _start_worker(self, op: str, **kwargs):
        self._set_buttons(False)
        self.progress_bar.setVisible(True)

        self.worker = FileWorker(self.fm, op, **kwargs)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _organize(self):
        if not self._check_dir():
            return
        reply = QMessageBox.question(
            self, "確認",
            f"以下のフォルダ内のファイルを拡張子別に整理します。\n{self.current_dir}\n\n実行しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._start_worker("organize", directory=self.current_dir)

    def _rename(self):
        if not self._check_dir():
            return
        pattern = self.rename_from.text()
        replacement = self.rename_to.text()
        if not pattern:
            QMessageBox.warning(self, "エラー", "置換前の文字列を入力してください。")
            return
        self._start_worker("rename", directory=self.current_dir,
                           pattern=pattern, replacement=replacement)

    def _search(self):
        if not self._check_dir():
            return
        kw = self.search_kw.text().strip()
        if not kw:
            QMessageBox.warning(self, "エラー", "検索キーワードを入力してください。")
            return
        self._start_worker("search", directory=self.current_dir, keyword=kw)

    def _on_done(self, result: str):
        self.result_text.append(result + "\n")
        self._reset_ui()

    def _on_error(self, msg: str):
        self.result_text.append(f"❌ エラー: {msg}\n")
        self._reset_ui()

    def _reset_ui(self):
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _set_buttons(self, enabled: bool):
        for btn in (self.select_btn, self.organize_btn,
                    self.rename_btn, self.search_btn):
            btn.setEnabled(enabled)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
