# -*- coding: utf-8 -*-
"""メインウィンドウ。"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.compatibility import Compatibility
from src.config import Config
from src.ui.tabs.ai_tab import AITab
from src.ui.tabs.email_tab import EmailTab
from src.ui.tabs.file_tab import FileTab
from src.ui.tabs.ocr_tab import OCRTab
from src.ui.tabs.viz_tab import VizTab
from src.ui.tabs.web_tab import WebTab
from src.utils.i18n import I18n


ICON_DIR = Path("src/ui/resources/icons")
TAB_TRANSLATIONS = {
    "en": {
        "AI ワークスペース": "AI Workspace",
        "要約、議事録整理、TODO 抽出、ファイル分析、OCR 保存案などを大きなレポート表示で扱えます。": "Handle summaries, meeting cleanup, TODO extraction, file analysis, and OCR archive ideas in a large report workspace.",
        "クイックコマンド": "Quick Command",
        "例: ワークスペースを分析して": "Example: Analyze this workspace",
        "実行": "Run",
        "分析モード": "Analysis Mode",
        "ワークスペース分析": "Workspace Analysis",
        "テキスト要約": "Text Summary",
        "TODO 抽出": "TODO Extraction",
        "メール草案": "Mail Draft",
        "議事録レポート": "Meeting Report",
        "ファイル分析": "File Analysis",
        "CSV / Excel 異常値検出": "CSV / Excel Anomaly Detection",
        "OCR 結果の整理保存": "Archive OCR Result",
        "Web 抽出要約": "Web Extraction Summary",
        "改善アイデア提案": "Improvement Ideas",
        "ファイル選択": "Select File",
        "解除": "Clear",
        "Web 抽出用 URL": "URL for web extraction",
        "モード": "Mode",
        "選択ファイル: なし": "Selected file: none",
        "外部 AI API で結果を強化する": "Enhance results with external AI API",
        "API 設定": "API Settings",
        "要約": "Summary",
        "議事録": "Meeting",
        "改善案": "Ideas",
        "ここにメモ、議事録、指示文、分析したい内容を入力してください。": "Enter notes, meeting logs, prompts, or analysis targets here.",
        "AI で分析": "Analyze with AI",
        "結果をコピー": "Copy Result",
        "PDF レポートを開く": "Open PDF Report",
        "入力をクリア": "Clear Input",
        "結果レポート": "Result Report",
        "ローカル処理": "Local Processing",
        "常時利用可能": "Always Available",
        "外部 AI API": "External AI API",
        "入力形式": "Input Type",
        "テキスト / URL / ファイル": "Text / URL / File",
        "大画面レポート": "Large Report View",
        "データ可視化": "Visualization",
        "グラフ生成、AI解説、PDFレポート出力までを一つの画面で扱えます。": "Handle chart generation, AI commentary, and PDF export in one screen.",
        "入力ファイル": "Input File",
        "ファイルを選択": "Select File",
        "可視化モード": "Visualization Mode",
        "棒グラフ": "Bar Chart",
        "折れ線グラフ": "Line Chart",
        "円グラフ": "Pie Chart",
        "ワードクラウド": "Word Cloud",
        "AI API で解説を強化する": "Enhance commentary with AI API",
        "生成する": "Generate",
        "出力ファイルを開く": "Open Output",
        "処理ログ": "Processing Log",
        "可視化の進行状況や補足情報をここに表示します。": "Progress and notes will appear here.",
        "可視化レポート": "Visualization Report",
        "Web 抽出": "Web Extract",
        "URL から本文を抽出し、AI 要約や保存まで見やすいレポート形式で扱えます。": "Extract main text from a URL and review summaries or saved output in report form.",
        "URL": "URL",
        "Web 抽出結果を AI API で整理する": "Organize extracted web text with AI API",
        "本文を抽出": "Extract Main Text",
        "PDF 保存": "Save as PDF",
        "テキスト保存": "Save Text",
        "ヒント": "Tip",
        "URL は省略して入力しても自動で https:// を補完します。": "Even if you omit the scheme, https:// will be added automatically.",
        "抽出レポート": "Extraction Report",
        "AI メールアシスタント": "AI Mail Assistant",
        "メール読解、返信候補生成、修正、SMTP 送信までを一つの画面で扱えます。": "Handle email reading, reply generation, refinement, and SMTP sending in one screen.",
        "メールソース": "Mail Source",
        "SMTP 未設定": "SMTP not configured",
        "EML / TXT 読み込み": "Load EML / TXT",
        "入力クリア": "Clear Input",
        "読み込み元: なし": "Source: none",
        "SMTP 設定": "SMTP Settings",
        "件名": "Subject",
        "送信者": "Sender",
        "返信先 / 宛先": "Reply To / Recipient",
        "メール本文またはヘッダー付きの原文を貼り付けてください。": "Paste the email body or original text with headers.",
        "外部 AI API で分析と返信生成を強化する": "Enhance analysis and reply generation with external AI API",
        "返信モード": "Reply Mode",
        "通常返信": "Standard Reply",
        "受諾返信": "Acceptance Reply",
        "追加確認": "Follow-up Question",
        "正式・丁寧": "Formal",
        "親しみやすい": "Friendly",
        "簡潔": "Brief",
        "例: 納期を必ず確認したい / 英語表現を避けたい / 価格相談を含めたい": "Example: Confirm the deadline / avoid English phrases / include a pricing question",
        "帮我读": "Read for Me",
        "帮我回": "Reply for Me",
        "修改回复": "Refine Reply",
        "返信草案": "Reply Draft",
        "返信件名": "Reply Subject",
        "生成された返信本文をここで確認・修正できます。": "Review and edit the generated reply body here.",
        "添付ファイル": "Attachments",
        "追加": "Add",
        "削除": "Remove",
        "返信文をコピー": "Copy Reply",
        "SMTP 送信": "Send via SMTP",
        "AI メールレポート": "AI Mail Report",
        "送信方式": "Delivery",
        "SMTP / 添付対応": "SMTP / Attachments",
        "AI Reply Flow": "AI Reply Flow",
        "ファイル整理": "File Tools",
        "整理、検索、重複検出、フォルダ可視化、ツリー閲覧までを統合した管理画面です。": "An integrated file workspace for cleanup, search, duplicate detection, folder visualization, and tree browsing.",
        "対象フォルダ": "Target Folder",
        "フォルダを選択": "Select Folder",
        "この PC ルート": "This PC Root",
        "分析と整理": "Analysis & Cleanup",
        "フォルダ分析": "Analyze Folder",
        "拡張子ごとに整理": "Organize by Extension",
        "重複ファイルを検出": "Detect Duplicates",
        "CleanUp モード": "CleanUp Mode",
        "Space Lens 可視化": "Space Lens View",
        "大型MB": "Large MB",
        "未使用日数": "Idle Days",
        "大型・旧ファイル抽出": "Find Large / Old Files",
        "選択項目をシュレッダー": "Shred Selected Items",
        "一括リネーム": "Batch Rename",
        "置換前": "Find",
        "置換後": "Replace",
        "リネーム実行": "Run Rename",
        "検索": "Search",
        "検索キーワード": "Search keyword",
        "ファイル名検索": "Search by Name",
        "内容検索": "Search in Content",
        "ファイル管理レポート": "File Management Report",
        "ツリー表示（エクスプローラー）": "Tree View (Explorer)",
        "すべて": "All",
        "文書": "Documents",
        "表計算": "Spreadsheets",
        "画像": "Images",
        "コード": "Code",
        "圧縮": "Archives",
        "最小MB": "Min MB",
        "最大MB": "Max MB",
        "更新日: すべて": "Modified: All",
        "過去7日": "Last 7 Days",
        "過去30日": "Last 30 Days",
        "過去90日": "Last 90 Days",
        "フィルタ適用": "Apply Filters",
        "フィルタ解除": "Clear Filters",
        "検索結果一覧": "Search Results",
    },
    "zh": {
        "クイックコマンド": "快捷指令",
        "実行": "执行",
        "分析モード": "分析模式",
        "ファイル選択": "选择文件",
        "解除": "清除",
        "モード": "模式",
        "API 設定": "API 设置",
        "要約": "摘要",
        "議事録": "会议",
        "改善案": "建议",
        "AI で分析": "用 AI 分析",
        "結果をコピー": "复制结果",
        "PDF レポートを開く": "打开 PDF 报告",
        "入力をクリア": "清空输入",
        "結果レポート": "结果报告",
        "画像ファイル": "图片文件",
        "画像を選択": "选择图片",
        "未選択": "未选择",
        "実行メニュー": "执行菜单",
        "全文 OCR": "全文 OCR",
        "請求書 / 領収書 解析": "发票 / 收据解析",
        "OCR 結果を整理保存": "整理保存 OCR 结果",
        "OCR レポート": "OCR 报告",
        "入力ファイル": "输入文件",
        "ファイルを選択": "选择文件",
        "可視化モード": "可视化模式",
        "棒グラフ": "柱状图",
        "折れ線グラフ": "折线图",
        "円グラフ": "饼图",
        "ワードクラウド": "词云",
        "生成する": "生成",
        "出力ファイルを開く": "打开输出文件",
        "処理ログ": "处理日志",
        "可視化レポート": "可视化报告",
        "本文を抽出": "提取正文",
        "PDF 保存": "保存 PDF",
        "テキスト保存": "保存文本",
        "ヒント": "提示",
        "抽出レポート": "提取报告",
        "メールソース": "邮件来源",
        "SMTP 未設定": "SMTP 未设置",
        "EML / TXT 読み込み": "读取 EML / TXT",
        "SMTP 設定": "SMTP 设置",
        "件名": "主题",
        "送信者": "发件人",
        "返信先 / 宛先": "回复地址 / 收件人",
        "返信モード": "回复模式",
        "通常返信": "常规回复",
        "受諾返信": "接受回复",
        "追加確認": "追加确认",
        "正式・丁寧": "正式礼貌",
        "親しみやすい": "亲切自然",
        "簡潔": "简洁",
        "返信草案": "回复草稿",
        "返信件名": "回复主题",
        "添付ファイル": "附件",
        "追加": "添加",
        "削除": "删除",
        "返信文をコピー": "复制回复",
        "SMTP 送信": "通过 SMTP 发送",
        "AI メールレポート": "AI 邮件报告",
        "対象フォルダ": "目标文件夹",
        "フォルダを選択": "选择文件夹",
        "この PC ルート": "本机根目录",
        "分析と整理": "分析与整理",
        "フォルダ分析": "分析文件夹",
        "拡張子ごとに整理": "按扩展名整理",
        "重複ファイルを検出": "检测重复文件",
        "CleanUp モード": "清理模式",
        "Space Lens 可視化": "Space Lens 可视化",
        "大型・旧ファイル抽出": "提取大文件/旧文件",
        "選択項目をシュレッダー": "粉碎选中项",
        "一括リネーム": "批量重命名",
        "リネーム実行": "执行重命名",
        "検索": "搜索",
        "ファイル名検索": "按文件名搜索",
        "内容検索": "按内容搜索",
        "ファイル管理レポート": "文件管理报告",
        "ツリー表示（エクスプローラー）": "树状视图（资源管理器）",
        "検索結果一覧": "搜索结果列表",
    },
}


def create_placeholder_icon(label: str, size: int = 40) -> QIcon:
    """簡易アイコンを生成する。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor("#0f766e"))
    gradient.setColorAt(1, QColor("#d97745"))
    painter.setBrush(gradient)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 12, 12)

    painter.setPen(QColor("white"))
    painter.setFont(QFont("Yu Gothic UI", max(10, size // 3), QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, label[:2].upper())
    painter.end()
    return QIcon(pixmap)


def load_sidebar_icon(name: str, fallback_label: str) -> QIcon:
    """サイドバー用アイコンを読み込む。"""
    icon_path = ICON_DIR / f"{name}.png"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return create_placeholder_icon(fallback_label)


def translate_widget_tree(root_widget, lang_code: str):
    """タブ内の主要ウィジェット文言を一括翻訳する。"""
    if lang_code == "ja":
        return
    catalog = TAB_TRANSLATIONS.get(lang_code, {})
    if not catalog:
        return
    for widget_type in (QLabel, QPushButton, QCheckBox):
        for widget in root_widget.findChildren(widget_type):
            text = widget.text()
            if text in catalog:
                widget.setText(catalog[text])
    for widget_type in (QLineEdit, QTextEdit):
        for widget in root_widget.findChildren(widget_type):
            placeholder = widget.placeholderText()
            if placeholder in catalog:
                widget.setPlaceholderText(catalog[placeholder])
    for combo in root_widget.findChildren(QComboBox):
        for index in range(combo.count()):
            item_text = combo.itemText(index)
            if item_text in catalog:
                combo.setItemText(index, catalog[item_text])


class SidebarButton(QPushButton):
    """サイドバー用ボタン。"""

    def __init__(self, text: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarButton")
        self.setCheckable(True)
        self.setMinimumHeight(60)
        self.setFont(QFont("Yu Gothic UI", 11))
        self.setIcon(icon)
        self.setIconSize(QSize(30, 30))
        self.setText(f"  {text}")
        self.setToolTip(text)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    """アプリケーションのメイン画面。"""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.compat = Compatibility()
        self.i18n = I18n()
        self.current_theme = self.config.get("General", "theme", fallback="light")
        self.tabs = {}
        self.nav_items = []

        self.setWindowTitle(self.i18n.get("app_title"))
        self.setGeometry(80, 60, 1360, 860)
        self.setMinimumSize(1100, 760)
        self.setWindowIcon(self._create_app_icon())

        self._load_stylesheet()
        self._setup_ui()
        self._apply_theme()

        QTimer.singleShot(500, self._check_compat)

    def _create_app_icon(self) -> QIcon:
        """アプリのウィンドウアイコンを作る。"""
        pixmap = QPixmap(72, 72)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, 72, 72)
        gradient.setColorAt(0, QColor("#0f766e"))
        gradient.setColorAt(1, QColor("#d97745"))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 72, 72, 18, 18)
        painter.setPen(QColor("#fffdf8"))
        painter.setFont(QFont("Yu Gothic UI", 23, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "OA")
        painter.end()
        return QIcon(pixmap)

    def _load_stylesheet(self):
        """スタイルシートを読み込む。"""
        try:
            with open("src/ui/resources/style.qss", "r", encoding="utf-8") as file:
                self.setStyleSheet(file.read())
        except FileNotFoundError:
            pass

    def _setup_ui(self):
        """全体 UI を構築する。"""
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.i18n.get("ready"))

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)
        self._build_menu()

    def _build_sidebar(self) -> QFrame:
        """左サイドバーを作る。"""
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("SidebarHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(6)

        self.sidebar_title = QLabel("Office AI")
        self.sidebar_title.setObjectName("SidebarHeroTitle")
        self.sidebar_subtitle = QLabel()
        self.sidebar_subtitle.setObjectName("SidebarHeroSubtitle")
        self.sidebar_subtitle.setWordWrap(True)
        hero_layout.addWidget(self.sidebar_title)
        hero_layout.addWidget(self.sidebar_subtitle)
        layout.addWidget(hero)

        self.workspace_label = QLabel()
        self.workspace_label.setObjectName("SidebarHint")
        layout.addWidget(self.workspace_label)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        self.nav_buttons: list[SidebarButton] = []
        self.nav_items = self._build_nav_items()

        for key, fallback_label, text in self.nav_items:
            button = SidebarButton(text, load_sidebar_icon(key, fallback_label))
            button.clicked.connect(lambda _, current_key=key: self._switch_to(current_key))
            layout.addWidget(button)
            self.nav_buttons.append(button)

        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        footer_card = QFrame()
        footer_card.setObjectName("SidebarFooterCard")
        footer_layout = QVBoxLayout(footer_card)
        footer_layout.setContentsMargins(14, 14, 14, 14)
        footer_layout.setSpacing(6)

        self.footer_title = QLabel()
        self.footer_title.setObjectName("SidebarFooterTitle")
        self.footer_hint = QLabel()
        self.footer_hint.setObjectName("SidebarFooterHint")
        self.footer_hint.setWordWrap(True)
        footer_layout.addWidget(self.footer_title)
        footer_layout.addWidget(self.footer_hint)

        theme_row = QHBoxLayout()
        self.light_btn = QPushButton()
        self.dark_btn = QPushButton()
        for button, theme in ((self.light_btn, "light"), (self.dark_btn, "dark")):
            button.setObjectName("ThemeToggle")
            button.setMinimumHeight(34)
            button.clicked.connect(lambda _, current_theme=theme: self._set_theme(current_theme))
            theme_row.addWidget(button)
        footer_layout.addLayout(theme_row)
        layout.addWidget(footer_card)
        self._refresh_sidebar_texts()

        return sidebar

    def _build_content(self) -> QStackedWidget:
        """右側のコンテンツ領域を作る。"""
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")
        self._rebuild_tabs("ai")
        return self.content_stack

    def _build_menu(self):
        """メニューバーを作る。"""
        menu_bar = self.menuBar()
        menu_bar.clear()

        file_menu = menu_bar.addMenu(self.i18n.get("menu_file"))
        file_menu.addAction(self.i18n.get("menu_open"), lambda: self._placeholder("ファイルを開く"))
        file_menu.addSeparator()
        file_menu.addAction(self.i18n.get("menu_exit"), self.close)

        edit_menu = menu_bar.addMenu(self.i18n.get("menu_edit"))
        edit_menu.addAction(self.i18n.get("menu_clear_log"), self._clear_status)
        edit_menu.addAction(self.i18n.get("menu_settings"), lambda: self._placeholder("設定"))

        view_menu = menu_bar.addMenu(self.i18n.get("menu_view"))
        view_menu.addAction(self.i18n.get("menu_theme_light"), lambda: self._set_theme("light"))
        view_menu.addAction(self.i18n.get("menu_theme_dark"), lambda: self._set_theme("dark"))
        view_menu.addSeparator()
        view_menu.addAction(self.i18n.get("menu_fullscreen"), self._toggle_fullscreen)
        view_menu.addAction(self.i18n.get("menu_reset_window"), self._reset_window_size)

        tools_menu = menu_bar.addMenu(self.i18n.get("menu_tools"))
        for key, _fallback, text in self.nav_items:
            tools_menu.addAction(text, lambda current_key=key: self._switch_to(current_key))

        language_menu = menu_bar.addMenu(self.i18n.get("menu_language"))
        language_menu.addAction(self.i18n.get("menu_lang_ja"), lambda: self._set_language("ja"))
        language_menu.addAction(self.i18n.get("menu_lang_en"), lambda: self._set_language("en"))
        language_menu.addAction(self.i18n.get("menu_lang_zh"), lambda: self._set_language("zh"))

        help_menu = menu_bar.addMenu(self.i18n.get("menu_help"))
        help_menu.addAction(self.i18n.get("menu_usage"), lambda: self._placeholder("使い方"))
        help_menu.addAction(
            self.i18n.get("menu_report_bug"),
            lambda: self._open_url("https://github.com/pullead/office-ai-assistant/issues"),
        )
        help_menu.addAction(
            self.i18n.get("menu_github"),
            lambda: self._open_url("https://github.com/pullead/office-ai-assistant"),
        )
        help_menu.addSeparator()
        help_menu.addAction(self.i18n.get("menu_about"), self._show_about)

    def _build_nav_items(self):
        """現在言語に応じたナビゲーション文言を返す。"""
        return [
            ("ai", "AI", self.i18n.get("ai_tab_title")),
            ("ocr", "OCR", self.i18n.get("ocr_tab_title")),
            ("viz", "VZ", self.i18n.get("viz_tab_title")),
            ("web", "WB", self.i18n.get("web_tab_title")),
            ("email", "ML", self.i18n.get("email_tab_title")),
            ("file", "FL", self.i18n.get("file_tab_title")),
        ]

    def _refresh_sidebar_texts(self):
        """サイドバーの固定文言を更新する。"""
        self.sidebar_subtitle.setText(self.i18n.get("sidebar_subtitle"))
        self.workspace_label.setText(
            self.i18n.get("workspace_label").format(name=Path.cwd().name)
        )
        self.footer_title.setText(self.i18n.get("sidebar_footer_title"))
        self.footer_hint.setText(self.i18n.get("sidebar_footer_hint"))
        self.light_btn.setText(self.i18n.get("theme_light_short"))
        self.dark_btn.setText(self.i18n.get("theme_dark_short"))

    def _rebuild_tabs(self, current_key: str):
        """現在言語向けにタブを再生成する。"""
        try:
            new_tabs = {
                "ai": AITab(),
                "ocr": OCRTab(),
                "viz": VizTab(),
                "web": WebTab(),
                "email": EmailTab(),
                "file": FileTab(),
            }
            for tab in new_tabs.values():
                translate_widget_tree(tab, self.i18n.get_current_language())
        except Exception as error:
            QMessageBox.warning(
                self,
                self.i18n.get("warning"),
                f"タブの再構築に失敗しました。\n{error}",
            )
            return

        previous_widgets = [self.content_stack.widget(index) for index in range(self.content_stack.count())]
        for widget in previous_widgets:
            self.content_stack.removeWidget(widget)
            widget.deleteLater()

        self.tabs = new_tabs
        for tab in self.tabs.values():
            self.content_stack.addWidget(tab)

        if current_key not in self.tabs:
            current_key = "ai"
        self._switch_to(current_key)
        keys = list(self.tabs.keys())
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(keys[button_index] == current_key)

    def _switch_to(self, key: str):
        """表示タブを切り替える。"""
        keys = list(self.tabs.keys())
        if key not in keys:
            return

        index = keys.index(key)
        self.content_stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

        self.status_bar.showMessage(f"{self.nav_items[index][2]} | {self.i18n.get('ready')}")

    def _set_theme(self, theme: str):
        """テーマを切り替える。"""
        self.current_theme = theme
        self.config.set("General", "theme", theme)
        self._apply_theme()

    def _apply_theme(self):
        """テーマを適用する。"""
        self.setProperty("theme", self.current_theme)
        self.style().unpolish(self)
        self.style().polish(self)

    def _set_language(self, lang_code: str):
        """UI 言語を切り替える。"""
        current_key = list(self.tabs.keys())[self.content_stack.currentIndex()] if self.tabs else "ai"
        self.i18n.set_language(lang_code)
        self.setWindowTitle(self.i18n.get("app_title"))
        self.nav_items = self._build_nav_items()

        for button, item in zip(self.nav_buttons, self.nav_items):
            button.setText(f"  {item[2]}")
            button.setToolTip(item[2])

        self._refresh_sidebar_texts()
        self._rebuild_tabs(current_key)
        self.status_bar.showMessage(self.i18n.get("ready"))
        self._build_menu()

    def _clear_status(self):
        """ステータスバーを初期表示へ戻す。"""
        self.status_bar.showMessage(self.i18n.get("ready"))

    def _toggle_fullscreen(self):
        """フルスクリーン表示を切り替える。"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _reset_window_size(self):
        """ウィンドウサイズを標準へ戻す。"""
        self.showNormal()
        self.setGeometry(80, 60, 1360, 860)

    def _placeholder(self, feature: str):
        """未実装機能の案内を出す。"""
        QMessageBox.information(self, "案内", f"「{feature}」は今後さらに拡張予定です。")

    def _open_url(self, url: str):
        """外部 URL を開く。"""
        QDesktopServices.openUrl(QUrl(url))

    def _check_compat(self):
        """互換性チェックを表示する。"""
        warning = self.compat.check_and_warn()
        if warning:
            QMessageBox.information(self, self.i18n.get("info"), warning)

    def _show_about(self):
        """About ダイアログを表示する。"""
        QMessageBox.about(
            self,
            self.i18n.get("menu_about"),
            (
                f"<h3>{self.i18n.get('app_title')}</h3>"
                "<p>Version 1.3.0</p>"
                "<p>業務支援、AI 補助、OCR、可視化を一つにまとめたデスクトップツールです。</p>"
                "<p><b>主な機能:</b><br>"
                "AI 補助 / OCR / データ可視化 / Web 抽出 / メール支援 / ファイル整理</p>"
                '<p><a href="https://github.com/pullead/office-ai-assistant">GitHub</a></p>'
            ),
        )

    def closeEvent(self, event):
        event.accept()
