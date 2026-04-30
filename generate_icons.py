# -*- coding: utf-8 -*-
"""アプリ用の統一アイコンを生成する。"""

from pathlib import Path

from PIL import Image, ImageDraw


ICON_DIR = Path("src/ui/resources/icons")


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """HEX 色を RGB に変換する。"""
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """2色を線形補間する。"""
    return tuple(int(a[index] + (b[index] - a[index]) * t) for index in range(3))


def _draw_gradient(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], start: str, end: str):
    """角丸用の下地グラデーションを描く。"""
    x1, y1, x2, y2 = box
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    for y in range(y1, y2):
        t = (y - y1) / max(1, y2 - y1)
        color = _mix(start_rgb, end_rgb, t)
        draw.line((x1, y, x2, y), fill=color)


def _rounded_gradient(size: int, start: str, end: str, radius: int) -> Image.Image:
    """角丸グラデーションのレイヤーを返す。"""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    _draw_gradient(gradient_draw, (0, 0, size, size), start, end)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((4, 4, size - 4, size - 4), radius=radius, fill=255)
    layer.alpha_composite(gradient)
    layer.putalpha(mask)
    return layer


def _draw_symbol(draw: ImageDraw.ImageDraw, symbol: str, size: int):
    """白い線画シンボルを描く。"""
    c = "#ffffff"
    w = max(4, size // 16)
    if symbol == "ai":
        draw.rounded_rectangle((26, 28, 70, 68), radius=12, outline=c, width=w)
        draw.line((38, 22, 38, 28), fill=c, width=w)
        draw.line((58, 22, 58, 28), fill=c, width=w)
        draw.ellipse((34, 42, 42, 50), fill=c)
        draw.ellipse((54, 42, 62, 50), fill=c)
        draw.line((40, 58, 56, 58), fill=c, width=w)
    elif symbol == "ocr":
        draw.rounded_rectangle((25, 20, 71, 76), radius=7, outline=c, width=w)
        draw.line((35, 36, 61, 36), fill=c, width=w)
        draw.line((35, 50, 61, 50), fill=c, width=w)
        draw.line((35, 64, 52, 64), fill=c, width=w)
    elif symbol == "viz":
        draw.line((26, 70, 72, 70), fill=c, width=w)
        draw.rounded_rectangle((30, 48, 40, 70), radius=3, fill=c)
        draw.rounded_rectangle((45, 34, 55, 70), radius=3, fill=c)
        draw.rounded_rectangle((60, 24, 70, 70), radius=3, fill=c)
    elif symbol == "web":
        draw.ellipse((24, 24, 72, 72), outline=c, width=w)
        draw.line((24, 48, 72, 48), fill=c, width=w)
        draw.arc((34, 24, 62, 72), 90, 270, fill=c, width=w)
        draw.arc((34, 24, 62, 72), -90, 90, fill=c, width=w)
    elif symbol == "email":
        draw.rounded_rectangle((22, 30, 74, 66), radius=7, outline=c, width=w)
        draw.line((24, 34, 48, 52), fill=c, width=w)
        draw.line((72, 34, 48, 52), fill=c, width=w)
    elif symbol == "file":
        draw.rounded_rectangle((24, 22, 72, 74), radius=7, outline=c, width=w)
        draw.line((38, 38, 60, 38), fill=c, width=w)
        draw.line((34, 52, 64, 52), fill=c, width=w)
        draw.line((34, 64, 56, 64), fill=c, width=w)
    elif symbol == "settings":
        draw.ellipse((34, 34, 62, 62), outline=c, width=w)
        draw.ellipse((43, 43, 53, 53), fill=c)
        for x1, y1, x2, y2 in ((48, 18, 48, 30), (48, 66, 48, 78), (18, 48, 30, 48), (66, 48, 78, 48)):
            draw.line((x1, y1, x2, y2), fill=c, width=w)


def create_icon(filename: str, symbol: str, start: str, end: str, size: int = 96):
    """1つの PNG アイコンを生成する。"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    image.alpha_composite(_rounded_gradient(size, start, end, 24))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, size - 8, size - 8), radius=20, outline=(255, 255, 255, 95), width=3)
    draw.rounded_rectangle((14, 14, size - 14, size - 14), radius=16, outline=(255, 255, 255, 40), width=2)
    _draw_symbol(draw, symbol, size)
    image.save(ICON_DIR / filename)


def main():
    """全アイコンを再生成する。"""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    specs = [
        ("ai.png", "ai", "#10b981", "#2563eb"),
        ("ocr.png", "ocr", "#2563eb", "#7c3aed"),
        ("viz.png", "viz", "#f97316", "#db2777"),
        ("web.png", "web", "#0ea5e9", "#14b8a6"),
        ("email.png", "email", "#f43f5e", "#f59e0b"),
        ("file.png", "file", "#64748b", "#0f766e"),
        ("settings.png", "settings", "#475569", "#7c3aed"),
    ]
    for filename, symbol, start, end in specs:
        create_icon(filename, symbol, start, end)
        print(f"生成完了: {ICON_DIR / filename}")


if __name__ == "__main__":
    main()
