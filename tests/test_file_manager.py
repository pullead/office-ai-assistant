# -*- coding: utf-8 -*-
"""ファイル管理機能の回帰テスト。"""

import tempfile
import unittest
import zipfile
from pathlib import Path

from src.core.file_manager import FileManager


class TestFileManager(unittest.TestCase):
    """ファイル整理の主要補助機能を確認する。"""

    def test_preview_batch_rename_returns_before_after_pairs(self):
        """一括リネームのプレビューが変更前後を返せる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "report_old.txt").write_text("a", encoding="utf-8")
            rows = FileManager.preview_batch_rename(str(root), "old", "new")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["before"], "report_old.txt")
            self.assertEqual(rows[0]["after"], "report_new.txt")

    def test_create_template_file_writes_default_content(self):
        """テンプレート作成で既定内容を書き込める。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            created = FileManager.create_template_file(temp_dir, "markdown", "memo.md")
            text = Path(created).read_text(encoding="utf-8")
            self.assertIn("# 新規ドキュメント", text)

    def test_list_archive_entries_reads_zip_contents(self):
        """ZIP の内容一覧を取得できる。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "sample.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("docs/readme.txt", "hello")
            payload = FileManager.list_archive_entries(str(archive_path))
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["entries"][0]["name"], "docs/readme.txt")


if __name__ == "__main__":
    unittest.main()
