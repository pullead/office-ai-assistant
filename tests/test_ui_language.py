# -*- coding: utf-8 -*-
"""UI 言語切り替えの回帰テスト。"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from src.ui.main_window import MainWindow, translate_widget_tree


class TestUILanguage(unittest.TestCase):
    """言語切り替え時の描画対象を確認する。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_translate_widget_tree_updates_common_controls(self):
        """タブ内の主要コントロール文言を翻訳できる。"""
        root = QWidget()
        layout = QVBoxLayout(root)
        label = QLabel("クイックコマンド")
        edit = QLineEdit()
        edit.setPlaceholderText("例: ワークスペースを分析して")
        combo = QComboBox()
        combo.addItem("ワークスペース分析")
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.addWidget(combo)

        translate_widget_tree(root, "en")

        self.assertEqual(label.text(), "Quick Command")
        self.assertEqual(edit.placeholderText(), "Example: Analyze this workspace")
        self.assertEqual(combo.itemText(0), "Workspace Analysis")

    def test_main_window_builds_all_tabs(self):
        """メイン画面が主要タブを全て構築できる。"""
        window = MainWindow()
        self.assertEqual(window.content_stack.count(), 6)
        checked = [button.isChecked() for button in window.nav_buttons]
        self.assertEqual(sum(1 for state in checked if state), 1)
        window._switch_to("web")
        checked_after_switch = [button.isChecked() for button in window.nav_buttons]
        self.assertEqual(sum(1 for state in checked_after_switch if state), 1)


if __name__ == "__main__":
    unittest.main()
