# -*- coding: utf-8 -*-
"""UI 言語切り替えの回帰テスト。"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


class TestUILanguage(unittest.TestCase):
    """言語切り替え時の描画対象を確認する。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_rebuild_tabs_for_each_language(self):
        """言語切り替え後もタブが維持される。"""
        window = MainWindow()
        self.assertEqual(window.content_stack.count(), 6)
        for lang in ("ja", "en", "zh"):
            window._set_language(lang)
            self.assertEqual(window.content_stack.count(), 6)
            current = window.content_stack.currentWidget()
            self.assertIsNotNone(current)
            self.assertGreater(current.sizeHint().width(), 100)
            self.assertGreater(current.sizeHint().height(), 100)


if __name__ == "__main__":
    unittest.main()
