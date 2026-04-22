# -*- coding: utf-8 -*-
"""ファイル操作の小さな補助関数。"""

import os
from pathlib import Path


def ensure_dir(path: str | Path):
    """ディレクトリがなければ作成する。"""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_size(path: str | Path) -> str:
    """ファイルサイズを読みやすい形式で返す。"""
    size = os.path.getsize(path)
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
