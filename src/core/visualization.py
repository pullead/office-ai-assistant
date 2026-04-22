# -*- coding: utf-8 -*-
"""データ可視化処理をまとめたモジュール。"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DataVisualizer:
    """表データやテキストから可視化結果を生成する。"""

    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "output" / "visualization"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_visualization(
        self,
        file_path: str,
        mode: str,
        x_col: str | None = None,
        y_col: str | None = None,
    ) -> dict[str, Any]:
        """ファイル種別に応じて可視化を生成する。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        if mode == "wordcloud":
            text = self._load_text_source(path)
            image_path = self.generate_wordcloud(text, output_name=f"{path.stem}_wordcloud.png")
            return {
                "kind": "image",
                "output_path": image_path,
                "summary": self._build_wordcloud_summary(path, text),
                "dataframe": None,
            }

        dataframe = self.load_table(path)
        if dataframe.empty:
            raise ValueError("入力データが空のため、可視化を生成できません。")

        x_col, y_col = self._resolve_columns(dataframe, x_col, y_col)
        html_path = self._create_plotly_chart(dataframe, path.stem, mode, x_col, y_col)

        return {
            "kind": "html",
            "output_path": html_path,
            "summary": self._build_table_summary(path, dataframe, x_col, y_col, mode),
            "dataframe": dataframe,
            "x_col": x_col,
            "y_col": y_col,
        }

    def load_table(self, path: Path):
        """CSV / Excel を DataFrame として読み込む。"""
        _plt, pd, _wordcloud, _plotly = self._load_dependencies()

        suffix = path.suffix.lower()
        if suffix == ".csv":
            return self._read_csv_with_fallback(path, pd)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        raise ValueError("表データとして読み込めるのは CSV / Excel のみです。")

    def generate_wordcloud(self, text: str, output_name: str = "wordcloud.png") -> str:
        """テキストからワードクラウド画像を生成する。"""
        plt, _pd, wordcloud_cls, _plotly = self._load_dependencies()
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("ワードクラウド用のテキストが空です。")

        stopwords = {
            "こと",
            "ため",
            "これ",
            "それ",
            "です",
            "ます",
            "した",
            "して",
            "ある",
            "いる",
        }

        wc = wordcloud_cls(
            font_path=self._get_japanese_font_path(),
            width=1400,
            height=900,
            background_color="white",
            stopwords=stopwords,
            colormap="magma",
        ).generate(cleaned_text)

        fig, ax = plt.subplots(figsize=(12, 8))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout()

        return self._save_figure(fig, output_name)

    def _create_plotly_chart(self, dataframe, source_name: str, mode: str, x_col: str, y_col: str) -> str:
        """Plotly のインタラクティブな HTML を生成する。"""
        _plt, _pd, _wordcloud, plotly = self._load_dependencies()

        df = dataframe.copy()
        df[x_col] = df[x_col].astype(str)

        if mode == "bar":
            fig = plotly.bar(
                df,
                x=x_col,
                y=y_col,
                color=y_col,
                text_auto=".2s",
                title=f"{source_name} | 棒グラフ",
            )
        elif mode == "line":
            fig = plotly.line(
                df,
                x=x_col,
                y=y_col,
                markers=True,
                title=f"{source_name} | 折れ線グラフ",
            )
        elif mode == "pie":
            fig = plotly.pie(
                df,
                names=x_col,
                values=y_col,
                hole=0.35,
                title=f"{source_name} | 円グラフ",
            )
        else:
            raise ValueError("未対応の可視化モードです。")

        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#fcfaf6",
            plot_bgcolor="#ffffff",
            font={"family": "Yu Gothic UI, Meiryo, sans-serif", "size": 14},
            margin={"l": 30, "r": 20, "t": 70, "b": 30},
            legend={"orientation": "h", "y": -0.18},
            hoverlabel={"bgcolor": "#0f172a", "font_size": 13},
        )
        fig.update_traces(
            hovertemplate=f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<extra></extra>"
            if mode != "pie"
            else f"{x_col}: %{{label}}<br>{y_col}: %{{value}}<br>比率: %{{percent}}<extra></extra>"
        )

        if mode in {"bar", "line"}:
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridcolor="#e7e5e4")

        html_path = self.output_dir / f"{source_name}_{mode}.html"
        html_body = fig.to_html(include_plotlyjs="cdn", full_html=False)
        html_path.write_text(
            (
                "<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
                "<title>可視化結果</title>"
                "<style>"
                "body{margin:0;padding:18px;background:linear-gradient(180deg,#fffdf8,#f4efe7);"
                "font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#1f2937;}"
                ".card{background:#ffffff;border-radius:20px;padding:18px;"
                "box-shadow:0 18px 48px rgba(15,23,42,.10);}"
                ".note{margin:0 0 12px 0;color:#475569;font-size:14px;}"
                "</style></head><body><div class='card'>"
                "<p class='note'>マウスオーバーで詳細値を確認できます。拡大・縮小や凡例クリックにも対応しています。</p>"
                f"{html_body}</div></body></html>"
            ),
            encoding="utf-8",
        )
        return str(html_path)

    def _build_table_summary(self, path: Path, dataframe, x_col: str, y_col: str, mode: str) -> str:
        """グラフ用の要約文を作る。"""
        series = dataframe[y_col].dropna()
        top_rows = dataframe[[x_col, y_col]].sort_values(by=y_col, ascending=False).head(5)
        lines = [
            f"可視化モード: {self._mode_label(mode)}",
            f"対象ファイル: {path}",
            f"行数: {len(dataframe)}",
            f"列数: {len(dataframe.columns)}",
            f"軸: {x_col} / {y_col}",
            "",
            "指標サマリー",
            f"- 平均値: {series.mean():.3f}",
            f"- 最小値: {series.min():.3f}",
            f"- 最大値: {series.max():.3f}",
            f"- 欠損数: {int(dataframe[y_col].isna().sum())}",
            "",
            "上位 5 件",
        ]
        for _, row in top_rows.iterrows():
            lines.append(f"- {row[x_col]}: {row[y_col]}")
        return "\n".join(lines)

    def _build_wordcloud_summary(self, path: Path, text: str) -> str:
        """ワードクラウド用の要約文を作る。"""
        tokens = self._tokenize(text)
        top_tokens = self._top_tokens(tokens)
        lines = [
            f"可視化モード: ワードクラウド",
            f"対象ファイル: {path}",
            f"文字数: {len(text)}",
            f"抽出語数: {len(tokens)}",
            "",
            "頻出語",
        ]
        lines.extend(f"- {token}: {count}" for token, count in top_tokens)
        return "\n".join(lines)

    def _load_text_source(self, path: Path) -> str:
        """テキスト系入力を文字列として読み込む。"""
        suffix = path.suffix.lower()
        if suffix == ".txt":
            return self._read_text_with_fallback(path)
        if suffix == ".csv":
            dataframe = self.load_table(path)
            return " ".join(dataframe.astype(str).fillna("").values.flatten())
        if suffix in {".xlsx", ".xls"}:
            dataframe = self.load_table(path)
            return " ".join(dataframe.astype(str).fillna("").values.flatten())
        raise ValueError("ワードクラウドは TXT / CSV / Excel のみ対応しています。")

    def _read_csv_with_fallback(self, path: Path, pd_module):
        """CSV を文字コードの候補を切り替えながら読み込む。"""
        encodings = ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1")
        last_error = None
        for encoding in encodings:
            try:
                return pd_module.read_csv(path, encoding=encoding)
            except UnicodeDecodeError as error:
                last_error = error
            except Exception as error:
                last_error = error
        raise ValueError(f"CSV の読み込みに失敗しました: {last_error}") from last_error

    def _read_text_with_fallback(self, path: Path) -> str:
        """テキストを文字コード候補で読み込む。"""
        encodings = ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1")
        last_error = None
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as error:
                last_error = error
        raise ValueError(f"テキストの読み込みに失敗しました: {last_error}") from last_error

    def _resolve_columns(self, dataframe, first_col: str | None, second_col: str | None) -> tuple[str, str]:
        """グラフ用の列を自動判定する。"""
        _plt, pd, _wordcloud, _plotly = self._load_dependencies()

        if first_col is None:
            first_col = str(dataframe.columns[0])
        if second_col is None:
            numeric_columns = [col for col in dataframe.columns if pd.api.types.is_numeric_dtype(dataframe[col])]
            if not numeric_columns:
                raise ValueError("数値列が見つからないため、グラフを生成できません。")
            second_col = str(numeric_columns[0])

        if first_col not in dataframe.columns or second_col not in dataframe.columns:
            raise ValueError("指定された列名がデータ内に存在しません。")

        return first_col, second_col

    def _save_figure(self, fig, output_name: str) -> str:
        """Matplotlib 図を保存する。"""
        output_path = self.output_dir / output_name
        fig.savefig(output_path, dpi=160, bbox_inches="tight")
        import matplotlib.pyplot as plt

        plt.close(fig)
        return str(output_path)

    def _get_japanese_font_path(self) -> str | None:
        """使用可能な日本語フォントを探す。"""
        candidates = [
            Path("C:/Windows/Fonts/meiryo.ttc"),
            Path("C:/Windows/Fonts/YuGothM.ttc"),
            Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return None

    def _tokenize(self, text: str) -> list[str]:
        """簡易的な単語抽出を行う。"""
        import re

        return re.findall(r"[A-Za-z0-9_\u3041-\u30ff\u4e00-\u9fff]{2,}", text)

    def _top_tokens(self, tokens: list[str]) -> list[tuple[str, int]]:
        """頻出語の上位を返す。"""
        from collections import Counter

        stopwords = {"です", "ます", "した", "して", "こと", "ため", "これ", "それ"}
        counter = Counter(token for token in tokens if token not in stopwords)
        return counter.most_common(12)

    def _mode_label(self, mode: str) -> str:
        """内部モード名を表示向けに変換する。"""
        return {
            "bar": "棒グラフ",
            "line": "折れ線グラフ",
            "pie": "円グラフ",
            "wordcloud": "ワードクラウド",
        }.get(mode, mode)

    def _load_dependencies(self):
        """必要なライブラリを遅延読み込みする。"""
        try:
            import matplotlib.pyplot as plt
            import pandas as pd
            import plotly.express as px
            from wordcloud import WordCloud
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "可視化機能には matplotlib・pandas・plotly・wordcloud が必要です。"
            ) from error

        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [
            "Meiryo",
            "Yu Gothic",
            "Hiragino Sans",
            "Noto Sans CJK JP",
            "DejaVu Sans",
        ]
        return plt, pd, WordCloud, px
