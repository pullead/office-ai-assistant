# -*- coding: utf-8 -*-
"""
Office AI アシスタント - メインエントリーポイント
面接作品集向け統合オフィス自動化ツール
"""
import threading
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from loguru import logger
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger


def _install_exception_hooks():
    """未捕捉例外をログへ記録する。"""

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("未捕捉例外が発生しました")

    def handle_thread_exception(args):
        logger.opt(exception=(args.exc_type, args.exc_value, args.exc_traceback)).error(
            "スレッド内で未捕捉例外が発生しました"
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception


def main():
    """アプリケーション起動"""
    # ロガー初期化
    setup_logger()
    _install_exception_hooks()

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
