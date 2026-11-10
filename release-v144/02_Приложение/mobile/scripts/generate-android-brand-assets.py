"""Generate raster fallbacks and the Android legacy splash from folio's vector mark."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "android" / "app" / "src" / "main" / "res"
LIME = "#D7FA58"
INK = "#202126"
PAPER = "#F4F3EF"
SCALE = 4


def mark(draw: ImageDraw.ImageDraw, x: float, y: float, side: float, color: str) -> None:
    outer = [(29, 36.5), (54, 24), (79, 36.5), (79, 71.5), (54, 84), (29, 71.5)]
    inner = [(42.75, 47.75), (52.75, 40.25), (66.5, 47.75), (66.5, 61.5), (55.25, 69), (42.75, 61.5)]
    points = lambda coords: [(round(x + px * side / 108), round(y + py * side / 108)) for px, py in coords]
    width = max(1, round(3.75 * side / 108))
    draw.line(points(outer + [outer[0]]), fill=color, width=width, joint="curve")
    draw.line(points(inner + [inner[0]]), fill=color, width=width, joint="curve")


def render(size: int, shape: str) -> Image.Image:
    n = size * SCALE
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    if shape == "square":
        draw.rectangle((0, 0, n, n), fill=LIME)
    elif shape == "round":
        draw.ellipse((0, 0, n - 1, n - 1), fill=LIME)
    mark(draw, 0, 0, n, INK)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def splash() -> Image.Image:
    w, h = 480, 320
    im = Image.new("RGB", (w * SCALE, h * SCALE), PAPER)
    draw = ImageDraw.Draw(im)
    badge_side = 72 * SCALE
    bx, by = 132 * SCALE, 124 * SCALE
    draw.rounded_rectangle((bx, by, bx + badge_side, by + badge_side), radius=18 * SCALE, fill=LIME)
    mark(draw, bx + 6 * SCALE, by + 6 * SCALE, 60 * SCALE, INK)
    font_path = Path(r"C:\Windows\Fonts\seguisb.ttf")
    font = ImageFont.truetype(str(font_path), 42 * SCALE) if font_path.exists() else ImageFont.load_default(size=42 * SCALE)
    draw.text((218 * SCALE, 126 * SCALE), "folio", fill=INK, font=font, stroke_width=0)
    small = ImageFont.truetype(str(Path(r"C:\Windows\Fonts\segoeui.ttf")), 15 * SCALE) if Path(r"C:\Windows\Fonts\segoeui.ttf").exists() else ImageFont.load_default(size=15 * SCALE)
    draw.text((306 * SCALE, 128 * SCALE), "®", fill=LIME, font=small, stroke_width=0)
    return im.resize((w, h), Image.Resampling.LANCZOS)


def main() -> None:
    for directory in sorted(RES.glob("mipmap-*")):
        if "anydpi" in directory.name:
            continue
        for name, shape in (("ic_launcher.png", "square"), ("ic_launcher_round.png", "round"), ("ic_launcher_foreground.png", "foreground")):
            path = directory / name
            if path.exists():
                size = Image.open(path).size[0]
                render(size, "foreground" if shape == "foreground" else shape).save(path, optimize=True)
    splash().save(RES / "drawable" / "splash.png", optimize=True)
    print("Generated folio Android launcher fallbacks and splash from the vector brand mark.")


if __name__ == "__main__":
    main()
