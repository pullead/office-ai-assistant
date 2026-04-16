# -*- coding: utf-8 -*-
"""
データ可視化モジュール - グラフ・ワードクラウド生成
"""
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
from pathlib import Path


class DataVisualizer:
    """Excelデータからグラフ、テキストからワードクラウドを生成"""

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "output"
        self.output_dir.mkdir(exist_ok=True)
        # 日本語フォント対応（macOS/Windows）
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Hiragino Maru Gothic', 'Meiryo', 'SimHei']

    def excel_to_chart(self, excel_path: str, sheet_name: str = 0, x_col: str = None, y_col: str = None) -> str:
        """
        Excelデータから棒グラフを作成
        Returns: 保存された画像ファイルのパス
        """
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        # 自動的に最初の数値列を選択（簡易）
        if x_col is None:
            x_col = df.columns[0]
        if y_col is None:
            # 最初の数値列を探す
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    y_col = col
                    break

        plt.figure(figsize=(10, 6))
        plt.bar(df[x_col], df[y_col])
        plt.title(f"{y_col} の棒グラフ")
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.xticks(rotation=45)
        plt.tight_layout()

        output_path = self.output_dir / "chart.png"
        plt.savefig(output_path)
        plt.close()
        return str(output_path)

    def generate_wordcloud(self, text: str, output_name: str = "wordcloud.png") -> str:
        """
        テキストからワードクラウドを生成
        """
        # 日本語対応ストップワード（簡易）
        stopwords = set(["これ", "それ", "あれ", "こと", "もの", "ため", "そう", "する", "なる", "いる", "ある"])

        wc = WordCloud(
            font_path=self._get_japanese_font_path(),
            width=800,
            height=600,
            background_color='white',
            stopwords=stopwords,
            colormap='viridis'
        ).generate(text)

        plt.figure(figsize=(10, 6))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')

        output_path = self.output_dir / output_name
        plt.savefig(output_path)
        plt.close()
        return str(output_path)

    def textfile_to_wordcloud(self, txt_path: str) -> str:
        """テキストファイルを読み込みワードクラウド生成"""
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.generate_wordcloud(text)

    def _get_japanese_font_path(self) -> str:
        """日本語フォントのパスを自動検出"""
        import sys
        if sys.platform == 'darwin':  # macOS
            return '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
        elif sys.platform == 'win32':
            return 'C:\\Windows\\Fonts\\meiryo.ttc'
        else:
            return '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'