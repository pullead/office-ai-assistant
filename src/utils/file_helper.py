# -*- coding: utf-8 -*-
"""ファイル操作ヘルパー（共通関数）"""
import os
import shutil
from pathlib import Path

def ensure_dir(path):
    """ディレクトリが存在することを保証"""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_file_size(path):
    """ファイルサイズを人間可読な形式で返す"""
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"