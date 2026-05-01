# -*- coding: utf-8 -*-
"""ファイル整理タブ。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDir, QSortFilterProxyModel, QThread, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFrame,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src.core.file_manager import FileManager
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.ui.widgets.rich_result_panel import RichResultPanel


TYPE_FILTERS = {
    "すべて": set(),
    "文書": {".txt", ".md", ".doc", ".docx", ".pdf"},
    "表計算": {".csv", ".xlsx", ".xls"},
    "画像": {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"},
    "コード": {".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rs"},
    "圧縮": {".zip", ".rar", ".7z", ".tar", ".gz"},
}


# 旧定義に文字化けが混在していたため、実運用で使うフィルター定義をここで明示的に上書きする。
TYPE_FILTERS = {
    "すべて": set(),
    "文書": {".txt", ".md", ".doc", ".docx", ".pdf"},
    "表計算": {".csv", ".xlsx", ".xls"},
    "画像": {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"},
    "コード": {".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rs"},
    "アーカイブ": {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"},
}


class FileFilterProxyModel(QSortFilterProxyModel):
    """ツリー表示向けのファイル絞り込み。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.allowed_extensions: set[str] = set()
        self.min_bytes: int | None = None
        self.max_bytes: int | None = None
        self.modified_since: datetime | None = None
        self.setRecursiveFilteringEnabled(True)

    def set_filter_values(
        self,
        allowed_extensions: set[str],
        min_bytes: int | None,
        max_bytes: int | None,
        modified_since: datetime | None,
    ):
        """絞り込み条件を更新する。"""
        self.allowed_extensions = {item.lower() for item in allowed_extensions}
        self.min_bytes = min_bytes
        self.max_bytes = max_bytes
        self.modified_since = modified_since
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """行の表示可否を返す。"""
        source_model = self.sourceModel()
        source_index = source_model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False
        file_info = source_model.fileInfo(source_index)
        if file_info.isDir():
            return True

        suffix = f".{file_info.suffix().lower()}" if file_info.suffix() else ""
        if self.allowed_extensions and suffix not in self.allowed_extensions:
            return False

        size = file_info.size()
        if self.min_bytes is not None and size < self.min_bytes:
            return False
        if self.max_bytes is not None and size > self.max_bytes:
            return False

        if self.modified_since is not None:
            modified = file_info.lastModified().toPython()
            if modified < self.modified_since:
                return False
        return True


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
                preview_files = [str(path) for path in Path(directory).rglob("*") if path.is_file()][:300]
                payload = {"title": "拡張子整理", "text": text, "files": preview_files}
            elif self.operation == "rename":
                text = self.manager.batch_rename(
                    directory,
                    self.kwargs["pattern"],
                    self.kwargs["replacement"],
                    self.kwargs.get("use_regex", False),
                )
                payload = {"title": "一括リネーム", "text": text, "files": []}
            elif self.operation == "search_content":
                hits = self.manager.search_content(directory, self.kwargs["keyword"], limit=400)
                payload = {
                    "title": "内容検索",
                    "text": f"{len(hits)} 件見つかりました。",
                    "files": hits,
                    "grouped": self.manager.classify_paths(hits),
                }
            elif self.operation == "search_name":
                hits = self.manager.search_files_by_name(directory, self.kwargs["keyword"], limit=400)
                payload = {
                    "title": "ファイル名検索",
                    "text": f"{len(hits)} 件見つかりました。",
                    "files": hits,
                    "grouped": self.manager.classify_paths(hits),
                }
            elif self.operation == "summary":
                report = self.manager.build_directory_report(directory)
                payload = {
                    "title": "フォルダサマリー",
                    "report": report,
                    "files": [item["path"] for item in report["largest_files"]],
                }
            elif self.operation == "duplicate":
                text = self.manager.find_duplicate_files(directory)
                payload = {"title": "重複ファイル検出", "text": text, "files": []}
            elif self.operation == "space_lens":
                report = self.manager.build_space_lens_report(directory)
                payload = {
                    "title": "スペースレンズ",
                    "space_lens": report,
                    "files": [item["path"] for item in report["largest_items"]],
                }
            elif self.operation == "large_old":
                rows = self.manager.find_large_old_files(
                    directory,
                    min_size_mb=self.kwargs.get("min_size_mb", 100),
                    older_than_days=self.kwargs.get("older_than_days", 180),
                )
                payload = {
                    "title": "大型・旧ファイル",
                    "large_old": rows,
                    "files": [item["path"] for item in rows],
                    "text": f"{len(rows)} 件の候補を抽出しました。",
                }
            elif self.operation == "shred":
                text = self.manager.shred_files(self.kwargs.get("paths", []), passes=self.kwargs.get("passes", 1))
                payload = {"title": "シュレッダー", "text": text, "files": []}
            else:
                raise ValueError("未対応の処理です。")
            self.finished.emit(payload)
        except Exception as error:
            self.error.emit(str(error))


