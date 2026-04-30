# -*- coding: utf-8 -*-
"""ファイル管理と検索を行うモジュール。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import time
import zipfile
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
    def batch_rename(directory: str, pattern: str, replacement: str, use_regex: bool = False) -> str:
        """ファイル名の一括置換を行う。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return f"ディレクトリが見つかりません: {directory}"

        count = 0
        for file in dir_path.iterdir():
            if not file.is_file():
                continue
            new_name = FileManager._build_renamed_name(file.name, pattern, replacement, use_regex)
            if new_name == file.name:
                continue
            file.rename(file.parent / new_name)
            count += 1

        return f"{count} 件のファイル名を変更しました。"

    @staticmethod
    def preview_batch_rename(
        directory: str,
        pattern: str,
        replacement: str,
        use_regex: bool = False,
        limit: int = 200,
    ) -> list[dict]:
        """一括リネームのプレビュー一覧を返す。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        rows = []
        for file in sorted(dir_path.iterdir(), key=lambda item: item.name.lower()):
            if len(rows) >= limit:
                break
            if not file.is_file():
                continue
            new_name = FileManager._build_renamed_name(file.name, pattern, replacement, use_regex)
            if new_name == file.name:
                continue
            rows.append(
                {
                    "before": file.name,
                    "after": new_name,
                    "path": str(file),
                    "size": file.stat().st_size,
                }
            )
        return rows

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
    def build_space_lens_report(directory: str, output_dir: str | None = None, max_items: int = 180) -> dict:
        """Space Lens 向けの容量可視化データを返す。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")

        nodes = FileManager._collect_storage_nodes(dir_path, max_items=max_items)
        summary_rows = []
        nodes.sort(key=lambda item: item["size"], reverse=True)
        visible_nodes = nodes[:max_items]
        for item in visible_nodes[:25]:
            summary_rows.append(
                {
                    "name": item["name"],
                    "path": item["path"],
                    "size": item["size"],
                    "items": item["items"],
                    "kind": item["kind"],
                }
            )

        html_path = FileManager._create_space_lens_html(dir_path, visible_nodes, output_dir)
        largest_files = [item for item in visible_nodes if item["kind"] == "file"][:12]
        top_folders = [item for item in visible_nodes if item["kind"] == "folder"][:12]
        extension_totals = Counter()
        for item in visible_nodes:
            suffix = Path(item["path"]).suffix.lower() or "[拡張子なし]"
            extension_totals[suffix] += item["size"]
        return {
            "directory": str(dir_path),
            "total_size": sum(item["size"] for item in nodes),
            "items": len(nodes),
            "summary_rows": summary_rows,
            "largest_items": visible_nodes[:20],
            "largest_files": largest_files,
            "top_folders": top_folders,
            "extension_totals": extension_totals.most_common(10),
            "html_path": html_path,
        }

    @staticmethod
    def find_large_old_files(
        directory: str,
        min_size_mb: int = 100,
        older_than_days: int = 180,
        limit: int = 200,
    ) -> list[dict]:
        """大容量かつ古いファイルを抽出する。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        threshold_size = min_size_mb * 1024 * 1024
        threshold_time = time.time() - older_than_days * 24 * 60 * 60
        results = []
        for path in dir_path.rglob("*"):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size < threshold_size or stat.st_atime > threshold_time:
                continue
            results.append(
                {
                    "path": str(path),
                    "size": stat.st_size,
                    "last_access_days": int((time.time() - stat.st_atime) // (24 * 60 * 60)),
                    "last_modified_days": int((time.time() - stat.st_mtime) // (24 * 60 * 60)),
                }
            )
        results.sort(key=lambda item: (item["size"], item["last_access_days"]), reverse=True)
        return results[:limit]

    @staticmethod
    def shred_files(paths: list[str], passes: int = 1) -> str:
        """ファイルを上書き後に削除する。"""
        shredded = 0
        skipped = 0
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                skipped += 1
                continue
            try:
                FileManager._overwrite_file(path, passes=passes)
                path.unlink()
                shredded += 1
            except OSError:
                skipped += 1
        return f"完全削除: {shredded} 件 / スキップ: {skipped} 件"

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
    def create_template_file(directory: str, template_key: str, file_name: str, custom_text: str = "") -> str:
        """テンプレートから新規ファイルを作成する。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")

        templates = {
            "text": "新規テキストファイル\n",
            "markdown": "# 新規ドキュメント\n\n## 概要\n\n- 項目\n",
            "csv": "項目,内容,備考\n",
            "json": json.dumps({"title": "new file", "items": []}, ensure_ascii=False, indent=2) + "\n",
            "python": "# -*- coding: utf-8 -*-\n\"\"\"新規スクリプト。\"\"\"\n\n\ndef main():\n    print(\"hello\")\n\n\nif __name__ == \"__main__\":\n    main()\n",
        }
        content = custom_text if custom_text.strip() else templates.get(template_key, "")
        target = dir_path / file_name
        if target.exists():
            raise FileExistsError(f"同名ファイルが既に存在します: {target.name}")
        target.write_text(content, encoding="utf-8")
        return str(target)

    @staticmethod
    def list_archive_entries(archive_path: str, limit: int = 400) -> dict:
        """圧縮ファイル内のエントリー一覧を返す。"""
        path = Path(archive_path)
        if not path.exists():
            raise FileNotFoundError(f"圧縮ファイルが見つかりません: {archive_path}")

        entries = []
        lower_name = path.name.lower()
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist()[:limit]:
                    entries.append(
                        {
                            "name": info.filename,
                            "size": info.file_size,
                            "compressed": info.compress_size,
                        }
                    )
        elif tarfile.is_tarfile(path) or any(
            lower_name.endswith(suffix) for suffix in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
        ):
            with tarfile.open(path) as archive:
                for member in archive.getmembers()[:limit]:
                    if not member.isfile():
                        continue
                    entries.append(
                        {
                            "name": member.name,
                            "size": member.size,
                            "compressed": member.size,
                        }
                    )
        else:
            raise ValueError("現在のバージョンでは ZIP / TAR 系の閲覧に対応しています。")

        return {
            "archive": str(path),
            "count": len(entries),
            "entries": entries,
        }

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
    def _collect_storage_nodes(root: Path, max_items: int = 220) -> list[dict]:
        """容量可視化向けのノード一覧を収集する。"""
        nodes = []
        for current in root.rglob("*"):
            try:
                if current.is_dir():
                    size = FileManager._calculate_directory_size(current)
                    if size <= 0:
                        continue
                    item_count = sum(1 for entry in current.rglob("*") if entry.is_file())
                    kind = "folder"
                elif current.is_file():
                    size = current.stat().st_size
                    item_count = 1
                    kind = "file"
                else:
                    continue
            except OSError:
                continue
            relative = str(current.relative_to(root))
            depth = len(current.relative_to(root).parts)
            nodes.append(
                {
                    "path": str(current),
                    "name": current.name,
                    "relative": relative,
                    "size": size,
                    "items": item_count,
                    "kind": kind,
                    "depth": depth,
                }
            )
        nodes.sort(key=lambda item: (item["size"], -item["depth"]), reverse=True)
        return nodes[:max_items]

    @staticmethod
    def _file_hash(path: Path) -> str:
        """ファイル内容のハッシュ値を返す。"""
        hasher = hashlib.md5()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _calculate_directory_size(path: Path) -> int:
        """ディレクトリ配下の総サイズを返す。"""
        total = 0
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    continue
        return total

    @staticmethod
    def _create_space_lens_html(root: Path, nodes: list[dict], output_dir: str | None) -> str | None:
        """容量マップ HTML を生成する。"""
        if not nodes:
            return None
        try:
            import plotly.express as px
        except ModuleNotFoundError:
            return None

        labels = []
        parents = []
        values = []
        custom = []

        root_label = root.name or str(root)
        labels.append(root_label)
        parents.append("")
        values.append(sum(item["size"] for item in nodes))
        custom.append(f"{len(nodes)} 項目")

        for item in nodes:
            labels.append(item["name"])
            parents.append(root_label)
            values.append(item["size"])
            custom.append(f"{item['items']} 項目 / {item['kind']}")

        figure = px.treemap(
            names=labels,
            parents=parents,
            values=values,
            custom_data=custom,
            color=values,
            color_continuous_scale=["#6ee7f9", "#60a5fa", "#8b5cf6", "#ec4899"],
        )
        figure.update_traces(
            root_color="#2b1d59",
            textinfo="label+value",
            hovertemplate="名前: %{label}<br>サイズ: %{value}<br>%{customdata}<extra></extra>",
        )
        figure.update_layout(
            paper_bgcolor="#140d26",
            plot_bgcolor="#140d26",
            margin={"l": 12, "r": 12, "t": 20, "b": 12},
            font={"family": "Yu Gothic UI, Meiryo, sans-serif", "color": "#f8fafc"},
            coloraxis_showscale=False,
        )

        target_dir = Path(output_dir) if output_dir else Path("output") / "space_lens"
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / f"{root_label}_space_lens.html"
        html_body = figure.to_html(include_plotlyjs="cdn", full_html=False)
        output_path.write_text(
            (
                "<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
                "<title>Space Lens</title>"
                "<style>"
                "body{margin:0;padding:18px;background:radial-gradient(circle at top,#2c165c,#12081f 62%,#09050f);"
                "font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#f8fafc;}"
                ".shell{display:grid;grid-template-columns:360px 1fr;gap:18px;min-height:92vh;}"
                ".panel,.map{background:rgba(255,255,255,0.08);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,0.12);"
                "border-radius:28px;box-shadow:0 20px 60px rgba(0,0,0,0.25);}"
                ".panel{padding:20px;}.panel h1{font-size:22px;margin:0 0 14px 0;}"
                ".metric{padding:14px 16px;border-radius:18px;background:rgba(255,255,255,0.06);margin-bottom:10px;}"
                ".item{display:flex;justify-content:space-between;gap:12px;padding:10px 12px;border-radius:14px;"
                "background:rgba(255,255,255,0.04);margin-bottom:8px;transition:transform .18s ease,background .18s ease;}"
                ".item:hover{transform:translateX(4px);background:rgba(255,255,255,0.09);}"
                ".map{padding:12px;}"
                "</style></head><body>"
                "<div class='shell'>"
                "<section class='panel'>"
                f"<h1>スペースレンズ</h1>"
                f"<div class='metric'>対象: {root}</div>"
                f"<div class='metric'>表示項目数: {len(nodes)}</div>"
                f"<div class='metric'>総容量: {FileManager._format_size(sum(item['size'] for item in nodes))}</div>"
                + "".join(
                    (
                        "<div class='item'>"
                        f"<span>{item['name']}</span>"
                        f"<span>{FileManager._format_size(item['size'])}</span>"
                        "</div>"
                    )
                    for item in nodes[:18]
                )
                + "</section><section class='map'>"
                f"{html_body}</section></div></body></html>"
            ),
            encoding="utf-8",
        )
        return str(output_path)

    @staticmethod
    def _build_renamed_name(file_name: str, pattern: str, replacement: str, use_regex: bool) -> str:
        """置換条件から新しいファイル名を返す。"""
        if use_regex:
            try:
                return re.sub(pattern, replacement, file_name)
            except re.error:
                return file_name
        return file_name.replace(pattern, replacement)

    @staticmethod
    def _overwrite_file(path: Path, passes: int = 1):
        """ファイルを乱数で上書きする。"""
        size = path.stat().st_size
        if size <= 0:
            return
        chunk_size = 1024 * 1024
        with open(path, "r+b") as handle:
            for _ in range(max(1, passes)):
                handle.seek(0)
                remaining = size
                while remaining > 0:
                    write_size = min(chunk_size, remaining)
                    handle.write(os.urandom(write_size))
                    remaining -= write_size
                handle.flush()

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
