# -*- coding: utf-8 -*-
"""
Web 抽出モジュール。
URL から本文を抽出し、テキスト保存や PDF 保存を行う。
"""

from pathlib import Path

import requests
from bs4 import BeautifulSoup


class WebExtractor:
    """Web ページの本文を扱うクラス。"""

    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "web_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_text(self, url: str) -> str:
        """URL から本文テキストを抽出する。"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        compact_lines = [line for line in lines if line]
        return "\n".join(compact_lines)

    def save_as_pdf(self, url: str, output_name: str = "webpage.pdf") -> str:
        """抽出テキストを PDF として保存する。"""
        from popdf import txt_to_pdf

        text = self.extract_text(url)
        output_path = self.output_dir / output_name
        txt_to_pdf(text, str(output_path))
        return str(output_path)

    def save_as_epub(self, url: str, output_name: str = "book.epub") -> str:
        """
        EPUB ライブラリ未導入環境でも使えるよう、
        まずはテキスト保存を代替手段とする。
        """
        text = self.extract_text(url)
        output_path = self.output_dir / output_name.replace(".epub", ".txt")
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(text)
        return str(output_path)

    def batch_extract(self, urls: list[str]) -> list[str]:
        """複数 URL を連続で抽出する。"""
        results = []
        for index, url in enumerate(urls, start=1):
            try:
                text = self.extract_text(url)
                output_path = self.output_dir / f"extract_{index}.txt"
                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(text)
                results.append(str(output_path))
            except Exception as error:
                results.append(f"エラー: {url} - {error}")
        return results
