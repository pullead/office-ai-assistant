# -*- coding: utf-8 -*-
"""
Web抽出モジュール - URLからテキスト抽出・PDF保存・電子書籍変換
"""
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from popdf import html_to_pdf  # python-officeの機能（実際には簡易実装）


class WebExtractor:
    """Webページからコンテンツを抽出し、PDFや電子書籍形式で保存"""

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "web_output"
        self.output_dir.mkdir(exist_ok=True)

    def extract_text(self, url: str) -> str:
        """URLから本文テキストを抽出"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        # スクリプト・スタイルを除去
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text

    def save_as_pdf(self, url: str, output_name: str = "webpage.pdf") -> str:
        """WebページをPDFとして保存（popdf利用）"""
        text = self.extract_text(url)
        # 簡易的にテキストをPDFに変換（実際にはpopdfのhtml_to_pdfを使用するのが理想）
        # ここではpopdfが存在する前提で実装
        from popdf import txt_to_pdf
        pdf_path = self.output_dir / output_name
        txt_to_pdf(text, str(pdf_path))
        return str(pdf_path)

    def save_as_epub(self, url: str, output_name: str = "book.epub") -> str:
        """
        URLからEPUB電子書籍を生成（簡易実装）
        実際にはEbookLibなどが必要だが、ここではプレースホルダ
        """
        # 完全なEPUB生成は複雑なため、サンプルとしてテキスト保存
        text = self.extract_text(url)
        epub_path = self.output_dir / output_name.replace('.epub', '.txt')
        with open(epub_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return str(epub_path) + " (テキストとして保存)"

    def batch_extract(self, urls: list) -> list:
        """複数URLを一括処理"""
        results = []
        for idx, url in enumerate(urls):
            try:
                text = self.extract_text(url)
                out_file = self.output_dir / f"extract_{idx + 1}.txt"
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                results.append(str(out_file))
            except Exception as e:
                results.append(f"エラー: {url} - {str(e)}")
        return results