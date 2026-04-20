# -*- coding: utf-8 -*-
"""
メインウィンドウ - 修正版（ステータスバー初期化順序バグ修正）
"""
import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QStackedWidget, QStatusBar,
                               QMessageBox, QFrame, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient, QDesktopServices
from PySide6.QtCore import QUrl
from src.ui.tabs.ai_tab import AITab
from src.ui.tabs.ocr_tab import OCRTab
from src.ui.tabs.viz_tab import VizTab
from src.ui.tabs.web_tab import WebTab
from src.ui.tabs.email_tab import EmailTab
from src.ui.tabs.file_tab import FileTab
from src.config import Config
from src.compatibility import Compatibility
from src.utils.i18n import I18n


def create_colored_icon(emoji: str, size: int = 40, bg_color: str = "#3b82f6") -> QIcon:
    """背景色付き角丸アイコンを生成"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(bg_color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size // 4, size // 4)
    font = QFont("Segoe UI Emoji", size - 14)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)


class SidebarButton(QPushButton):
    """サイドバーボタン"""
    def __init__(self, text: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarButton")
        self.setCheckable(True)
        self.setMinimumHeight(56)
        self.setFont(QFont("Meiryo", 12))
        self.setIcon(icon)
        self.setIconSize(QSize(36, 36))
        self.setText(f"  {text}")
        self.setToolTip(text)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.compat = Compatibility()
        self.i18n = I18n()
        self.current_theme = self.config.get('General', 'theme', fallback='light')
        self._menu_built = False

        self.setWindowTitle(self.i18n.get('app_title'))
        self.setGeometry(100, 100, 1280, 820)
        self.setMinimumSize(1024, 700)
        self.setWindowIcon(self._create_app_icon())

        self._load_stylesheet()
        self._setup_ui()
        self._apply_theme()

        # 互換性チェック（遅延実行）
        QTimer.singleShot(500, self._check_compat)

    # ────────────────────────────────────────────
    #  アイコン生成
    # ────────────────────────────────────────────
    def _create_app_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 64, 64)
        grad.setColorAt(0, QColor("#3b82f6"))
        grad.setColorAt(1, QColor("#6366f1"))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 64, 64, 16, 16)
        p.setPen(QColor("white"))
        p.setFont(QFont("Meiryo", 22, QFont.Bold))
        p.drawText(pixmap.rect(), Qt.AlignCenter, "AI")
        p.end()
        return QIcon(pixmap)

    # ────────────────────────────────────────────
    #  スタイルシート読み込み
    # ────────────────────────────────────────────
    def _load_stylesheet(self):
        try:
            with open("src/ui/resources/style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    # ────────────────────────────────────────────
    #  UI構築（ステータスバーを先に作成）
    # ────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ステータスバーはコンテンツより前に作成（_switch_toで使うため）
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.i18n.get('ready'))

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)

        # メニューは最後に（コンテンツ準備後に）
        self._build_menu()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # ── ロゴ ──
        logo_frame = QFrame()
        logo_frame.setObjectName("LogoArea")
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(8, 0, 0, 0)
        logo_layout.setSpacing(10)

        logo_icon = QLabel("🤖")
        logo_icon.setFont(QFont("Segoe UI Emoji", 22))
        logo_icon.setObjectName("LogoText")

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        app_name = QLabel("Office AI")
        app_name.setObjectName("LogoText")
        app_name.setFont(QFont("Meiryo", 15, QFont.Bold))
        ver = QLabel("v1.1.0")
        ver.setObjectName("AppVersion")
        ver.setFont(QFont("Meiryo", 9))
        title_col.addWidget(app_name)
        title_col.addWidget(ver)

        logo_layout.addWidget(logo_icon)
        logo_layout.addLayout(title_col)
        logo_layout.addStretch()
        layout.addWidget(logo_frame)
        layout.addSpacing(16)

        # ── 区切り線 ──
        div = QFrame()
        div.setObjectName("SidebarDivider")
        div.setFixedHeight(1)
        layout.addWidget(div)
        layout.addSpacing(12)

        # ── ナビゲーションボタン ──
        self.nav_buttons: list[SidebarButton] = []
        nav_items = [
            ("ai",    "🤖", self.i18n.get('ai_tab_title'),    "#4f46e5"),
            ("ocr",   "📄", self.i18n.get('ocr_tab_title'),   "#059669"),
            ("viz",   "📊", self.i18n.get('viz_tab_title'),   "#d97706"),
            ("web",   "🌐", self.i18n.get('web_tab_title'),   "#7c3aed"),
            ("email", "📧", self.i18n.get('email_tab_title'), "#dc2626"),
            ("file",  "📁", self.i18n.get('file_tab_title'),  "#475569"),
        ]
        for key, emoji, text, color in nav_items:
            icon = create_colored_icon(emoji, 36, color)
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda _, k=key: self._switch_to(k))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # ── テーマ切替ボタン ──
        div2 = QFrame()
        div2.setObjectName("SidebarDivider")
        div2.setFixedHeight(1)
        layout.addWidget(div2)
        layout.addSpacing(8)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(6)
        light_btn = QPushButton("☀")
        dark_btn = QPushButton("🌙")
        for btn, theme in [(light_btn, 'light'), (dark_btn, 'dark')]:
            btn.setObjectName("ToolButton")
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont("Segoe UI Emoji", 14))
            btn.clicked.connect(lambda _, t=theme: self._set_theme(t))
            theme_row.addWidget(btn)
        layout.addLayout(theme_row)

        self.sidebar = sidebar
        return sidebar

    def _build_content(self) -> QStackedWidget:
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        self.tabs = {
            "ai":    AITab(),
            "ocr":   OCRTab(),
            "viz":   VizTab(),
            "web":   WebTab(),
            "email": EmailTab(),
            "file":  FileTab(),
        }
        for tab in self.tabs.values():
            self.content_stack.addWidget(tab)

        # ステータスバーは既に存在するので安全に呼べる
        self._switch_to("ai")
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        return self.content_stack

    # ────────────────────────────────────────────
    #  タブ切替（ステータスバーは存在済み）
    # ────────────────────────────────────────────
    def _switch_to(self, key: str):
        keys = list(self.tabs.keys())
        if key not in keys:
            return
        index = keys.index(key)
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.status_bar.showMessage(f"{self.nav_buttons[index].text().strip()} — {self.i18n.get('ready')}")

    # ────────────────────────────────────────────
    #  メニューバー（重複防止：clear→build）
    # ────────────────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()
        mb.clear()

        # ファイル
        file_menu = mb.addMenu(self.i18n.get('menu_file'))
        file_menu.addAction("📂  " + self.i18n.get('menu_open'),
                            lambda: self._placeholder("ファイルを開く")).setShortcut("Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("❌  " + self.i18n.get('menu_exit'),
                            self.close).setShortcut("Ctrl+Q")

        # 編集
        edit_menu = mb.addMenu(self.i18n.get('menu_edit'))
        edit_menu.addAction("🗑  " + self.i18n.get('menu_clear_log'),
                            self._clear_status)
        edit_menu.addSeparator()
        edit_menu.addAction("⚙  設定",
                            lambda: self._placeholder("設定ダイアログ"))

        # 表示
        view_menu = mb.addMenu(self.i18n.get('menu_view'))
        view_menu.addAction("☀  " + self.i18n.get('menu_theme_light'),
                            lambda: self._set_theme('light'))
        view_menu.addAction("🌙  " + self.i18n.get('menu_theme_dark'),
                            lambda: self._set_theme('dark'))
        view_menu.addSeparator()
        view_menu.addAction("🖥  フルスクリーン",
                            self._toggle_fullscreen).setShortcut("F11")
        view_menu.addAction("↩  ウィンドウサイズをリセット",
                            self._reset_window_size)

        # ツール
        tool_menu = mb.addMenu("ツール")
        tool_menu.addAction("🤖  AIアシスタント", lambda: self._switch_to("ai")).setShortcut("Ctrl+1")
        tool_menu.addAction("📄  OCR認識",         lambda: self._switch_to("ocr")).setShortcut("Ctrl+2")
        tool_menu.addAction("📊  データ可視化",     lambda: self._switch_to("viz")).setShortcut("Ctrl+3")
        tool_menu.addAction("🌐  Web抽出",         lambda: self._switch_to("web")).setShortcut("Ctrl+4")
        tool_menu.addAction("📧  メール送信",       lambda: self._switch_to("email")).setShortcut("Ctrl+5")
        tool_menu.addAction("📁  ファイル管理",     lambda: self._switch_to("file")).setShortcut("Ctrl+6")

        # 言語
        lang_menu = mb.addMenu(self.i18n.get('menu_language'))
        lang_menu.addAction("🇯🇵  " + self.i18n.get('menu_lang_ja'),
                            lambda: self._set_language('ja'))
        lang_menu.addAction("🇺🇸  " + self.i18n.get('menu_lang_en'),
                            lambda: self._set_language('en'))
        lang_menu.addAction("🇨🇳  " + self.i18n.get('menu_lang_zh'),
                            lambda: self._set_language('zh'))

        # ヘルプ
        help_menu = mb.addMenu(self.i18n.get('menu_help'))
        help_menu.addAction("📖  使い方ガイド",
                            lambda: self._placeholder("使い方ガイド"))
        help_menu.addAction("🐛  バグを報告",
                            lambda: self._open_url("https://github.com/pullead/office-ai-assistant/issues"))
        help_menu.addAction("⭐  GitHubでスターを付ける",
                            lambda: self._open_url("https://github.com/pullead/office-ai-assistant"))
        help_menu.addSeparator()
        help_menu.addAction("ℹ  " + self.i18n.get('menu_about'),
                            self._show_about)

    def _rebuild_menu(self):
        self.menuBar().clear()
        self._build_menu()

    # ────────────────────────────────────────────
    #  テーマ切替
    # ────────────────────────────────────────────
    def _set_theme(self, theme: str):
        self.current_theme = theme
        self.config.set('General', 'theme', theme)
        self._apply_theme()

    def _apply_theme(self):
        self.setProperty('theme', self.current_theme)
        self.style().unpolish(self)
        self.style().polish(self)

    # ────────────────────────────────────────────
    #  言語切替
    # ────────────────────────────────────────────
    def _set_language(self, lang_code: str):
        self.i18n.set_language(lang_code)
        self.setWindowTitle(self.i18n.get('app_title'))
        labels = [
            self.i18n.get('ai_tab_title'),
            self.i18n.get('ocr_tab_title'),
            self.i18n.get('viz_tab_title'),
            self.i18n.get('web_tab_title'),
            self.i18n.get('email_tab_title'),
            self.i18n.get('file_tab_title'),
        ]
        for i, btn in enumerate(self.nav_buttons):
            btn.setText(f"  {labels[i]}")
        self.status_bar.showMessage(self.i18n.get('ready'))
        self._rebuild_menu()

    # ────────────────────────────────────────────
    #  ユーティリティ
    # ────────────────────────────────────────────
    def _clear_status(self):
        self.status_bar.showMessage(self.i18n.get('ready'))

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _reset_window_size(self):
        self.showNormal()
        self.setGeometry(100, 100, 1280, 820)

    def _placeholder(self, feature: str):
        QMessageBox.information(self, "準備中", f"「{feature}」は今後実装予定の機能です。")

    def _open_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _check_compat(self):
        warning = self.compat.check_and_warn()
        if warning:
            QMessageBox.information(self, self.i18n.get('info'), warning)

    def _show_about(self):
        QMessageBox.about(
            self,
            self.i18n.get('menu_about'),
            f"<h3>{self.i18n.get('app_title')}</h3>"
            "<p>Version 1.1.0 &nbsp;|&nbsp; © 2026 pullead</p>"
            "<p>転職面接作品集のために開発された<br>"
            "モダンなオフィス自動化ツールです。</p>"
            "<p><b>技術スタック：</b><br>"
            "PySide6 · pytesseract · matplotlib<br>"
            "wordcloud · pandas · BeautifulSoup4</p>"
            '<p><a href="https://github.com/pullead/office-ai-assistant">GitHub</a></p>'
        )

    def closeEvent(self, event):
        event.accept()