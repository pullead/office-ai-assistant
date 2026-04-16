# -*- coding: utf-8 -*-
"""
ファイル管理モジュール - 自動整理・一括リネーム・内容検索
"""
import os
import shutil
from pathlib import Path
import re


class FileManager:
    """ファイル操作ユーティリティ"""

    @staticmethod
    def organize_by_extension(directory: str) -> str:
        """拡張子別にファイルを整理"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが存在しません: {directory}"

        for file in dir_path.iterdir():
            if file.is_file():
                ext = file.suffix[1:] if file.suffix else "no_extension"
                target_dir = dir_path / ext
                target_dir.mkdir(exist_ok=True)
                shutil.move(str(file), str(target_dir / file.name))
        return f"整理完了: {directory} 内のファイルを拡張子別に分類しました。"

    @staticmethod
    def batch_rename(directory: str, pattern: str, replacement: str) -> str:
        """
        一括リネーム（例: pattern='old', replacement='new'）
        """
        dir_path = Path(directory)
        count = 0
        for file in dir_path.iterdir():
            if file.is_file():
                new_name = file.name.replace(pattern, replacement)
                if new_name != file.name:
                    new_path = file.parent / new_name
                    file.rename(new_path)
                    count += 1
        return f"{count}個のファイルをリネームしました。"

    @staticmethod
    def search_content(directory: str, keyword: str) -> list:
        """ディレクトリ内のテキストファイルからキーワード検索"""
        results = []
        dir_path = Path(directory)
        for file in dir_path.rglob("*"):
            if file.is_file() and file.suffix in ['.txt', '.md', '.py', '.csv', '.json']:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        if keyword in f.read():
                            results.append(str(file))
                except:
                    pass
        return results