# -*- coding: utf-8 -*-
"""メインウィンドウ。"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QStatusBar,
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

        title = QLabel("Office AI")
        title.setObjectName("SidebarHeroTitle")
        subtitle = QLabel("業務を速く、見やすく、整理して扱うための統合ツール")
        subtitle.setObjectName("SidebarHeroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        workspace_label = QLabel(f"Workspace: {Path.cwd().name}")
        workspace_label.setObjectName("SidebarHint")
        layout.addWidget(workspace_label)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        self.nav_buttons: list[SidebarButton] = []
        self.nav_items = [
            ("ai", "AI", self.i18n.get("ai_tab_title")),
            ("ocr", "OCR", self.i18n.get("ocr_tab_title")),
            ("viz", "VZ", self.i18n.get("viz_tab_title")),
            ("web", "WB", self.i18n.get("web_tab_title")),
            ("email", "ML", self.i18n.get("email_tab_title")),
            ("file", "FL", self.i18n.get("file_tab_title")),
        ]

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

        footer_title = QLabel("Quick Status")
        footer_title.setObjectName("SidebarFooterTitle")
        footer_hint = QLabel("AI / OCR / 可視化 / Web / Mail / Files")
        footer_hint.setObjectName("SidebarFooterHint")
        footer_hint.setWordWrap(True)
        footer_layout.addWidget(footer_title)
        footer_layout.addWidget(footer_hint)

        theme_row = QHBoxLayout()
        light_btn = QPushButton("Light")
        dark_btn = QPushButton("Dark")
        for button, theme in ((light_btn, "light"), (dark_btn, "dark")):
            button.setObjectName("ThemeToggle")
            button.setMinimumHeight(34)
            button.clicked.connect(lambda _, current_theme=theme: self._set_theme(current_theme))
            theme_row.addWidget(button)
        footer_layout.addLayout(theme_row)
        layout.addWidget(footer_card)

        return sidebar

    def _build_content(self) -> QStackedWidget:
        """右側のコンテンツ領域を作る。"""
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        self.tabs = {
            "ai": AITab(),
            "ocr": OCRTab(),
            "viz": VizTab(),
            "web": WebTab(),
            "email": EmailTab(),
            "file": FileTab(),
        }
        for tab in self.tabs.values():
            self.content_stack.addWidget(tab)

        self._switch_to("ai")
        self.nav_buttons[0].setChecked(True)
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
        self.i18n.set_language(lang_code)
        self.setWindowTitle(self.i18n.get("app_title"))

        self.nav_items = [
            ("ai", "AI", self.i18n.get("ai_tab_title")),
            ("ocr", "OCR", self.i18n.get("ocr_tab_title")),
            ("viz", "VZ", self.i18n.get("viz_tab_title")),
            ("web", "WB", self.i18n.get("web_tab_title")),
            ("email", "ML", self.i18n.get("email_tab_title")),
            ("file", "FL", self.i18n.get("file_tab_title")),
        ]

        for button, item in zip(self.nav_buttons, self.nav_items):
            button.setText(f"  {item[2]}")
            button.setToolTip(item[2])

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
