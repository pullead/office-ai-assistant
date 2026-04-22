# -*- coding: utf-8 -*-
"""ファイル管理と検索を行うモジュール。"""

from __future__ import annotations

import hashlib
import shutil
from collections import Counter, defaultdict
from pathlib import Path


class FileManager:
    """ファイル整理、検索、重複検出をまとめて扱う。"""

    @staticmethod
    def organize_by_extension(directory: str) -> str:
        """拡張子ごとにファイルを整理する。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが見つかりません: {directory}"

        moved_count = 0
        for file in dir_path.iterdir():
            if not file.is_file():
                continue
            ext = file.suffix[1:].lower() if file.suffix else "no_extension"
            target_dir = dir_path / ext
            target_dir.mkdir(exist_ok=True)
            target_path = target_dir / file.name
            if target_path.exists():
                target_path = target_dir / f"{file.stem}_copy{file.suffix}"
            shutil.move(str(file), str(target_path))
            moved_count += 1

        return f"{moved_count} 件のファイルを拡張子ごとに整理しました。"

    @staticmethod
    def batch_rename(directory: str, pattern: str, replacement: str) -> str:
        """ファイル名の一括置換を行う。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが見つかりません: {directory}"

        count = 0
        for file in dir_path.iterdir():
            if not file.is_file():
                continue
            new_name = file.name.replace(pattern, replacement)
            if new_name == file.name:
                continue
            file.rename(file.parent / new_name)
            count += 1

        return f"{count} 件のファイル名を変更しました。"

    @staticmethod
    def search_content(directory: str, keyword: str, limit: int = 200) -> list[str]:
        """テキスト系ファイルの中身からキーワード検索を行う。"""
        results = []
        dir_path = Path(directory)
        if not dir_path.exists():
            return results

        for file in dir_path.rglob("*"):
            if len(results) >= limit:
                break
            if not file.is_file():
                continue
            if file.suffix.lower() not in {".txt", ".md", ".py", ".csv", ".json", ".log"}:
                continue

            try:
                content = FileManager._read_text_with_fallback(file)
            except OSError:
                continue

            if keyword.lower() in content.lower():
                results.append(str(file))
        return results

    @staticmethod
    def search_files_by_name(directory: str, keyword: str, limit: int = 300) -> list[str]:
        """ファイル名ベースで検索する。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        hits = []
        for file in dir_path.rglob("*"):
            if len(hits) >= limit:
                break
            if file.is_file() and keyword.lower() in file.name.lower():
                hits.append(str(file))
        return hits

    @staticmethod
    def summarize_directory(directory: str) -> str:
        """ディレクトリ全体の概要を返す。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが見つかりません: {directory}"

        files = [path for path in dir_path.rglob("*") if path.is_file()]
        ext_counter = Counter(path.suffix.lower() or "[拡張子なし]" for path in files)
        largest = sorted(files, key=lambda path: path.stat().st_size, reverse=True)[:5]

        lines = [
            "フォルダサマリー",
            f"対象: {dir_path}",
            f"ファイル数: {len(files)}",
            f"フォルダ数: {sum(1 for path in dir_path.rglob('*') if path.is_dir())}",
            "",
            "拡張子トップ 8",
        ]
        for ext, count in ext_counter.most_common(8):
            lines.append(f"- {ext}: {count}")

        if largest:
            lines.append("")
            lines.append("大きいファイル")
            for path in largest:
                lines.append(f"- {path.relative_to(dir_path)} ({FileManager._format_size(path.stat().st_size)})")
        return "\n".join(lines)

    @staticmethod
    def build_directory_report(directory: str, max_depth: int = 2) -> dict:
        """可視化向けの詳細レポートを返す。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")

        files = [path for path in dir_path.rglob("*") if path.is_file()]
        ext_counter = Counter(path.suffix.lower() or "[拡張子なし]" for path in files)
        total_size = sum(path.stat().st_size for path in files)

        top_folders = []
        for child in sorted([item for item in dir_path.iterdir() if item.is_dir()], key=lambda item: item.name.lower()):
            file_count = sum(1 for item in child.rglob("*") if item.is_file())
            folder_size = sum(item.stat().st_size for item in child.rglob("*") if item.is_file())
            top_folders.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "files": file_count,
                    "size": folder_size,
                }
            )

        return {
            "directory": str(dir_path),
            "file_count": len(files),
            "folder_count": sum(1 for path in dir_path.rglob("*") if path.is_dir()),
            "total_size": total_size,
            "extensions": ext_counter.most_common(12),
            "largest_files": [
                {"path": str(path), "size": path.stat().st_size}
                for path in sorted(files, key=lambda item: item.stat().st_size, reverse=True)[:12]
            ],
            "top_folders": top_folders[:12],
            "tree_preview": FileManager._build_tree_preview(dir_path, max_depth=max_depth),
        }

    @staticmethod
    def find_duplicate_files(directory: str) -> str:
        """内容が同じ重複ファイルを検出する。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが見つかりません: {directory}"

        grouped_by_size = defaultdict(list)
        for path in dir_path.rglob("*"):
            if path.is_file():
                grouped_by_size[path.stat().st_size].append(path)

        duplicates = []
        for paths in grouped_by_size.values():
            if len(paths) < 2:
                continue

            hashes = defaultdict(list)
            for path in paths:
                digest = FileManager._file_hash(path)
                hashes[digest].append(path)

            for same_hash_paths in hashes.values():
                if len(same_hash_paths) > 1:
                    duplicates.append(same_hash_paths)

        if not duplicates:
            return "重複ファイルは見つかりませんでした。"

        lines = ["重複ファイル一覧", ""]
        for index, group in enumerate(duplicates[:10], start=1):
            lines.append(f"{index}. {FileManager._format_size(group[0].stat().st_size)}")
            for path in group:
                lines.append(f"- {path}")
        return "\n".join(lines)

    @staticmethod
    def classify_paths(paths: list[str]) -> dict[str, list[str]]:
        """パス一覧を拡張子ごとに分類する。"""
        grouped: dict[str, list[str]] = defaultdict(list)
        for raw_path in paths:
            path = Path(raw_path)
            key = path.suffix.lower() or "[拡張子なし]"
            grouped[key].append(raw_path)
        return dict(grouped)

    @staticmethod
    def _build_tree_preview(root: Path, max_depth: int = 2) -> list[str]:
        """表示用の簡易ツリーを生成する。"""
        lines: list[str] = []

        def walk(current: Path, depth: int):
            if depth > max_depth:
                return
            children = sorted(current.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
            for child in children[:25]:
                prefix = "  " * depth + ("- " if child.is_file() else "+ ")
                lines.append(f"{prefix}{child.name}")
                if child.is_dir():
                    walk(child, depth + 1)

        walk(root, 0)
        return lines[:120]

    @staticmethod
    def _file_hash(path: Path) -> str:
        """ファイル内容のハッシュ値を返す。"""
        hasher = hashlib.md5()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _read_text_with_fallback(path: Path) -> str:
        """文字コード候補を切り替えてテキストを読む。"""
        encodings = ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1")
        last_error = None
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as error:
                last_error = error
        if last_error:
            raise last_error
        return ""

    @staticmethod
    def _format_size(size: int) -> str:
        """バイト数を見やすい単位に変換する。"""
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
