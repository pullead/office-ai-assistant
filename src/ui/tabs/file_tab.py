# -*- coding: utf-8 -*-
"""ファイル整理タブ。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.file_manager import FileManager
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.ui.widgets.rich_result_panel import RichResultPanel


class FileWorker(QThread):
    """ファイル管理処理ワーカー。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, manager: FileManager, operation: str, **kwargs):
        super().__init__()
        self.manager = manager
        self.operation = operation
        self.kwargs = kwargs

    def run(self):
        try:
            directory = self.kwargs["directory"]
            if self.operation == "organize":
                text = self.manager.organize_by_extension(directory)
                preview_files = [str(path) for path in Path(directory).rglob("*") if path.is_file()][:120]
                payload = {"title": "拡張子整理", "text": text, "files": preview_files}
            elif self.operation == "rename":
                text = self.manager.batch_rename(directory, self.kwargs["pattern"], self.kwargs["replacement"])
                payload = {"title": "一括リネーム", "text": text, "files": []}
            elif self.operation == "search_content":
                hits = self.manager.search_content(directory, self.kwargs["keyword"])
                payload = {
                    "title": "内容検索",
                    "text": f"{len(hits)} 件見つかりました。",
                    "files": hits,
                }
            elif self.operation == "search_name":
                hits = self.manager.search_files_by_name(directory, self.kwargs["keyword"])
                payload = {
                    "title": "ファイル名検索",
                    "text": f"{len(hits)} 件見つかりました。",
                    "files": hits,
                }
            elif self.operation == "summary":
                report = self.manager.build_directory_report(directory)
                payload = {"title": "フォルダサマリー", "report": report, "files": [item["path"] for item in report["largest_files"]]}
            elif self.operation == "duplicate":
                text = self.manager.find_duplicate_files(directory)
                payload = {"title": "重複ファイル検出", "text": text, "files": []}
            else:
                raise ValueError("未対応の処理です。")
            self.finished.emit(payload)
        except Exception as error:
            self.error.emit(str(error))


