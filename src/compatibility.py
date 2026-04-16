# -*- coding: utf-8 -*-
"""
クロスプラットフォーム互換性チェック
非Windows環境での警告表示など
"""
import sys
import platform
from pathlib import Path


class Compatibility:
    """OS互換性チェッカー"""

    def __init__(self):
        self.system = platform.system()
        self.is_windows = (self.system == 'Windows')
        self.is_mac = (self.system == 'Darwin')
        self.is_linux = (self.system == 'Linux')

        # 初回起動マークファイル
        self.mark_file = Path.home() / ".office_ai_assistant" / "first_run_mark"

    def check_and_warn(self):
        """非Windows環境で初回のみ警告表示"""
        if not self.is_windows and not self.mark_file.exists():
            self.mark_file.parent.mkdir(exist_ok=True)
            self.mark_file.touch()
            return self._get_warning_message()
        return None

    def _get_warning_message(self):
        """警告メッセージ（日本語）"""
        msg = (
            "【互換性に関する注意】\n\n"
            "python-officeの一部機能（poppt, powordなど）はWindows専用です。\n"
            "現在のOS: {}\n\n"
            "代替機能を以下に示します：\n"
            "・PDF処理 → popdf（全OS対応）\n"
            "・OCR → pytesseract（全OS対応）\n"
            "・ファイル管理 → pofile（全OS対応）\n\n"
            "このメッセージは初回のみ表示されます。"
        ).format(self.system)
        return msg