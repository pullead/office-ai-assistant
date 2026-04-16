# -*- coding: utf-8 -*-
"""
アイコン自動生成スクリプト
実行すると src/ui/resources/icons/ に必要なアイコンファイルが作成されます。
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_icon(filename, text, color="#4a6fa5", size=64):
    """シンプルなテキストアイコンを生成"""
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 背景円
    draw.ellipse((4, 4, size - 4, size - 4), fill=color)

    # テキスト（日本語不可の場合は英字1文字）
    try:
        # 日本語フォントを試す
        font = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 32)
    except:
        font = ImageFont.load_default()

    # テキストの中央配置
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 4
    draw.text((x, y), text, fill="white", font=font)

    img.save(filename)


def main():
    # 出力先ディレクトリ
    icon_dir = Path("src/ui/resources/icons")
    icon_dir.mkdir(parents=True, exist_ok=True)

    # 各タブ用アイコン（ファイル名, 表示テキスト, 色）
    icons = [
        ("ai.png", "AI", "#6c5ce7"),
        ("ocr.png", "OCR", "#00b894"),
        ("viz.png", "V", "#0984e3"),
        ("web.png", "W", "#e17055"),
        ("email.png", "@", "#d63031"),
        ("file.png", "F", "#2d3436"),
        ("settings.png", "S", "#636e72"),
    ]

    for filename, text, color in icons:
        filepath = icon_dir / filename
        create_icon(str(filepath), text, color)
        print(f"生成: {filepath}")

    print("\nすべてのアイコンを生成しました。")
    print("注意: アイコンは簡易的なものです。必要に応じて差し替えてください。")


if __name__ == "__main__":
    main()