class FileTab(BaseTab):
    """ファイル整理、検索、可視化表示を行うタブ。"""

    def __init__(self):
        super().__init__(
            title="ファイル整理",
            subtitle="整理、検索、重複検出、フォルダ全体の可視化サマリーまでを大きなレポートで確認できます。",
            icon="FILE",
        )
        self.file_manager = FileManager()
        self.current_dir = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label("対象フォルダ"))
        dir_row = QHBoxLayout()
        self.select_btn = QPushButton("フォルダを選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self._select_dir)
        dir_row.addWidget(self.select_btn)

        self.pc_btn = QPushButton("この PC ルート")
        self.pc_btn.setObjectName("ToolButton")
        self.pc_btn.setMinimumHeight(40)
        self.pc_btn.clicked.connect(self._set_pc_root)
        dir_row.addWidget(self.pc_btn)
        controls_layout.addLayout(dir_row)

        self.dir_label = QLabel("未選択")
        self.dir_label.setObjectName("PageSubtitle")
        self.dir_label.setWordWrap(True)
        controls_layout.addWidget(self.dir_label)

        controls_layout.addWidget(make_section_label("分析と整理"))
        self.summary_btn = QPushButton("フォルダ分析")
        self.summary_btn.setObjectName("PrimaryButton")
        self.summary_btn.setMinimumHeight(42)
        self.summary_btn.clicked.connect(lambda: self._start_simple("summary"))
        controls_layout.addWidget(self.summary_btn)

        self.organize_btn = QPushButton("拡張子ごとに整理")
        self.organize_btn.setObjectName("SecondaryButton")
        self.organize_btn.setMinimumHeight(42)
        self.organize_btn.clicked.connect(self._organize)
        controls_layout.addWidget(self.organize_btn)

        self.duplicate_btn = QPushButton("重複ファイルを検出")
        self.duplicate_btn.setObjectName("ToolButton")
        self.duplicate_btn.setMinimumHeight(42)
        self.duplicate_btn.clicked.connect(lambda: self._start_simple("duplicate"))
        controls_layout.addWidget(self.duplicate_btn)

        controls_layout.addWidget(make_section_label("一括リネーム"))
        rename_row = QHBoxLayout()
        self.rename_from = QLineEdit()
        self.rename_from.setPlaceholderText("置換前")
        rename_row.addWidget(self.rename_from)
        self.rename_to = QLineEdit()
        self.rename_to.setPlaceholderText("置換後")
        rename_row.addWidget(self.rename_to)
        controls_layout.addLayout(rename_row)

        self.rename_btn = QPushButton("リネーム実行")
        self.rename_btn.setObjectName("SecondaryButton")
        self.rename_btn.setMinimumHeight(40)
        self.rename_btn.clicked.connect(self._rename)
        controls_layout.addWidget(self.rename_btn)

        controls_layout.addWidget(make_section_label("検索"))
        self.search_kw = QLineEdit()
        self.search_kw.setPlaceholderText("検索キーワード")
        self.search_kw.returnPressed.connect(self._search_name)
        controls_layout.addWidget(self.search_kw)

        search_row = QHBoxLayout()
        self.search_name_btn = QPushButton("ファイル名検索")
        self.search_name_btn.setObjectName("PrimaryButton")
        self.search_name_btn.clicked.connect(self._search_name)
        search_row.addWidget(self.search_name_btn)

        self.search_content_btn = QPushButton("内容検索")
        self.search_content_btn.setObjectName("ToolButton")
        self.search_content_btn.clicked.connect(self._search_content)
        search_row.addWidget(self.search_content_btn)
        controls_layout.addLayout(search_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)
        controls_layout.addStretch()

        result_wrapper = QWidget()
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)
        result_layout.addWidget(make_section_label("ファイル管理レポート"))

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([380, 920])
        self.card_layout.addWidget(splitter, 1)

    def _select_dir(self):
        """対象フォルダを選択する。"""
        path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if path:
            self.current_dir = path
            self.dir_label.setText(path)

    def _set_pc_root(self):
        """PC 全体検索向けのルートを設定する。"""
        root = str(Path.home().anchor or "C:\\")
        self.current_dir = root
        self.dir_label.setText(root)

    def _check_dir(self) -> bool:
        """対象フォルダの有無を確認する。"""
        if not self.current_dir:
            QMessageBox.warning(self, "入力確認", "先に対象フォルダを選択してください。")
            return False
        return True

    def _start_worker(self, operation: str, **kwargs):
        """ワーカーを起動する。"""
        self._set_buttons(False)
        self.progress_bar.setVisible(True)

        self.worker = FileWorker(self.file_manager, operation, **kwargs)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _start_simple(self, operation: str):
        """フォルダのみで実行できる処理を開始する。"""
        if not self._check_dir():
            return
        self._start_worker(operation, directory=self.current_dir)

    def _organize(self):
        """整理処理を確認付きで実行する。"""
        if not self._check_dir():
            return
        reply = QMessageBox.question(
            self,
            "確認",
            f"次のフォルダを拡張子ごとに整理します。\n{self.current_dir}\n\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._start_worker("organize", directory=self.current_dir)

    def _rename(self):
        """一括リネームを実行する。"""
        if not self._check_dir():
            return
        pattern = self.rename_from.text().strip()
        replacement = self.rename_to.text()
        if not pattern:
            QMessageBox.warning(self, "入力確認", "置換前の文字列を入力してください。")
            return
        self._start_worker("rename", directory=self.current_dir, pattern=pattern, replacement=replacement)

    def _search_name(self):
        """ファイル名検索を行う。"""
        if not self._check_dir():
            return
        keyword = self.search_kw.text().strip()
        if not keyword:
            QMessageBox.warning(self, "入力確認", "検索キーワードを入力してください。")
            return
        self._start_worker("search_name", directory=self.current_dir, keyword=keyword)

    def _search_content(self):
        """内容検索を行う。"""
        if not self._check_dir():
            return
        keyword = self.search_kw.text().strip()
        if not keyword:
            QMessageBox.warning(self, "入力確認", "検索キーワードを入力してください。")
            return
        self._start_worker("search_content", directory=self.current_dir, keyword=keyword)

    def _on_done(self, payload: dict):
        """結果表示を更新する。"""
        if "report" in payload:
            report = payload["report"]
            self.result_panel.set_report_html(self._build_report_html(report))
            self.result_panel.show_files(report["tree_preview"])
            return

        body = self._escape_html(payload["text"]).replace("\n", "<br>")
        self.result_panel.set_report_html(
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            f"<h2>{self._escape_html(payload['title'])}</h2>"
            "<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:18px;'>"
            f"{body}</div></div>"
        )
        if payload.get("files"):
            self.result_panel.show_files(payload["files"])
        else:
            self.result_panel.show_text_preview(payload["text"])

    def _on_error(self, message: str):
        """エラーを表示する。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{message}</p>")
        self.result_panel.clear_preview()

    def _build_report_html(self, report: dict) -> str:
        """フォルダ分析結果を HTML に整形する。"""
        ext_items = "".join(f"<li>{self._escape_html(ext)}: {count}</li>" for ext, count in report["extensions"])
        folder_items = "".join(
            f"<li>{self._escape_html(item['name'])} | {item['files']} 件 | {self._format_size(item['size'])}</li>"
            for item in report["top_folders"][:8]
        )
        file_items = "".join(
            f"<li>{self._escape_html(item['path'])} | {self._format_size(item['size'])}</li>"
            for item in report["largest_files"][:8]
        )
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>フォルダ分析レポート</h2>"
            "<div style='display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:12px;'>"
            f"{self._metric_card('ファイル数', str(report['file_count']))}"
            f"{self._metric_card('フォルダ数', str(report['folder_count']))}"
            f"{self._metric_card('総サイズ', self._format_size(report['total_size']))}"
            "</div>"
            "<h3 style='margin-top:18px;'>拡張子構成</h3>"
            f"<ul>{ext_items}</ul>"
            "<h3>上位フォルダ</h3>"
            f"<ul>{folder_items}</ul>"
            "<h3>大きいファイル</h3>"
            f"<ul>{file_items}</ul>"
            "</div>"
        )

    def _metric_card(self, title: str, value: str) -> str:
        """メトリクスカードを返す。"""
        return (
            "<div style='background:#ffffff;border:1px solid #e7dcc7;border-radius:16px;padding:14px;'>"
            f"<div style='font-size:12px;color:#64748b;'>{self._escape_html(title)}</div>"
            f"<div style='font-size:18px;font-weight:700;margin-top:4px;'>{self._escape_html(value)}</div>"
            "</div>"
        )

    def _set_buttons(self, enabled: bool):
        """ボタン状態を切り替える。"""
        for button in (
            self.select_btn,
            self.pc_btn,
            self.summary_btn,
            self.organize_btn,
            self.duplicate_btn,
            self.rename_btn,
            self.search_name_btn,
            self.search_content_btn,
        ):
            button.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """処理終了後に UI を戻す。"""
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _format_size(self, size: int) -> str:
        """サイズを見やすく表示する。"""
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
