# -*- coding: utf-8 -*-
"""データ可視化モジュールの回帰テスト。"""

import tempfile
import unittest
from pathlib import Path

from src.core.visualization import DataVisualizer


class TestDataVisualizer(unittest.TestCase):
    """可視化の主要入力パターンを確認する。"""

    def test_txt_file_can_generate_bar_chart(self):
        """TXT 入力でも棒グラフを生成できる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "notes.txt"
            source.write_text(
                "売上 売上 売上 改善 提案 提案 課題 課題 課題 課題 共有",
                encoding="utf-8",
            )
            visualizer = DataVisualizer(output_dir=str(root / "output"))

            payload = visualizer.create_visualization(str(source), "bar")

            self.assertEqual(payload["x_col"], DataVisualizer.TEXT_LABEL_COLUMN)
            self.assertEqual(payload["y_col"], DataVisualizer.TEXT_VALUE_COLUMN)
            self.assertFalse(payload["dataframe"].empty)
            self.assertTrue(Path(payload["output_path"]).exists())
            self.assertTrue(Path(payload["preview_image_path"]).exists())
            self.assertIn("可視化モード: 棒グラフ", payload["summary"])

    def test_empty_txt_creates_empty_dataframe(self):
        """空の TXT は空の表として扱われる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "empty.txt"
            source.write_text("", encoding="utf-8")
            visualizer = DataVisualizer(output_dir=str(root / "output"))

            dataframe = visualizer.load_table(source)

            self.assertEqual(list(dataframe.columns), ["項目", "件数"])
            self.assertTrue(dataframe.empty)

    def test_csv_input_still_works_for_pie_chart(self):
        """既存の CSV 入力も継続して利用できる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sales.csv"
            source.write_text("部署,件数\n営業,10\n開発,7\n総務,3\n", encoding="utf-8")
            visualizer = DataVisualizer(output_dir=str(root / "output"))

            payload = visualizer.create_visualization(str(source), "pie")

            self.assertEqual(payload["x_col"], "部署")
            self.assertEqual(payload["y_col"], "件数")
            self.assertTrue(Path(payload["output_path"]).exists())
            self.assertIn("可視化モード: 円グラフ", payload["summary"])


if __name__ == "__main__":
    unittest.main()
