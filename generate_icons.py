# -*- coding: utf-8 -*-
"""
アプリ用アイコン生成スクリプト。
温かみのある配色とシンプルなモノグラムで、統一感のある PNG を生成する。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ICON_DIR = Path("src/ui/resources/icons")
FONT_CANDIDATES = [
    "C:/Windows/Fonts/seguiemj.ttf",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
]


def load_font(size: int):
    """利用可能なフォントを順に試す。"""
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def create_icon(filename: str, symbol: str, primary: str, secondary: str, size: int = 96):
    """角丸グラデーションのモノグラムアイコンを作る。"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    padding = 4
    radius = 24
    draw.rounded_rectangle(
        (padding, padding, size - padding, size - padding),
        radius=radius,
        fill=primary,
    )

    glow_padding = 14
    draw.rounded_rectangle(
        (glow_padding, glow_padding, size - glow_padding, size - glow_padding),
        radius=18,
        outline=secondary,
        width=3,
    )

    font = load_font(34)
    bbox = draw.textbbox((0, 0), symbol, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) / 2
    y = (size - text_height) / 2 - 2
    draw.text((x, y), symbol, fill="#fffdf8", font=font)

    image.save(ICON_DIR / filename)


def main():
    """全アイコンを生成する。"""
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    specs = [
        ("ai.png", "AI", "#0f766e", "#99f6e4"),
        ("ocr.png", "読", "#1d4ed8", "#bfdbfe"),
        ("viz.png", "図", "#b45309", "#fdba74"),
        ("web.png", "網", "#7c2d12", "#fdba74"),
        ("email.png", "〒", "#be123c", "#fda4af"),
        ("file.png", "整", "#334155", "#cbd5e1"),
        ("settings.png", "設", "#4b5563", "#e5e7eb"),
    ]

    for filename, symbol, primary, secondary in specs:
        create_icon(filename, symbol, primary, secondary)
        print(f"生成完了: {ICON_DIR / filename}")


if __name__ == "__main__":
    main()
