from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
pages = sorted(ROOT.glob("page-*.png"))
if len(pages) != 10:
    raise SystemExit(f"Expected 10 rendered pages, found {len(pages)}")

tiles = []
for number, path in enumerate(pages, 1):
    image = Image.open(path).convert("RGB")
    image.thumbnail((420, 594))
    tile = Image.new("RGB", (444, 626), "white")
    tile.paste(image, ((tile.width - image.width) // 2, 25))
    ImageDraw.Draw(tile).text((10, 6), f"Page {number}", fill="black")
    tiles.append(tile)

columns = 2
rows = (len(tiles) + columns - 1) // columns
sheet = Image.new("RGB", (columns * tiles[0].width, rows * tiles[0].height), (225, 225, 225))
for index, tile in enumerate(tiles):
    sheet.paste(tile, ((index % columns) * tile.width, (index // columns) * tile.height))
sheet.save(ROOT / "contact-sheet.png")
