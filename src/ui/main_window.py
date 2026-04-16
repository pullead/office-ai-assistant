# -*- coding: utf-8 -*-
"""
メインウィンドウ - タブ切り替えGUI（完全版）
"""
from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar, QMessageBox
from PySide6.QtCore import Qt
from src.ui.tabs.ai_tab import AITab
from src.ui.tabs.ocr_tab import OCRTab
from src.ui.tabs.viz_tab import VizTab
from src.ui.tabs.web_tab import WebTab
from src.ui.tabs.email_tab import EmailTab
from src.ui.tabs.file_tab import FileTab
from src.config import Config
from src.compatibility import Compatibility


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.compat = Compatibility()
        self.setWindowTitle("Office AI アシスタント - 面接作品集")
        self.setGeometry(100, 100, 1200, 800)

        self.apply_stylesheet()

        # 互換性警告（初回のみ）
        warning = self.compat.check_and_warn()
        if warning:
            QMessageBox.information(self, "互換性に関する注意", warning)

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setMovable(False)

        # 各タブを追加（すべてインポート済み）
        self.tab_widget.addTab(AITab(), "🤖 AIアシスタント")
        self.tab_widget.addTab(OCRTab(), "📄 OCR認識")
        self.tab_widget.addTab(VizTab(), "📊 データ可視化")
        self.tab_widget.addTab(WebTab(), "🌐 Web抽出")
        self.tab_widget.addTab(EmailTab(), "📧 メール自動送信")
        self.tab_widget.addTab(FileTab(), "📁 ファイル管理")

        layout.addWidget(self.tab_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了")

    def apply_stylesheet(self):
        style = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 10px 20px;
            margin: 2px;
            border-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: #4a90e2;
            color: white;
        }
        QPushButton {
            background-color: #4a90e2;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #357abd;
        }
        QLineEdit, QTextEdit, QComboBox, QListWidget {
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 5px;
        }
        """
        self.setStyleSheet(style)