class FileTab(BaseTab):
    """ファイル整理、検索、分類表示を行うタブ。"""

    def __init__(self):
        super().__init__(
            title="ファイル整理",
            subtitle="整理、検索、重複検出、フォルダ可視化、ツリー閲覧までを統合した管理画面です。",
            icon="file",
        )
        self.file_manager = FileManager()
        self.current_dir = None
        self.worker = None
        self.last_space_lens_html = None
        self._tree_flash_timer = QTimer(self)
        self._tree_flash_timer.setSingleShot(True)
        self._tree_flash_timer.timeout.connect(self._reset_tree_highlight_style)
        self._setup_content()

    def _setup_content(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        rail = QFrame()
        rail.setObjectName("WorkspaceNav")
        rail.setFixedWidth(200)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(14, 16, 14, 16)
        rail_layout.setSpacing(12)

        rail_layout.addWidget(make_section_label("File Modes"))
        for title, hint in (
            ("Space Lens", "容量の大きい項目を俯瞰表示"),
            ("大型 / 旧ファイル", "整理候補をすばやく抽出"),
            ("検索 / 分類", "名前・内容・種類で探索"),
            ("シュレッダー", "選択項目を安全に削除"),
        ):
            card = QFrame()
            card.setObjectName("WorkspaceNavCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(4)
            title_label = QLabel(title)
            title_label.setObjectName("WorkspaceNavTitle")
            hint_label = QLabel(hint)
            hint_label.setObjectName("WorkspaceNavHint")
            hint_label.setWordWrap(True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(hint_label)
            rail_layout.addWidget(card)

        self.rail_space_btn = QPushButton("Space Lens 可視化")
        self.rail_space_btn.setObjectName("PrimaryButton")
        self.rail_space_btn.clicked.connect(lambda: self._start_simple("space_lens"))
        rail_layout.addWidget(self.rail_space_btn)

        self.rail_summary_btn = QPushButton("フォルダ分析")
        self.rail_summary_btn.setObjectName("SecondaryButton")
        self.rail_summary_btn.clicked.connect(lambda: self._start_simple("summary"))
        rail_layout.addWidget(self.rail_summary_btn)

        self.rail_search_btn = QPushButton("ファイル名検索")
        self.rail_search_btn.setObjectName("ToolButton")
        self.rail_search_btn.clicked.connect(self._search_name)
        rail_layout.addWidget(self.rail_search_btn)
        rail_layout.addStretch()

        controls = QFrame()
        controls.setObjectName("WorkspacePanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(18, 18, 18, 18)
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

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("C:\\Users\\... または任意のフォルダパス")
        self.path_input.setMinimumHeight(38)
        self.path_input.returnPressed.connect(self._jump_to_path)
        path_row.addWidget(self.path_input)

        self.go_path_btn = QPushButton("移動")
        self.go_path_btn.setObjectName("ToolButton")
        self.go_path_btn.setMinimumHeight(38)
        self.go_path_btn.clicked.connect(self._jump_to_path)
        path_row.addWidget(self.go_path_btn)
        controls_layout.addLayout(path_row)

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

        controls_layout.addWidget(make_section_label("CleanUp モード"))
        self.space_lens_btn = QPushButton("Space Lens 可視化")
        self.space_lens_btn.setObjectName("PrimaryButton")
        self.space_lens_btn.setMinimumHeight(42)
        self.space_lens_btn.clicked.connect(lambda: self._start_simple("space_lens"))
        controls_layout.addWidget(self.space_lens_btn)

        cleanup_row = QHBoxLayout()
        self.large_file_mb = QLineEdit()
        self.large_file_mb.setPlaceholderText("大型MB")
        cleanup_row.addWidget(self.large_file_mb)

        self.old_file_days = QLineEdit()
        self.old_file_days.setPlaceholderText("未使用日数")
        cleanup_row.addWidget(self.old_file_days)
        controls_layout.addLayout(cleanup_row)

        self.large_old_btn = QPushButton("大型・旧ファイル抽出")
        self.large_old_btn.setObjectName("SecondaryButton")
        self.large_old_btn.setMinimumHeight(42)
        self.large_old_btn.clicked.connect(self._scan_large_old_files)
        controls_layout.addWidget(self.large_old_btn)

        self.shred_btn = QPushButton("選択項目をシュレッダー")
        self.shred_btn.setObjectName("ToolButton")
        self.shred_btn.setMinimumHeight(42)
        self.shred_btn.clicked.connect(self._shred_selected_files)
        controls_layout.addWidget(self.shred_btn)

        controls_layout.addWidget(make_section_label("一括リネーム"))
        rename_row = QHBoxLayout()
        self.rename_from = QLineEdit()
        self.rename_from.setPlaceholderText("置換前")
        rename_row.addWidget(self.rename_from)
        self.rename_to = QLineEdit()
        self.rename_to.setPlaceholderText("置換後")
        rename_row.addWidget(self.rename_to)
        controls_layout.addLayout(rename_row)
        rename_option_row = QHBoxLayout()
        self.rename_regex_box = QCheckBox("正規表現")
        rename_option_row.addWidget(self.rename_regex_box)
        self.rename_preview_btn = QPushButton("プレビュー")
        self.rename_preview_btn.setObjectName("ToolButton")
        self.rename_preview_btn.setMinimumHeight(36)
        self.rename_preview_btn.clicked.connect(self._preview_rename)
        rename_option_row.addWidget(self.rename_preview_btn)
        rename_option_row.addStretch()
        controls_layout.addLayout(rename_option_row)

        self.rename_btn = QPushButton("リネーム実行")
        self.rename_btn.setObjectName("SecondaryButton")
        self.rename_btn.setMinimumHeight(40)
        self.rename_btn.clicked.connect(self._rename)
        controls_layout.addWidget(self.rename_btn)
        controls_layout.addWidget(make_section_label("クイック作成"))
        template_row = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItem("テキスト", "text")
        self.template_combo.addItem("Markdown", "markdown")
        self.template_combo.addItem("CSV", "csv")
        self.template_combo.addItem("JSON", "json")
        self.template_combo.addItem("Python", "python")
        template_row.addWidget(self.template_combo)
        self.template_name_input = QLineEdit()
        self.template_name_input.setPlaceholderText("新規ファイル名")
        template_row.addWidget(self.template_name_input)
        controls_layout.addLayout(template_row)
        self.template_content_input = QLineEdit()
        self.template_content_input.setPlaceholderText("任意の初期内容（空ならテンプレート既定値）")
        controls_layout.addWidget(self.template_content_input)
        self.create_template_btn = QPushButton("テンプレートから作成")
        self.create_template_btn.setObjectName("ToolButton")
        self.create_template_btn.setMinimumHeight(40)
        self.create_template_btn.clicked.connect(self._create_template_file)
        controls_layout.addWidget(self.create_template_btn)
        controls_layout.addWidget(make_section_label("アーカイブ閲覧"))
        self.archive_btn = QPushButton("圧縮ファイルを閲覧")
        self.archive_btn.setObjectName("ToolButton")
        self.archive_btn.setMinimumHeight(40)
        self.archive_btn.clicked.connect(self._browse_archive)
        self.archive_btn.setText("ZIP / TAR を閲覧")
        controls_layout.addWidget(self.archive_btn)

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

        report_wrapper = QFrame()
        report_wrapper.setObjectName("WorkspaceFloat")
        report_layout = QVBoxLayout(report_wrapper)
        report_layout.setContentsMargins(18, 18, 18, 18)
        report_layout.setSpacing(10)
        report_layout.addWidget(make_section_label("ファイル管理レポート"))
        self.result_panel = RichResultPanel()
        report_layout.addWidget(self.result_panel)

        explorer_wrapper = QFrame()
        explorer_wrapper.setObjectName("WorkspacePanel")
        explorer_layout = QVBoxLayout(explorer_wrapper)
        explorer_layout.setContentsMargins(18, 18, 18, 18)
        explorer_layout.setSpacing(8)
        explorer_layout.addWidget(make_section_label("ツリー表示（エクスプローラー）"))

        filter_row = QHBoxLayout()
        self.type_filter_combo = QComboBox()
        for label in TYPE_FILTERS:
            self.type_filter_combo.addItem(label)
        self.type_filter_combo.setMinimumHeight(34)
        filter_row.addWidget(self.type_filter_combo)

        self.min_size_edit = QLineEdit()
        self.min_size_edit.setPlaceholderText("最小MB")
        self.min_size_edit.setMinimumHeight(34)
        filter_row.addWidget(self.min_size_edit)

        self.max_size_edit = QLineEdit()
        self.max_size_edit.setPlaceholderText("最大MB")
        self.max_size_edit.setMinimumHeight(34)
        filter_row.addWidget(self.max_size_edit)

        self.modified_filter_combo = QComboBox()
        self.modified_filter_combo.addItem("更新日: すべて", None)
        self.modified_filter_combo.addItem("過去7日", 7)
        self.modified_filter_combo.addItem("過去30日", 30)
        self.modified_filter_combo.addItem("過去90日", 90)
        self.modified_filter_combo.setMinimumHeight(34)
        filter_row.addWidget(self.modified_filter_combo)
        explorer_layout.addLayout(filter_row)

        filter_action_row = QHBoxLayout()
        self.apply_filter_btn = QPushButton("フィルタ適用")
        self.apply_filter_btn.setObjectName("ToolButton")
        self.apply_filter_btn.clicked.connect(self._apply_tree_filters)
        filter_action_row.addWidget(self.apply_filter_btn)

        self.clear_filter_btn = QPushButton("フィルタ解除")
        self.clear_filter_btn.setObjectName("ToolButton")
        self.clear_filter_btn.clicked.connect(self._clear_tree_filters)
        filter_action_row.addWidget(self.clear_filter_btn)
        explorer_layout.addLayout(filter_action_row)

        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath("")
        self.tree_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        self.path_model = QFileSystemModel(self)
        self.path_model.setRootPath("")
        self.path_model.setFilter(QDir.AllDirs | QDir.Drives | QDir.NoDotAndDotDot)
        self.path_completer = QCompleter(self.path_model, self)
        self.path_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.path_completer.setFilterMode(Qt.MatchContains)
        self.path_input.setCompleter(self.path_completer)

        self.tree_proxy = FileFilterProxyModel(self)
        self.tree_proxy.setSourceModel(self.tree_model)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_proxy)
        self.tree_view.setAnimated(True)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setMinimumHeight(240)
        self.tree_view.doubleClicked.connect(self._on_tree_double_click)
        explorer_layout.addWidget(self.tree_view)

        explorer_layout.addWidget(make_section_label("検索結果一覧"))
        self.search_result_list = QListWidget()
        self.search_result_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.search_result_list.setMinimumHeight(140)
        self.search_result_list.itemClicked.connect(self._focus_selected_result)
        self.search_result_list.itemDoubleClicked.connect(self._open_selected_result)
        explorer_layout.addWidget(self.search_result_list)

        center_splitter = QSplitter(Qt.Vertical)
        center_splitter.setChildrenCollapsible(False)
        center_splitter.addWidget(controls)
        center_splitter.addWidget(explorer_wrapper)
        center_splitter.setSizes([360, 420])

        splitter.addWidget(rail)
        splitter.addWidget(center_splitter)
        splitter.addWidget(report_wrapper)
        splitter.setSizes([190, 640, 470])
        self.card_layout.addWidget(splitter, 1)

    def _select_dir(self):
        """対象フォルダを選択する。"""
        path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if path:
            self._set_current_dir(path)

    def _set_pc_root(self):
        """PC 全体検索向けルートを設定する。"""
        root = str(Path.home().anchor or "C:\\")
        self._set_current_dir(root)

    def _set_current_dir(self, directory: str):
        """現在の対象フォルダを設定し、ツリーを更新する。"""
        self.current_dir = directory
        self.path_input.setText(directory)
        self.dir_label.setText(directory)
        root_index = self.tree_model.index(directory)
        proxy_root = self.tree_proxy.mapFromSource(root_index)
        self.tree_view.setRootIndex(proxy_root)
        self.tree_view.setColumnWidth(0, 380)
        self.search_result_list.clear()
        self._apply_tree_filters()

    def _jump_to_path(self):
        """アドレスバーから任意の場所へ移動する。"""
        raw_path = self.path_input.text().strip().strip('"')
        if not raw_path:
            return
        target = Path(raw_path).expanduser()
        if target.is_file():
            if target.suffix.lower() in {".zip", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz"}:
                self._show_archive_entries(str(target))
                return
            target = target.parent
        if not target.exists() or not target.is_dir():
            QMessageBox.warning(self, "入力確認", "有効なフォルダパスを入力してください。")
            return
        self._set_current_dir(str(target))

    def _check_dir(self) -> bool:
        """対象フォルダの有無を確認する。"""
        if not self.current_dir:
            QMessageBox.warning(self, "入力確認", "先に対象フォルダを選択してください。")
            return False
        return True

    def _apply_tree_filters(self):
        """ツリーの絞り込み条件を反映する。"""
        allowed = TYPE_FILTERS.get(self.type_filter_combo.currentText(), set())
        min_bytes = self._parse_mb(self.min_size_edit.text().strip(), "最小サイズ", silent=False)
        if min_bytes is None and self.min_size_edit.text().strip():
            return
        max_bytes = self._parse_mb(self.max_size_edit.text().strip(), "最大サイズ", silent=False)
        if max_bytes is None and self.max_size_edit.text().strip():
            return
        if min_bytes is not None and max_bytes is not None and min_bytes > max_bytes:
            QMessageBox.warning(self, "入力確認", "最小サイズは最大サイズ以下で指定してください。")
            return

        days = self.modified_filter_combo.currentData()
        modified_since = None
        if isinstance(days, int):
            modified_since = datetime.now() - timedelta(days=days)

        self.tree_proxy.set_filter_values(
            allowed_extensions=allowed,
            min_bytes=min_bytes,
            max_bytes=max_bytes,
            modified_since=modified_since,
        )
        if self.current_dir:
            source_root = self.tree_model.index(self.current_dir)
            proxy_root = self.tree_proxy.mapFromSource(source_root)
            self.tree_view.setRootIndex(proxy_root)

    def _clear_tree_filters(self):
        """ツリー絞り込みを初期化する。"""
        self.type_filter_combo.setCurrentText("すべて")
        self.min_size_edit.clear()
        self.max_size_edit.clear()
        self.modified_filter_combo.setCurrentIndex(0)
        self._apply_tree_filters()

    def _parse_mb(self, text: str, label: str, silent: bool) -> int | None:
        """MB 入力をバイトへ変換する。"""
        if not text:
            return None
        try:
            mb = float(text)
        except ValueError:
            if not silent:
                QMessageBox.warning(self, "入力確認", f"{label}は数値で入力してください。")
            return None
        if mb < 0:
            if not silent:
                QMessageBox.warning(self, "入力確認", f"{label}は0以上で入力してください。")
            return None
        return int(mb * 1024 * 1024)

    def _parse_positive_int(self, text: str, fallback: int, label: str) -> int:
        """正の整数を安全に解釈する。"""
        if not text:
            return fallback
        try:
            value = int(text)
        except ValueError:
            QMessageBox.warning(self, "入力確認", f"{label}は整数で入力してください。")
            return fallback
        if value <= 0:
            QMessageBox.warning(self, "入力確認", f"{label}は1以上で入力してください。")
            return fallback
        return value

    def _start_worker(self, operation: str, **kwargs):
        """処理ワーカーを起動する。"""
        self._set_buttons(False)
        self.progress_bar.setVisible(True)

        self.worker = FileWorker(self.file_manager, operation, **kwargs)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _start_simple(self, operation: str):
        """フォルダだけで実行できる処理を開始する。"""
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
        self._start_worker(
            "rename",
            directory=self.current_dir,
            pattern=pattern,
            replacement=replacement,
            use_regex=self.rename_regex_box.isChecked(),
        )

    def _preview_rename(self):
        """一括リネームのプレビューを表示する。"""
        if not self._check_dir():
            return
        pattern = self.rename_from.text().strip()
        replacement = self.rename_to.text()
        if not pattern:
            QMessageBox.warning(self, "入力確認", "置換前の文字列を入力してください。")
            return
        rows = self.file_manager.preview_batch_rename(
            self.current_dir,
            pattern,
            replacement,
            use_regex=self.rename_regex_box.isChecked(),
        )
        self.result_panel.set_report_html(self._build_rename_preview_html(rows))
        if rows:
            self.result_panel.show_files([item["path"] for item in rows[:250]])
        else:
            self.result_panel.show_text_preview("変更対象になるファイルは見つかりませんでした。")

    def _create_template_file(self):
        """テンプレートから新規ファイルを作成する。"""
        if not self._check_dir():
            return
        file_name = self.template_name_input.text().strip()
        if not file_name:
            QMessageBox.warning(self, "入力確認", "新規ファイル名を入力してください。")
            return
        try:
            created = self.file_manager.create_template_file(
                self.current_dir,
                self.template_combo.currentData(),
                file_name,
                self.template_content_input.text(),
            )
        except Exception as error:
            QMessageBox.warning(self, "作成エラー", str(error))
            return
        self._set_current_dir(self.current_dir)
        self.result_panel.set_report_html(
            f"<h2>テンプレート作成</h2><p>{self._escape_html(created)} を作成しました。</p>"
        )
        self.result_panel.show_text_preview(Path(created).read_text(encoding='utf-8', errors='ignore')[:12000])

    def _browse_archive(self):
        """圧縮ファイルを選択して内容一覧を表示する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "圧縮ファイルを選択",
            self.current_dir or "",
            "圧縮ファイル (*.zip *.tar *.gz *.tgz *.bz2 *.xz *.tar.gz *.tar.bz2 *.tar.xz)",
        )
        if path:
            self._show_archive_entries(path)

    def _show_archive_entries(self, archive_path: str):
        """圧縮ファイルの内容を結果パネルへ表示する。"""
        try:
            payload = self.file_manager.list_archive_entries(archive_path)
        except Exception as error:
            QMessageBox.warning(self, "アーカイブ閲覧", str(error))
            return
        self.result_panel.set_report_html(self._build_archive_html(payload))
        preview_rows = [
            f"{entry['name']} | {self._format_size(entry['size'])}"
            for entry in payload["entries"][:300]
        ]
        self.result_panel.show_files(preview_rows)

    def _scan_large_old_files(self):
        """大型かつ長期間未使用のファイルを抽出する。"""
        if not self._check_dir():
            return
        min_size_mb = self._parse_positive_int(self.large_file_mb.text().strip(), 100, "大型ファイルしきい値")
        older_than_days = self._parse_positive_int(self.old_file_days.text().strip(), 180, "未使用日数")
        self._start_worker(
            "large_old",
            directory=self.current_dir,
            min_size_mb=min_size_mb,
            older_than_days=older_than_days,
        )

    def _shred_selected_files(self):
        """選択中ファイルを完全削除する。"""
        selected_items = self.search_result_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "入力確認", "シュレッダー対象として検索結果一覧からファイルを選択してください。")
            return
        paths = [item.text() for item in selected_items]
        reply = QMessageBox.question(
            self,
            "最終確認",
            f"選択した {len(paths)} 件を完全削除します。この操作は元に戻せません。\n\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._start_worker("shred", directory=self.current_dir, paths=paths, passes=1)

    def _search_name(self):
        """ファイル名検索を実行する。"""
        if not self._check_dir():
            return
        keyword = self.search_kw.text().strip()
        if not keyword:
            QMessageBox.warning(self, "入力確認", "検索キーワードを入力してください。")
            return
        self._start_worker("search_name", directory=self.current_dir, keyword=keyword)

    def _search_content(self):
        """内容検索を実行する。"""
        if not self._check_dir():
            return
        keyword = self.search_kw.text().strip()
        if not keyword:
            QMessageBox.warning(self, "入力確認", "検索キーワードを入力してください。")
            return
        self._start_worker("search_content", directory=self.current_dir, keyword=keyword)

    def _on_done(self, payload: dict):
        """処理完了時の表示を更新する。"""
        self.search_result_list.clear()
        if "space_lens" in payload:
            report = payload["space_lens"]
            self.last_space_lens_html = report.get("html_path")
            self.result_panel.set_report_html(self._build_space_lens_html(report))
            if report.get("html_path"):
                self.result_panel.show_html_file(report["html_path"])
            else:
                self.result_panel.show_files([item["path"] for item in report["largest_items"]])
            for path in self._filter_file_list_for_active_filters(payload.get("files", []))[:200]:
                self.search_result_list.addItem(path)
            return

        if "large_old" in payload:
            rows = payload["large_old"]
            self.result_panel.set_report_html(self._build_large_old_html(rows))
            if rows:
                self.result_panel.show_files([item["path"] for item in rows[:300]])
                for item in rows[:300]:
                    self.search_result_list.addItem(item["path"])
            else:
                self.result_panel.show_text_preview("条件に一致する大型・旧ファイルは見つかりませんでした。")
            return

        if "report" in payload:
            report = payload["report"]
            self.result_panel.set_report_html(self._build_report_html(report))
            self.result_panel.show_files(report["tree_preview"])
            for path in self._filter_file_list_for_active_filters(payload.get("files", []))[:200]:
                self.search_result_list.addItem(path)
            return

        body = self._escape_html(payload["text"]).replace("\n", "<br>")
        grouped_html = ""
        grouped = payload.get("grouped")
        if grouped:
            grouped_lines = []
            for ext, items in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)[:10]:
                grouped_lines.append(f"<li>{self._escape_html(ext)}: {len(items)} 件</li>")
            grouped_html = f"<h3>分類内訳</h3><ul>{''.join(grouped_lines)}</ul>"

        self.result_panel.set_report_html(
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            f"<h2>{self._escape_html(payload['title'])}</h2>"
            f"{grouped_html}"
            "<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:18px;'>"
            f"{body}</div></div>"
        )
        filtered_files = self._filter_file_list_for_active_filters(payload.get("files", []))
        if filtered_files:
            self.result_panel.show_files(filtered_files[:300])
            for file_path in filtered_files[:300]:
                self.search_result_list.addItem(file_path)
        else:
            self.result_panel.show_text_preview(payload["text"])

    def _filter_file_list_for_active_filters(self, file_paths: list[str]) -> list[str]:
        """現在のフィルタ条件でパス一覧を絞り込む。"""
        results: list[str] = []
        allowed = TYPE_FILTERS.get(self.type_filter_combo.currentText(), set())
        min_bytes = self._parse_mb(self.min_size_edit.text().strip(), "最小サイズ", silent=True)
        max_bytes = self._parse_mb(self.max_size_edit.text().strip(), "最大サイズ", silent=True)
        days = self.modified_filter_combo.currentData()
        modified_since = datetime.now() - timedelta(days=days) if isinstance(days, int) else None

        for raw_path in file_paths:
            if self._path_passes_filters(raw_path, allowed, min_bytes, max_bytes, modified_since):
                results.append(raw_path)
        return results

    def _path_passes_filters(
        self,
        raw_path: str,
        allowed_extensions: set[str],
        min_bytes: int | None,
        max_bytes: int | None,
        modified_since: datetime | None,
    ) -> bool:
        """単一パスが条件を満たすかを判定する。"""
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return False
        if allowed_extensions and path.suffix.lower() not in allowed_extensions:
            return False
        try:
            size = path.stat().st_size
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return False
        if min_bytes is not None and size < min_bytes:
            return False
        if max_bytes is not None and size > max_bytes:
            return False
        if modified_since is not None and modified < modified_since:
            return False
        return True

    def _on_error(self, message: str):
        """エラー表示を行う。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{self._escape_html(message)}</p>")
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
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('ファイル数', str(report['file_count']))}"
            f"{self._table_row('フォルダ数', str(report['folder_count']))}"
            f"{self._table_row('総サイズ', self._format_size(report['total_size']))}"
            "</table>"
            "<h3 style='margin-top:18px;'>拡張子構成</h3>"
            f"<ul>{ext_items}</ul>"
            "<h3>上位フォルダ</h3>"
            f"<ul>{folder_items}</ul>"
            "<h3>大きいファイル</h3>"
            f"<ul>{file_items}</ul>"
            "</div>"
        )

    def _build_space_lens_html(self, report: dict) -> str:
        """Space Lens の要約 HTML を返す。"""
        rows = []
        for item in report.get("summary_rows", [])[:12]:
            rows.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(item['name'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._format_size(item['size'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{item['items']}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(item['kind'])}</td>"
                "</tr>"
            )
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>スペースレンズ</h2>"
            "<p>容量マップを生成し、上位容量項目を俯瞰表示します。</p>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('対象フォルダ', report.get('directory', ''))}"
            f"{self._table_row('総容量', self._format_size(report.get('total_size', 0)))}"
            f"{self._table_row('集計項目数', str(report.get('items', 0)))}"
            "</table>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>項目</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>サイズ</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>件数</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>種別</b></td>"
            "</tr>"
            + "".join(rows)
            + "</table></div>"
        )

    def _build_large_old_html(self, rows: list[dict]) -> str:
        """大型・旧ファイル一覧の HTML を返す。"""
        body_rows = []
        for item in rows[:30]:
            body_rows.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(Path(item['path']).name)}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._format_size(item['size'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{item['last_access_days']} 日前</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{item['last_modified_days']} 日前</td>"
                "</tr>"
            )
        if not body_rows:
            body_rows.append(
                "<tr><td colspan='4' style='border:1px solid #e7dcc7;padding:8px;'>条件に一致する候補はありません。</td></tr>"
            )
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>大型・旧ファイル</h2>"
            "<p>容量が大きく、長期間アクセスされていないファイル候補です。</p>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>ファイル</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>サイズ</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>最終アクセス</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>最終更新</b></td>"
            "</tr>"
            + "".join(body_rows)
            + "</table></div>"
        )

    def _build_rename_preview_html(self, rows: list[dict]) -> str:
        """一括リネームのプレビュー HTML を返す。"""
        body_rows = []
        for item in rows[:30]:
            body_rows.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(item['before'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(item['after'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._format_size(item['size'])}</td>"
                "</tr>"
            )
        if not body_rows:
            body_rows.append("<tr><td colspan='3' style='padding:8px;border:1px solid #e7dcc7;'>変更対象なし</td></tr>")
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>一括リネームプレビュー</h2>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>変更前</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>変更後</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>サイズ</b></td>"
            "</tr>"
            + "".join(body_rows)
            + "</table></div>"
        )

    def _build_archive_html(self, payload: dict) -> str:
        """アーカイブ一覧の HTML を返す。"""
        rows = []
        for entry in payload["entries"][:30]:
            rows.append(
                "<tr>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'>{self._escape_html(entry['name'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._format_size(entry['size'])}</td>"
                f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._format_size(entry['compressed'])}</td>"
                "</tr>"
            )
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>アーカイブ閲覧</h2>"
            f"<p>{self._escape_html(payload['archive'])}</p>"
            f"<p>格納ファイル数: {payload['count']}</p>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<tr>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>項目</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>元サイズ</b></td>"
            "<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;'><b>圧縮後</b></td>"
            "</tr>"
            + "".join(rows)
            + "</table></div>"
        )

    def _table_row(self, title: str, value: str) -> str:
        """レポート用の2列テーブル行を返す。"""
        return (
            "<tr>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;width:22%;'>{self._escape_html(title)}</td>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(value)}</td>"
            "</tr>"
        )

    def _on_tree_double_click(self, index):
        """ツリー項目のダブルクリック時にファイルを開く。"""
        source_index = self.tree_proxy.mapToSource(index)
        path = self.tree_model.filePath(source_index)
        target = Path(path)
        if target.is_file():
            import os

            os.startfile(str(target))

    def _focus_selected_result(self, item):
        """一覧で選択した結果をツリー上で強調表示する。"""
        self._focus_tree_path(item.text())

    def _open_selected_result(self, item):
        """検索結果一覧からファイルを開く。"""
        path = item.text()
        self._focus_tree_path(path)
        target = Path(path)
        if target.exists() and target.is_file():
            import os

            os.startfile(str(target))

    def _focus_tree_path(self, path: str):
        """指定パスをツリーで表示し、ハイライト演出を行う。"""
        if not path:
            return
        source_index = self.tree_model.index(path)
        if not source_index.isValid():
            return
        parent = source_index.parent()
        while parent.isValid():
            proxy_parent = self.tree_proxy.mapFromSource(parent)
            if proxy_parent.isValid():
                self.tree_view.expand(proxy_parent)
            parent = parent.parent()

        proxy_index = self.tree_proxy.mapFromSource(source_index)
        if not proxy_index.isValid():
            return
        self.tree_view.setCurrentIndex(proxy_index)
        self.tree_view.scrollTo(proxy_index, QTreeView.PositionAtCenter)
        self._animate_tree_focus()

    def _animate_tree_focus(self):
        """結果行の強調表示を短時間だけ適用する。"""
        self.tree_view.setStyleSheet(
            "QTreeView::item:selected{background:#f59e0b;color:#111827;border-radius:4px;}"
        )
        self._tree_flash_timer.start(720)

    def _reset_tree_highlight_style(self):
        """ツリーハイライトの一時スタイルを解除する。"""
        self.tree_view.setStyleSheet("")

    def _set_buttons(self, enabled: bool):
        """操作ボタンの有効状態を切り替える。"""
        for button in (
            self.select_btn,
            self.pc_btn,
            self.summary_btn,
            self.organize_btn,
            self.duplicate_btn,
            self.space_lens_btn,
            self.rail_space_btn,
            self.rail_summary_btn,
            self.rail_search_btn,
            self.large_old_btn,
            self.shred_btn,
            self.rename_btn,
            self.rename_preview_btn,
            self.search_name_btn,
            self.search_content_btn,
            self.apply_filter_btn,
            self.clear_filter_btn,
            self.go_path_btn,
            self.create_template_btn,
            self.archive_btn,
        ):
            button.setEnabled(enabled)
        self.type_filter_combo.setEnabled(enabled)
        self.min_size_edit.setEnabled(enabled)
        self.max_size_edit.setEnabled(enabled)
        self.modified_filter_combo.setEnabled(enabled)
        self.large_file_mb.setEnabled(enabled)
        self.old_file_days.setEnabled(enabled)
        self.path_input.setEnabled(enabled)
        self.template_combo.setEnabled(enabled)
        self.template_name_input.setEnabled(enabled)
        self.template_content_input.setEnabled(enabled)
        self.rename_regex_box.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """処理終了後に UI を戻す。"""
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _format_size(self, size: int) -> str:
        """サイズを見やすい単位へ変換する。"""
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
