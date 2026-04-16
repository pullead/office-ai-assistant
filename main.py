# -*- coding: utf-8 -*-
"""
Office AI アシスタント - メインエントリーポイント
面接作品集向け統合オフィス自動化ツール
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger


def main():
    """アプリケーション起動"""
    # ロガー初期化
    setup_logger()

    # Qtアプリケーション生成
    app = QApplication(sys.argv)
    app.setApplicationName("Office AI アシスタント")
    app.setOrganizationName("AI Assistant")

    # メインウィンドウ表示
    window = MainWindow()
    window.show()

    # イベントループ開始
    sys.exit(app.exec())


if __name__ == "__main__":
    main()