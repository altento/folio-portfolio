from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent


def png_data_url(width: int, height: int) -> str:
    row = b"\0" + bytes((55, 82, 58, 255)) * width
    compressor = zlib.compressobj(level=9)
    compressed = b"".join(compressor.compress(row) for _ in range(height)) + compressor.flush()

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def portfolio(cover: str, gallery: str) -> dict:
    return {
        "schema_version": 1,
        "title": "Folio v97 import QA",
        "next_id": 50,
        "developer": {"full_name": "QA fixture", "specialization": "Проверка импорта"},
        "projects": [{
            "id": 49,
            "type": "Веб-приложение",
            "title": "QA: валидация изображений импорта",
            "description": "Синтетическая запись. Импорт не подтверждать.",
            "created_at": "2026-11-02",
            "status": "Завершён",
            "technologies": [],
            "demo_url": "",
            "role": "QA",
            "outcome": "Проверка чтения резервной копии.",
            "context": "",
            "solution": "",
            "process": "",
            "metrics": "",
            "tags": ["qa"],
            "featured": False,
            "sort_order": 1,
            "cover_image_data": cover,
            "gallery_images": [{"image_data": gallery, "alt": "QA изображение", "position": "50% 50%"}],
            "repository_url": "",
            "backend_stack": "",
        }],
    }


def write(name: str, data: dict) -> None:
    (OUTPUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    valid_png = png_data_url(1, 1)
    oversized_png = png_data_url(5000, 5000)
    write("valid-image.json", portfolio(valid_png, valid_png))
    write("corrupt-image.json", portfolio("data:image/png;base64,AAAA", valid_png))
    write("over-24mp-image.json", portfolio(oversized_png, valid_png))
    print(f"Created valid 1x1, corrupted, and 5000x5000 ({5000 * 5000:,} px) PNG fixtures in {OUTPUT}")


if __name__ == "__main__":
    main()
