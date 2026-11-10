"""Портфолио веб-разработчика — учебное приложение ООП, модули 4–5."""
from __future__ import annotations

import csv
import base64
import copy
import io
import json
import os
import sys
import tempfile
import re
import tkinter as tk
from dataclasses import asdict
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any
from urllib.parse import urlparse
import webbrowser
from portfolio_core import (
    Developer, LandingProject, Portfolio, Project, Technology, WebAppProject,
    merge_portfolio_import, project_type_change_loss_fields, render_portfolio_markdown,
)
from sqlite_storage import SQLiteStore

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:  # Pillow is optional; Tk can still display PNG files.
    Image = ImageOps = ImageTk = None

_COVER_ERRORS = (OSError, ValueError, SyntaxError, tk.TclError) + (
    (Image.DecompressionBombError,) if Image is not None else ()
)


DATA_SCHEMA_VERSION = 1
GALLERY_MAX_IMAGES = 10
GALLERY_MAX_TOTAL_DATA_CHARS = 8_000_000
GALLERY_MAX_IMAGE_DATA_CHARS = 1_600_000
PORTFOLIO_IMPORT_MAX_BYTES = 64 * 1024 * 1024
PORTFOLIO_IMPORT_MAX_PROJECTS = 130_000
PORTFOLIO_IMPORT_MAX_IMAGES = 250
PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS = 24_000_000
PORTFOLIO_IMPORT_MAX_IMAGE_PIXELS = 24_000_000
PORTFOLIO_IMPORT_MAX_TOTAL_IMAGE_PIXELS = 120_000_000
PORTFOLIO_MAX_SAFE_INTEGER = 9_007_199_254_740_991
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
BUILTIN_COVER_ALIASES = {
    "cleaning-crm.png": "cleaning-crm-case-v2.webp",
    "city-courtyards.png": "city-courtyards-case-v2.webp",
    "portfolio-studio.png": "portfolio-studio.webp",
    "cleaning-crm.webp": "cleaning-crm-case-v2.webp",
    "city-courtyards.webp": "city-courtyards-case-v2.webp",
}


def default_data_path() -> Path:
    """Keep frozen-app data outside the temporary one-file extraction folder."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Folio"
        base.mkdir(parents=True, exist_ok=True)
        return base / "portfolio_data.sqlite3"
    return Path(__file__).with_name("portfolio_data.sqlite3")


def enable_tk_accessibility(root: tk.Tk) -> bool:
    """Expose the root window to screen readers when the Tcl/Tk build supports it."""
    try:
        root.tk.call("tk", "accessible", "add_acc_object", root._w)
    except tk.TclError:
        # Tk 8.6 has no accessibility command; keep the established runtime usable.
        return False
    return True


DESKTOP_HERO_ART_PATH = RESOURCE_ROOT / "web" / "assets" / "illustrations" / "folio-dashboard-hero-v1.webp"

# Shared desktop tokens mirror the web companion's neutral and accent palette.
DESKTOP_PALETTE = {
    "background": "#F4F5F1",
    "surface": "#FFFFFF",
    "ink": "#20221F",
    "muted": "#62666C",
    "border": "#E2E5DD",
    "accent": "#C8F36A",
    "dark": "#202124",
}


def project_count_label(value: int) -> str:
    """Return the Russian plural form for a project count."""
    count = abs(int(value))
    last_two = count % 100
    last = count % 10
    if 11 <= last_two <= 14:
        return "проектов"
    if last == 1:
        return "проект"
    if 2 <= last <= 4:
        return "проекта"
    return "проектов"


def case_story_completion_states(context: str, role: str, solution: str, process: str,
                                 outcome: str, metrics: str, has_visuals: bool) -> tuple[bool, ...]:
    """Return optional case-story completion states in the same order as the web guide."""
    return (
        bool(context.strip()),
        bool(role.strip()),
        bool(solution.strip()),
        bool(process.strip()),
        bool(outcome.strip() or metrics.strip()),
        bool(has_visuals),
    )


def is_placeholder_url(value: str) -> bool:
    """Recognize reserved example domains and the placeholder GitHub owner."""
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    path = [part for part in parsed.path.split("/") if part]
    return (host in {"example.com", "www.example.com", "example.net", "www.example.net", "example.org", "www.example.org"}
            or (host == "github.com" and bool(path) and path[0].lower() == "example"))


def desktop_window_dimensions(screen_width: int, screen_height: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Choose a useful desktop window size that stays inside smaller displays."""
    return fit_window_dimensions(screen_width, screen_height, (1360, 860), (1000, 680))


def fit_window_dimensions(screen_width: int, screen_height: int,
                          preferred: tuple[int, int], minimum: tuple[int, int],
                          margins: tuple[int, int] = (48, 96)) -> tuple[tuple[int, int], tuple[int, int]]:
    """Fit a resizable window and its minimum size within available screen space."""
    width = max(320, min(preferred[0], int(screen_width) - margins[0]))
    height = max(320, min(preferred[1], int(screen_height) - margins[1]))
    return (width, height), (min(minimum[0], width), min(minimum[1], height))


def center_window_position(screen_width: int, screen_height: int,
                            window_width: int, window_height: int) -> tuple[int, int]:
    """Center a top-level window while keeping its origin on-screen."""
    return (max(0, (int(screen_width) - int(window_width)) // 2),
            max(0, (int(screen_height) - int(window_height)) // 2))


def desktop_table_row_tags(index: int) -> tuple[str, ...]:
    """Return a subtle alternating surface treatment for desktop project rows."""
    return ("row-alt",) if index % 2 else ()


def desktop_density_for_height(height: int) -> str:
    """Choose a compact vertical layout when the available desktop height is limited."""
    if height <= 740:
        return "tight"
    if height <= 960:
        return "compact"
    return "comfortable"


def desktop_detail_art_size(density: str) -> tuple[int, int]:
    return {"tight": (150, 90), "compact": (220, 132), "comfortable": (280, 170)}.get(
        density, (280, 170))


def desktop_project_media_items(project: Project) -> list[tuple[str, str, str, str]]:
    """Build the ordered cover and gallery sequence used by desktop case viewers."""
    items = []
    if project.cover_image_data or project.cover_image:
        items.append((project.cover_image_data, project.cover_image, "Обложка проекта",
                      normalize_cover_position(project.cover_position)))
    items.extend((image["image_data"], "", image["alt"], image["position"])
                 for image in project.gallery_images)
    return items


def desktop_project_card_layout(window_width: int) -> tuple[int, tuple[int, int]]:
    """Return a responsive gallery column count and cover size for a desktop window."""
    width = max(320, int(window_width))
    columns = 1 if width < 1120 else 2
    available = width - 64 if columns == 1 else width // 2 - 52
    art_width = min(780, max(320, (available // 48) * 48))
    return columns, (art_width, round(art_width * 0.43))


def canvas_focus_view_fraction(view_top: float, viewport_height: float,
                               content_height: float, target_top: float,
                               target_height: float, margin: float = 12) -> float | None:
    """Keep a focused control inside the viewport with a little visual breathing room."""
    content_height = max(1.0, content_height)
    margin = max(0.0, min(float(margin), max(0.0, (viewport_height - target_height) / 2)))
    if target_top < view_top + margin:
        return max(0.0, min(1.0, (target_top - margin) / content_height))
    target_bottom = target_top + target_height
    if target_bottom > view_top + viewport_height - margin:
        return max(0.0, min(1.0, (target_bottom + margin - viewport_height) / content_height))
    return None


def desktop_text_wheel_target(delta: int, view: tuple[float, float]) -> str | None:
    """Choose the inner editor until it reaches an edge, then scroll the form."""
    if delta == 0:
        return None
    top, bottom = view
    if delta > 0:
        return "text" if top > 0 else "form"
    return "text" if bottom < 1 else "form"


def grid_anchor_in(container: Any, widget: Any) -> tuple[Any, dict[str, Any]] | None:
    """Resolve a nested widget to the grid-managed descendant of a container."""
    anchor = widget
    while anchor is not None and getattr(anchor, "master", None) is not container:
        anchor = getattr(anchor, "master", None)
    if anchor is None:
        return None
    placement = anchor.grid_info()
    return (anchor, placement) if placement else None


def is_valid_cover_image(value: str, *, data_url: bool = False) -> bool:
    if not value:
        return True
    if data_url:
        return validate_embedded_image_data(value, max_chars=2_800_000, max_bytes=2 * 1024 * 1024,
                                            max_pixels=PORTFOLIO_IMPORT_MAX_IMAGE_PIXELS)
    return bool(re.fullmatch(r"\./assets/covers/[A-Za-z0-9-]+\.(?:png|webp|jpe?g)", value, re.IGNORECASE))


def validate_embedded_image_data(value: str, *, max_chars: int, max_bytes: int, max_pixels: int) -> bool:
    """Decode and verify an embedded raster image before it enters portable data."""
    if Image is None or not isinstance(value, str) or len(value) > max_chars:
        return False
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})", value)
    if not match:
        return False
    try:
        raw = base64.b64decode(match.group(2), validate=True)
        if len(raw) > max_bytes:
            return False
        formats = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format != formats[match.group(1)] or probe.width * probe.height > max_pixels:
                return False
            probe.verify()
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != formats[match.group(1)] or image.width * image.height > max_pixels:
                return False
            image.load()
        return True
    except _COVER_ERRORS:
        return False


def embedded_image_pixel_count(value: str) -> int:
    """Return verified embedded image pixels, or raise a user-facing validation error."""
    if Image is None:
        raise ValueError("Для проверки изображений установите Pillow: python -m pip install -r requirements.txt")
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})", value)
    if not match:
        raise ValueError("Изображение имеет неподдерживаемый формат или повреждено.")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
        formats = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != formats[match.group(1)]:
                raise ValueError("Формат изображения не соответствует его data URL.")
            pixels = image.width * image.height
            if pixels > PORTFOLIO_IMPORT_MAX_IMAGE_PIXELS:
                raise ValueError("Разрешение изображения превышает 24 мегапикселя.")
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
        return pixels
    except _COVER_ERRORS as exc:
        raise ValueError("Изображение повреждено или не может быть декодировано.") from exc


def validate_portable_transfer_payload(data: dict[str, Any]) -> None:
    """Keep desktop saves and JSON exports within the web/PWA transfer contract."""
    if len(data.get("projects", [])) > PORTFOLIO_IMPORT_MAX_PROJECTS:
        raise ValueError(f"В портфолио может быть не больше {PORTFOLIO_IMPORT_MAX_PROJECTS} проектов для переноса между устройствами.")
    next_id = data.get("next_id")
    if isinstance(next_id, bool) or not isinstance(next_id, int) or not 1 <= next_id <= PORTFOLIO_MAX_SAFE_INTEGER:
        raise ValueError("Следующий ID проекта выходит за пределы общего формата переноса.")
    if not normalize_case_text(data.get("title", ""), "Название портфолио", 120):
        raise ValueError("Название портфолио не должно быть пустым.")
    normalize_developer_data(data.get("developer", {}))
    image_count = image_data_chars = image_pixels = 0
    for index, project in enumerate(data.get("projects", []), start=1):
        normalize_case_text(project.get("title"), f"Название проекта №{index}", 90)
        normalize_case_text(project.get("description"), f"Описание проекта №{index}", 500)
        normalize_case_text(project.get("role", ""), "Ваша роль", 120)
        normalize_case_text(project.get("outcome", ""), "Результат", 500)
        if len(project.get("technologies", [])) > 40:
            raise ValueError(f"У проекта №{index} может быть не больше 40 технологий для переноса.")
        for technology in project.get("technologies", []):
            normalize_case_text(technology.get("name"), "Название технологии", 60)
            normalize_case_text(technology.get("category", "Инструмент"), "Категория технологии", 60)
            normalize_case_text(technology.get("version", ""), "Версия технологии", 40)
        gallery = project.get("gallery_images", [])
        if not isinstance(gallery, list) or len(gallery) > GALLERY_MAX_IMAGES:
            raise ValueError(f"В галерее проекта №{index} может быть не больше {GALLERY_MAX_IMAGES} изображений.")
        if not isinstance(project.get("technologies", []), list):
            raise ValueError(f"Список технологий проекта №{index} задан неверно.")
        if not is_valid_cover_image(project.get("cover_image", "")) or not is_valid_cover_image(
                project.get("cover_image_data", ""), data_url=True):
            raise ValueError(f"У проекта №{index} обложка не подходит для переноса.")
        gallery = normalize_gallery_images(gallery)
        images = ([project.get("cover_image_data")] if project.get("cover_image_data") else []) + [
            item.get("image_data") for item in gallery if isinstance(item, dict) and item.get("image_data")
        ]
        image_count += len(images)
        image_data_chars += sum(len(image) for image in images)
        if image_count > PORTFOLIO_IMPORT_MAX_IMAGES:
            raise ValueError(f"В портфолио может быть не больше {PORTFOLIO_IMPORT_MAX_IMAGES} изображений для переноса.")
        if image_data_chars > PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS:
            raise ValueError("Общий объём изображений превышает лимит переноса в 24 млн символов.")
        for image in images:
            image_pixels += embedded_image_pixel_count(image)
            if image_pixels > PORTFOLIO_IMPORT_MAX_TOTAL_IMAGE_PIXELS:
                raise ValueError("Суммарное разрешение изображений превышает лимит переноса в 120 мегапикселей.")


def serialize_portable_json(data: dict[str, Any]) -> str:
    """Serialize a validated backup that remains within both apps' file-size cap."""
    validate_portable_transfer_payload(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) > PORTFOLIO_IMPORT_MAX_BYTES:
        raise ValueError("Экспорт JSON больше 64 МиБ и не откроется на другом устройстве.")
    return payload


def normalize_developer_data(data: dict) -> dict:
    """Validate the portable author profile while keeping older two-field files valid."""
    if not isinstance(data, dict):
        raise ValueError("Поле developer должно быть объектом.")
    allowed = {"full_name", "specialization", "introduction", "email", "website_url", "github_url",
               "include_email", "include_website", "include_github"}
    if set(data) - allowed:
        raise ValueError("Профиль автора содержит неизвестные поля.")
    limits = {"full_name": 90, "specialization": 90, "introduction": 800,
              "email": 254, "website_url": 300, "github_url": 300}
    defaults = {"full_name": "Даниил Головин", "specialization": "Веб-разработчик",
                "introduction": "", "email": "", "website_url": "", "github_url": ""}
    normalized = {}
    for key, limit in limits.items():
        value = data.get(key, defaults[key])
        if not isinstance(value, str):
            raise ValueError(f"Поле профиля «{key}» должно быть текстом.")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"Поле профиля «{key}» не должно превышать {limit} символов.")
        if any(ord(char) < 32 and char not in "\n\t" or ord(char) == 127 for char in value):
            raise ValueError(f"Поле профиля «{key}» содержит управляющие символы.")
        normalized[key] = value
    if not normalized["full_name"] or not normalized["specialization"]:
        raise ValueError("Имя и специализация автора обязательны.")
    if normalized["email"] and not re.fullmatch(r"[^\s@<>]+@[^\s@<>.]+(?:\.[^\s@<>.]+)+", normalized["email"]):
        raise ValueError("Введите корректный email автора.")
    for key in ("website_url", "github_url"):
        value = normalized[key]
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"Поле профиля «{key}» должно быть ссылкой HTTP или HTTPS без логина и пароля.")
    for key in ("include_email", "include_website", "include_github"):
        value = data.get(key, False)
        if not isinstance(value, bool):
            raise ValueError(f"Поле профиля «{key}» должно быть логическим значением.")
        normalized[key] = value
    return normalized


def normalize_tags(value: str | list[str] | None) -> list[str]:
    """Normalize user tags without silently dropping invalid or excess values."""
    if value is None:
        candidates = []
    elif isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        candidates = value
    else:
        raise ValueError("Теги должны быть текстом или списком строк.")
    tags, seen = [], set()
    for candidate in candidates:
        tag = candidate.strip()
        if not tag:
            continue
        if len(tag) > 32:
            raise ValueError("Каждый тег должен содержать не больше 32 символов.")
        if any(ord(char) < 32 or ord(char) == 127 for char in tag):
            raise ValueError("Теги не должны содержать управляющие символы.")
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            tags.append(tag)
            if len(tags) > 20:
                raise ValueError("Можно добавить не больше 20 тегов к одному кейсу.")
    return tags


def normalize_case_text(value: str | None, label: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"Поле «{label}» должно быть текстом.")
    text = value.strip()
    if len(text) > limit:
        raise ValueError(f"Поле «{label}» должно содержать не больше {limit} символов.")
    if any((ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in text):
        raise ValueError(f"Поле «{label}» содержит недопустимые управляющие символы.")
    return text


def normalize_cover_position(value: Any = "50% 46%") -> str:
    """Validate the shared, portable focal point used by every cover crop."""
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%", value
    ):
        raise ValueError("У обложки проекта некорректная точка кадрирования.")
    return value


def normalize_gallery_images(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > GALLERY_MAX_IMAGES:
        raise ValueError(f"В галерее проекта может быть не больше {GALLERY_MAX_IMAGES} изображений.")
    if sum(len(image.get("image_data", "")) for image in value if isinstance(image, dict) and isinstance(image.get("image_data", ""), str)) > GALLERY_MAX_TOTAL_DATA_CHARS:
        raise ValueError("Объём data URL галереи превышает 8 млн символов (около 6 МиБ медиа). Уменьшите или удалите несколько изображений.")
    images = []
    for index, image in enumerate(value, 1):
        if not isinstance(image, dict):
            raise ValueError(f"Изображение №{index} должно быть объектом.")
        data = image.get("image_data", "")
        if not isinstance(data, str) or len(data) > GALLERY_MAX_IMAGE_DATA_CHARS or not validate_embedded_image_data(
            data, max_chars=GALLERY_MAX_IMAGE_DATA_CHARS, max_bytes=1_200_000, max_pixels=24_000_000
        ):
            raise ValueError(f"Изображение №{index} должно быть PNG, JPEG или WebP до 1,2 МиБ.")
        alt = normalize_case_text(image.get("alt"), f"Описание изображения №{index}", 180)
        if not alt:
            raise ValueError(f"Добавьте текстовое описание для изображения №{index}.")
        position = image.get("position", "50% 50%")
        if not isinstance(position, str) or not re.fullmatch(r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%", position):
            raise ValueError(f"У изображения №{index} некорректная точка кадрирования.")
        images.append({"image_data": data, "alt": alt, "position": position})
    return images


def encode_gallery_image(file_path: str | Path, max_output_chars: int = GALLERY_MAX_IMAGE_DATA_CHARS) -> str:
    if Image is None:
        raise ValueError("Для работы с изображениями установите Pillow: python -m pip install -r requirements.txt")
    path = Path(file_path)
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Исходное изображение должно быть меньше 10 МиБ.")
    with Image.open(path) as image:
        if image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Поддерживаются только PNG, JPEG и WebP.")
        if image.width * image.height > 24_000_000:
            raise ValueError("Уменьшите разрешение до 24 мегапикселей.")
        image.load()
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=82, method=6)
    raw = output.getvalue()
    encoded = "data:image/webp;base64," + base64.b64encode(raw).decode("ascii")
    if len(encoded) > min(GALLERY_MAX_IMAGE_DATA_CHARS, max_output_chars):
        raise ValueError("Изображение не помещается в оставшийся лимит галереи. Уменьшите изображение или освободите место.")
    return encoded


def encode_cover_image(file_path: str | Path) -> str:
    """Validate and encode one small local cover for portable JSON/SQLite storage."""
    path = Path(file_path)
    if Image is None:
        raise ValueError("Для добавления обложек установите Pillow: python -m pip install -r requirements.txt")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Размер обложки не должен превышать 2 МиБ.")
    raw = path.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Размер обложки не должен превышать 2 МиБ.")
    with Image.open(io.BytesIO(raw)) as image:
        if image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Поддерживаются только PNG, JPEG и WebP.")
        if image.width * image.height > 30_000_000:
            raise ValueError("Слишком большое разрешение изображения (максимум 30 Мп).")
        image.load()
        mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp"}[image.format]
    data_url = f"data:image/{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    if not is_valid_cover_image(data_url, data_url=True):
        raise ValueError("Файл не удалось безопасно подготовить для сохранения.")
    return data_url


def validate_project_input(title: str, description: str, created_at: str, status: str,
                           demo_url: str, repository_url: str, project_type: str,
                           page_count: str) -> int | None:
    """Проверяет ввод формы и возвращает количество страниц для лендинга."""
    if not title.strip() or not description.strip():
        raise ValueError("Название и описание обязательны.")
    normalize_case_text(title, "Название проекта", 90)
    normalize_case_text(description, "Короткое описание", 500)
    try:
        parsed_date = date.fromisoformat(created_at.strip())
    except ValueError as exc:
        raise ValueError("Введите корректную дату в формате ГГГГ-ММ-ДД.") from exc
    if parsed_date.isoformat() != created_at.strip():
        raise ValueError("Введите дату строго в формате ГГГГ-ММ-ДД.")
    if status not in PortfolioApp.STATUSES:
        raise ValueError("Выберите статус проекта из списка.")
    for label, value in (("Демо URL", demo_url), ("Ссылка на репозиторий", repository_url)):
        if not value.strip():
            continue
        try:
            parsed = urlparse(value.strip())
            hostname = parsed.hostname
        except ValueError as exc:
            raise ValueError(f"{label}: проверьте формат ссылки.") from exc
        if parsed.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError(f"{label}: используйте полную ссылку http:// или https://.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError(f"{label}: ссылка не должна содержать имя пользователя или пароль.")
    if project_type == PortfolioApp.TYPES[0]:
        try:
            pages = int(page_count.strip())
        except ValueError as exc:
            raise ValueError("Количество страниц должно быть целым числом.") from exc
        if pages < 1:
            raise ValueError("Количество страниц должно быть положительным целым числом.")
        return pages
    return None


class PortfolioApp:
    TYPES = ("Сайт / лендинг", "Веб-приложение")
    STATUSES = ("В разработке", "Завершён", "Опубликован", "Архив")
    COLUMNS = ("Название", "Тип", "Статус", "Дата", "Страниц", "Технологии", "В фокусе")

    def __init__(self, root: tk.Tk):
        self.root = root
        self.accessibility_enabled = enable_tk_accessibility(root)
        self.developer = Developer()
        self.portfolio = self.developer.create_portfolio()
        self.data_path: Path | None = default_data_path()
        self.sort_column = "featured"
        self.sort_ascending = True
        self.root.title("Портфолио веб-разработчика")
        (window_width, window_height), minimum_size = desktop_window_dimensions(
            self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        )
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(*minimum_size)
        self.initial_window_width = window_width
        self._density_after = None
        self._layout_density = None
        self._card_layout_signature = None
        self.root.configure(background="#F4F5F1")
        self._build_menu()
        self._build_ui()
        self.root.bind("<Configure>", self._schedule_density_update, add="+")
        self.root.after_idle(self._update_layout_density)
        self._load_startup_data()

    def _build_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Открыть базу данных / JSON…", command=self.load)
        file_menu.add_command(label="Сохранить", command=self.save)
        file_menu.add_command(label="Сохранить базу как…", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Профиль автора…", command=self.edit_developer_profile)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт JSON…", command=self.export_json)
        file_menu.add_command(label="Экспорт CSV…", command=self.export_csv)
        file_menu.add_command(label="Экспорт портфолио в Markdown…", command=self.export_markdown)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.destroy)
        menu.add_cascade(label="Файл", menu=file_menu)
        menu.add_command(label="О программе", command=self.about)
        self.root.config(menu=menu)

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        bg, surface, ink, muted, border, accent, dark = (DESKTOP_PALETTE[key] for key in ("background", "surface", "ink", "muted", "border", "accent", "dark"))
        style.configure("TFrame", background=bg)
        style.configure("Surface.TFrame", background=surface)
        style.configure("Hero.TFrame", background="#EEE9DE")
        style.configure("Hero.Copy.TFrame", background="#EEE9DE")
        style.configure("TLabel", background=bg, foreground=ink, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=bg, foreground=ink, font=("Segoe UI", 26, "bold"))
        style.configure("Subheader.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("Hero.Eyebrow.TLabel", background="#EEE9DE", foreground="#586626",
                        font=("Segoe UI", 8, "bold"))
        style.configure("Hero.Title.TLabel", background="#EEE9DE", foreground=ink,
                        font=("Segoe UI", 24, "bold"))
        style.configure("Hero.Subtitle.TLabel", background="#EEE9DE", foreground=muted,
                        font=("Segoe UI", 10))
        style.configure("Hero.Art.TLabel", background="#EEE9DE")
        style.configure("Surface.TLabel", background=surface, foreground=ink, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
        style.configure("TLabelframe", background=bg, bordercolor=border, relief="solid", padding=2)
        style.configure("TLabelframe.Label", background=bg, foreground=ink, font=("Segoe UI", 10, "bold"))
        style.configure("Surface.TLabelframe", background=surface, bordercolor=border, relief="solid", padding=2)
        style.configure("Surface.TLabelframe.Label", background=surface, foreground=ink, font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=(12, 8), background=surface, foreground=ink,
                        bordercolor=border, borderwidth=1, relief="solid",
                        font=("Segoe UI", 9, "bold"), focusthickness=2)
        style.configure("Compact.TButton", padding=(7, 5), background=surface, foreground=ink,
                        bordercolor=border, borderwidth=1, relief="solid",
                        font=("Segoe UI", 8, "bold"), focusthickness=2)
        style.map("TButton", background=[("active", "#EEF4E4"), ("disabled", "#F1F2EF")],
                  foreground=[("disabled", "#A5AAA1")], bordercolor=[("focus", accent)],
                  relief=[("pressed", "flat"), ("active", "flat")])
        style.configure("Primary.TButton", background=accent, foreground=dark, bordercolor=accent,
                        borderwidth=0, relief="flat")
        style.map("Primary.TButton", background=[("active", "#B7E954"), ("disabled", "#E4EDCF")])
        style.configure("Danger.TButton", foreground="#A8342B")
        style.map("Danger.TButton", background=[("active", "#FCEBE8")])
        style.configure("TEntry", padding=(9, 7), fieldbackground=surface, foreground=ink, bordercolor=border)
        style.map("TEntry", bordercolor=[("focus", accent)])
        style.configure("TCombobox", padding=(8, 5), fieldbackground=surface, foreground=ink, bordercolor=border)
        style.map("TCombobox", fieldbackground=[("readonly", surface)], foreground=[("readonly", ink)],
                  bordercolor=[("focus", accent)])
        style.configure("Treeview", rowheight=42, font=("Segoe UI", 10), background=surface,
                        fieldbackground=surface, foreground=ink, bordercolor=border, relief="flat")
        style.map("Treeview", background=[("selected", dark)], foreground=[("selected", surface)])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#EFF1EB",
                        foreground="#555B52", bordercolor=border, relief="flat", padding=(9, 10))
        style.map("Treeview.Heading", background=[("active", "#E5E9DF")])
        style.configure("TCheckbutton", background=bg, foreground=ink, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", bg)])
        style.configure("TScrollbar", background="#E5E8E0", troughcolor=bg, bordercolor=bg,
                        arrowcolor=muted, gripcount=0)
        style.configure("CaseGuide.Horizontal.TProgressbar", troughcolor=border,
                        background=accent, bordercolor=border, thickness=7)
        self.footer = ttk.Label(self.root, text="Готово", anchor="w", padding=(24, 8), style="Muted.TLabel")
        self.footer.pack(fill="x", side="bottom")
        outer = ttk.Frame(self.root, padding=(24, 18))
        outer.pack(fill="both", expand=True)
        hero = ttk.Frame(outer, style="Hero.TFrame", padding=(20, 14))
        hero.pack(fill="x", pady=(0, 14))
        hero_copy = ttk.Frame(hero, style="Hero.Copy.TFrame")
        hero_copy.pack(side="left", fill="both", expand=True)
        ttk.Label(hero_copy, text="folio®  ·  ЛИЧНОЕ ПОРТФОЛИО",
                  style="Hero.Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(hero_copy, text="Ваши проекты,\nсобранные в одном месте.",
                  style="Hero.Title.TLabel", justify="left").pack(anchor="w", pady=(5, 2))
        ttk.Label(hero_copy, text="Кейсы, статусы и детали — под рукой на вашем компьютере.",
                  style="Hero.Subtitle.TLabel", wraplength=620, justify="left").pack(anchor="w")
        ttk.Button(hero_copy, text="＋ Добавить проект", command=self.add,
                   style="Primary.TButton").pack(anchor="w", pady=(9, 0))
        self.hero_art = None
        if Image is not None and ImageOps is not None and ImageTk is not None and DESKTOP_HERO_ART_PATH.is_file():
            art_width = min(390, max(160, int(self.root.winfo_screenwidth() * 0.285)))
            art_height = max(84, int(art_width * 0.36))
            try:
                with Image.open(DESKTOP_HERO_ART_PATH) as source:
                    art = ImageOps.fit(source.convert("RGB"), (art_width, art_height),
                                       method=Image.Resampling.LANCZOS, centering=(0.80, 0.5))
                self.hero_art = ImageTk.PhotoImage(art, master=hero)
                self.hero_art_label = ttk.Label(hero, image=self.hero_art, style="Hero.Art.TLabel")
                self.hero_art_label.pack(side="right", padx=(18, 0))
            except _COVER_ERRORS:
                self.hero_art = None
                self.hero_art_label = None
        else:
            self.hero_art_label = None
        self.hero_panel = hero
        filt = ttk.LabelFrame(outer, text="Поиск и фильтрация", padding=12, style="Surface.TLabelframe")
        filt.pack(fill="x", pady=(0, 10))
        self.filter_panel = filt
        ttk.Label(filt, text="Поиск:").grid(row=0, column=0, padx=(0, 5))
        self.query = tk.StringVar()
        search = ttk.Entry(filt, textvariable=self.query, width=34)
        search.grid(row=0, column=1, sticky="ew", padx=4)
        search.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(filt, text="Найти", command=self.refresh, style="Primary.TButton").grid(row=0, column=2, padx=4)
        ttk.Label(filt, text="Тип:").grid(row=0, column=3, padx=(14, 4))
        self.type_filter = tk.StringVar(value="Все типы")
        ttk.Combobox(filt, textvariable=self.type_filter, values=("Все типы", *self.TYPES), state="readonly", width=19).grid(row=0, column=4)
        ttk.Label(filt, text="Статус:").grid(row=0, column=5, padx=(12, 4))
        self.status_filter = tk.StringVar(value="Все статусы")
        ttk.Combobox(filt, textvariable=self.status_filter, values=("Все статусы", *self.STATUSES), state="readonly", width=16).grid(row=0, column=6)
        ttk.Button(filt, text="Сбросить", command=self.reset_filters).grid(row=0, column=7, padx=(10, 0))
        filt.columnconfigure(1, weight=1)
        self.type_filter.trace_add("write", lambda *_: self.refresh())
        self.status_filter.trace_add("write", lambda *_: self.refresh())
        self.featured_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(filt, text="Только избранные", variable=self.featured_only,
                        command=self.refresh).grid(row=1, column=1, columnspan=2, sticky="w", pady=(7, 0))
        ttk.Label(filt, text="Тег:").grid(row=1, column=3, sticky="e", padx=(14, 4), pady=(7, 0))
        self.tag_filter = tk.StringVar(value="Все теги")
        self.tag_combo = ttk.Combobox(filt, textvariable=self.tag_filter, values=("Все теги",),
                                      state="readonly", width=18)
        self.tag_combo.grid(row=1, column=4, sticky="w", pady=(7, 0))
        self.tag_filter.trace_add("write", lambda *_: self.refresh())
        # A visual project gallery is the default desktop presentation. Keep the
        # sortable table beside it for dense scanning and compatibility with the
        # module's tabular workflow.
        view_bar = ttk.Frame(outer)
        view_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(view_bar, text="ПРЕДСТАВЛЕНИЕ", style="Muted.TLabel").pack(side="left")
        view_actions = ttk.Frame(view_bar)
        view_actions.pack(side="right")
        self.view_mode = "cards"
        self.card_view_button = ttk.Button(view_actions, text="▦  Карточки",
                                           command=lambda: self._set_project_view("cards"),
                                           style="Primary.TButton")
        self.card_view_button.pack(side="left", padx=(0, 5))
        self.table_view_button = ttk.Button(view_actions, text="☷  Таблица",
                                            command=lambda: self._set_project_view("table"))
        self.table_view_button.pack(side="left")
        views = ttk.Frame(outer)
        table = ttk.Frame(views)
        self.table_view = table
        self.card_view = ttk.Frame(views)
        card_canvas = tk.Canvas(self.card_view, highlightthickness=0, borderwidth=0,
                                background=bg, takefocus=True)
        card_scroll = ttk.Scrollbar(self.card_view, orient="vertical", command=card_canvas.yview)
        card_canvas.configure(yscrollcommand=card_scroll.set)
        card_canvas.pack(side="left", fill="both", expand=True)
        card_scroll.pack(side="right", fill="y")
        self.card_canvas = card_canvas
        self.card_scroll = card_scroll
        self.card_grid = ttk.Frame(card_canvas, style="TFrame", padding=(0, 0, 10, 10))
        self.card_grid_window = card_canvas.create_window((0, 0), window=self.card_grid, anchor="nw")
        self.card_grid.bind("<Configure>", lambda _event: card_canvas.configure(
            scrollregion=card_canvas.bbox("all")))
        card_canvas.bind("<Configure>", lambda event: card_canvas.itemconfigure(
            self.card_grid_window, width=event.width))
        card_canvas.bind("<MouseWheel>", lambda event: card_canvas.yview_scroll(
            -1 if event.delta > 0 else 1, "units"))
        self.table_view.pack(fill="both", expand=True)
        # Create the project table before its action toolbar so keyboard traversal follows
        # the visual reading order: filters → projects → row actions.
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", side="bottom")
        # Reserve the fixed action row before the expandable gallery/table gets space.
        # Otherwise a short window can let the views consume the row and hide every action.
        views.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("title", "type", "status", "date", "pages", "tech", "featured"), show="headings", selectmode="browse", takefocus=True)
        self.tree.tag_configure("row-alt", background="#F6F5F1")
        widths = (250, 155, 120, 105, 75, 300, 95)
        for key, label, width in zip(self.tree["columns"], self.COLUMNS, widths):
            self.tree.heading(key, text=label, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree_vertical_scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree_horizontal_scroll = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.tree_vertical_scroll.set, xscrollcommand=self.tree_horizontal_scroll.set)
        self.tree_vertical_scroll.grid(row=0, column=1, sticky="ns")
        self.tree_horizontal_scroll.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.empty_state = ttk.Frame(views, padding=16, style="Surface.TFrame")
        self.empty_illustration = None
        illustration_path = RESOURCE_ROOT / "assets" / "portfolio-empty-illustration.png"
        try:
            self.empty_illustration = tk.PhotoImage(file=str(illustration_path)).subsample(2, 2)
            ttk.Label(self.empty_state, image=self.empty_illustration, style="Surface.TLabel").pack(side="left", padx=(0, 18))
        except tk.TclError:
            pass
        empty_copy = ttk.Frame(self.empty_state, style="Surface.TFrame")
        empty_copy.pack(side="left", fill="both", expand=True)
        self.empty_state_title = ttk.Label(empty_copy, text="", style="Surface.TLabel",
                                           font=("Segoe UI", 14, "bold"))
        self.empty_state_title.pack(anchor="w", pady=(0, 5))
        self.empty_state_description = ttk.Label(empty_copy, text="", style="Muted.TLabel", wraplength=340,
                                                 justify="left")
        self.empty_state_description.pack(anchor="w", pady=(0, 12))
        self.empty_state_action = ttk.Button(empty_copy, text="", style="Primary.TButton")
        self.empty_state_action.pack(anchor="w")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_details())
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        box = ttk.LabelFrame(bottom, text="Карточка проекта", padding=12, style="Surface.TLabelframe")
        self.detail_box = box
        self.detail_content = ttk.Frame(box, style="Surface.TFrame")
        self.detail_content.pack(fill="both", expand=True, padx=4, pady=4)
        self.details_label = tk.Text(self.detail_content, height=6, wrap="word", state="disabled",
                                     background=surface, foreground=ink, selectbackground=dark,
                                     selectforeground=surface, insertbackground=ink, relief="flat",
                                     borderwidth=0, highlightthickness=0, padx=8, pady=6,
                                     font=("Segoe UI", 10))
        self.details_label.pack(anchor="w", fill="both", expand=True, side="left")
        self.detail_scroll = ttk.Scrollbar(self.detail_content, orient="vertical", command=self.details_label.yview)
        self.details_label.configure(yscrollcommand=self.detail_scroll.set)
        self.detail_scroll.pack(side="left", fill="y", padx=(3, 8))
        self.detail_media = ttk.Frame(self.detail_content, style="Surface.TFrame")
        self.detail_media.pack(side="right", padx=(12, 0))
        self.detail_cover = ttk.Label(self.detail_media, text="Без обложки", anchor="center", width=30,
                                      style="Surface.TLabel")
        self.detail_cover.pack(fill="x")
        self.detail_gallery_caption = ttk.Label(self.detail_media, text="", anchor="w", wraplength=230,
                                                style="Muted.TLabel")
        self.detail_gallery_caption.pack(fill="x", pady=(5, 0))
        self.detail_gallery_controls = ttk.Frame(self.detail_media)
        self.detail_gallery_controls.pack(fill="x", pady=(4, 0))
        self.detail_gallery_previous = ttk.Button(self.detail_gallery_controls, text="‹ Назад", width=9,
                                                   command=lambda: self._show_gallery_image(-1))
        self.detail_gallery_previous.pack(side="left")
        self.detail_gallery_counter = ttk.Label(self.detail_gallery_controls, text="", anchor="center")
        self.detail_gallery_counter.pack(side="left", fill="x", expand=True)
        self.detail_gallery_next = ttk.Button(self.detail_gallery_controls, text="Вперёд ›", width=9,
                                               command=lambda: self._show_gallery_image(1))
        self.detail_gallery_next.pack(side="right")
        self.detail_gallery_items = []
        self.detail_gallery_index = 0
        self.detail_cover_image = None
        box.pack(fill="x", side="bottom", pady=(6, 0))
        actions = ttk.Frame(bottom, padding=(0, 7))
        self.row_action_buttons = []
        for label, callback, button_style in (("＋ Добавить", self.add, "Primary.TButton"), ("✎ Изменить", self.edit, "TButton"), ("⧉ Дублировать", self.duplicate_selected, "TButton"), ("− Удалить", self.delete, "Danger.TButton"), ("↑ Выше", lambda: self.move_selected(-1), "TButton"), ("↓ Ниже", lambda: self.move_selected(1), "TButton"), ("Открыть ссылку", self.open_link, "TButton")):
            button = ttk.Button(actions, text=label, command=callback, style=button_style)
            button.pack(side="left", padx=(0, 8))
            self.row_action_buttons.append((button, button_style))
        self.count_label = ttk.Label(actions, style="Muted.TLabel")
        self.count_label.pack(side="right")
        self.compact_details_button = ttk.Button(actions, text="▣ Карточка проекта",
                                                 command=self.open_details_window)
        actions.pack(fill="x", side="top")

    def _schedule_density_update(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if self._density_after is not None:
            try:
                self.root.after_cancel(self._density_after)
            except tk.TclError:
                pass
        self._density_after = self.root.after(90, self._update_layout_density)

    def _update_layout_density(self, height=None):
        self._density_after = None
        height = int(height or max(1, self.root.winfo_height()))
        density = desktop_density_for_height(height)
        if density == self._layout_density:
            self._update_project_card_layout()
            return
        self._layout_density = density
        self.details_label.configure(height={"tight": 3, "compact": 5, "comfortable": 6}[density])
        style = ttk.Style(self.root)
        style.configure("Hero.Title.TLabel", font=("Segoe UI", 20 if density == "tight" else 24, "bold"))
        style.configure("Compact.TButton", padding=(6, 5), background=DESKTOP_PALETTE["surface"],
                        foreground=DESKTOP_PALETTE["ink"], bordercolor=DESKTOP_PALETTE["border"],
                        font=("Segoe UI", 8, "bold"), focusthickness=2)
        self.hero_panel.configure(padding=(18, 8 if density == "tight" else 14))
        self.filter_panel.configure(padding=(10, 6) if density == "tight" else 12)
        if density == "comfortable":
            if not self.detail_box.winfo_manager():
                self.detail_box.pack(fill="x", side="bottom", pady=(6, 0))
            self.compact_details_button.pack_forget()
        else:
            self.detail_box.pack_forget()
            for button, _default_style in self.row_action_buttons:
                button.configure(style="Compact.TButton")
                button.pack_configure(padx=(0, 4))
            self.count_label.configure(text=f"{len(self.visible)} / {len(self.portfolio.projects)}")
            self.compact_details_button.configure(text="Карточка", style="Compact.TButton")
            if not self.compact_details_button.winfo_manager():
                self.compact_details_button.pack(side="left", padx=(0, 4))
        if density == "comfortable":
            for button, default_style in self.row_action_buttons:
                button.configure(style=default_style)
                button.pack_configure(padx=(0, 8))
        if self.hero_art_label is not None and Image is not None and ImageOps is not None and ImageTk is not None:
            width = self.root.winfo_width()
            if width <= 1:
                width = self.initial_window_width
            ratio = {"tight": 0.19, "compact": 0.235, "comfortable": 0.285}[density]
            art_width = min(390, max(160, int(width * ratio)))
            art_size = (art_width, max(64, int(art_width * 0.36)))
            try:
                with Image.open(DESKTOP_HERO_ART_PATH) as source:
                    art = ImageOps.fit(source.convert("RGB"), art_size,
                                       method=Image.Resampling.LANCZOS, centering=(0.80, 0.5))
                self.hero_art = ImageTk.PhotoImage(art, master=self.hero_art_label)
                self.hero_art_label.configure(image=self.hero_art)
            except _COVER_ERRORS:
                pass
        if self.detail_gallery_items:
            self._show_gallery_image()
        self._update_project_card_layout()

    def _update_project_card_layout(self):
        if not hasattr(self, "card_grid"):
            return
        width = max(320, int(self.root.winfo_width()))
        columns, art_size = desktop_project_card_layout(width)
        signature = (columns, art_size)
        if signature != self._card_layout_signature:
            self._render_project_cards()

    def open_details_window(self):
        project = self.selected(False)
        if project is None:
            return
        win = tk.Toplevel(self.root)
        win.title(f"Карточка проекта — {project.title}")
        win.transient(self.root)
        return_focus = self.root.focus_get()
        screen_width, screen_height = win.winfo_screenwidth(), win.winfo_screenheight()
        (width, height), minimum = fit_window_dimensions(
            screen_width, screen_height, (1040, 700), (680, 480))
        x, y = center_window_position(screen_width, screen_height, width, height)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.resizable(True, True)
        win.minsize(*minimum)
        surface = ttk.Frame(win, padding=18)
        surface.pack(fill="both", expand=True)
        surface.columnconfigure(0, weight=1)
        surface.rowconfigure(0, weight=1)
        story = tk.Text(surface, wrap="word", state="normal", background=DESKTOP_PALETTE["surface"],
                        foreground=DESKTOP_PALETTE["ink"], relief="flat", borderwidth=0,
                        padx=12, pady=10, font=("Segoe UI", 10), takefocus=True)
        story.grid(row=0, column=0, sticky="nsew")
        story.insert("1.0", self.details_label.get("1.0", "end-1c"))
        story.configure(state="disabled")
        scroll = ttk.Scrollbar(surface, orient="vertical", command=story.yview)
        story.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        media_items = desktop_project_media_items(project)
        media = ttk.Frame(surface, style="Surface.TFrame", padding=8)
        media.grid(row=0, column=2, sticky="n", padx=(16, 0))
        image = ttk.Label(media, anchor="center", style="Surface.TLabel", width=40,
                          takefocus=False)
        image.pack(fill="x")
        caption = ttk.Label(media, anchor="w", justify="left", wraplength=320,
                            style="Muted.TLabel")
        caption.pack(fill="x", pady=(8, 0))
        counter = ttk.Label(media, anchor="w", justify="left", style="Muted.TLabel")
        counter.pack(fill="x", pady=(6, 0))
        controls = ttk.Frame(media, style="Surface.TFrame")
        controls.pack(fill="x", pady=(8, 0))
        previous_button = ttk.Button(controls, text="← Предыдущее", takefocus=True)
        previous_button.pack(side="left")
        next_button = ttk.Button(controls, text="Следующее →", takefocus=True)
        next_button.pack(side="right")
        gallery_state = {"index": 0}

        def show_media(index: int) -> None:
            if not media_items:
                image.configure(image="", text="Для этого кейса пока нет изображений")
                image.image = None
                caption.configure(text="В кейс можно добавить обложку и изображения галереи.")
                counter.configure(text="Изображений пока нет")
                previous_button.configure(state="disabled")
                next_button.configure(state="disabled")
                return
            gallery_state["index"] = index % len(media_items)
            data, path, description, position = media_items[gallery_state["index"]]
            self._show_cover(image, data, path, (320, 190),
                             empty_text=description, position=position)
            # Keep the image description visible even when a local image cannot be decoded.
            caption.configure(text=f"Описание: {description or 'не указано'}")
            counter.configure(text=f"Изображение {gallery_state['index'] + 1} из {len(media_items)}")
            state = "normal" if len(media_items) > 1 else "disabled"
            previous_button.configure(state=state)
            next_button.configure(state=state)

        def move_media(direction: int) -> None:
            if media_items:
                show_media(gallery_state["index"] + direction)

        previous_button.configure(command=lambda: move_media(-1))
        next_button.configure(command=lambda: move_media(1))
        show_media(0)
        win.bind("<Left>", lambda _event: move_media(-1) if len(media_items) > 1 else None)
        win.bind("<Right>", lambda _event: move_media(1) if len(media_items) > 1 else None)
        win.bind("<Escape>", lambda _event: win.destroy())
        def close_dialog(_event=None):
            try:
                win.grab_release()
            except tk.TclError:
                pass
            if win.winfo_exists():
                win.destroy()
            if return_focus is not None:
                try:
                    return_focus.focus_set()
                except tk.TclError:
                    pass

        close_button = ttk.Button(surface, text="Закрыть", command=close_dialog)
        close_button.grid(
            row=1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        win.bind("<Escape>", close_dialog)
        win.protocol("WM_DELETE_WINDOW", close_dialog)
        win.grab_set()
        win.after_idle(story.focus_set)

    def _demo_data(self):
        demo = [
            LandingProject(
                "Портфолио веб-разработчика",
                "Учебный пример: персональный сайт с проектами и контактами.",
                "2026-09-20", "Опубликован",
                [Technology("HTML", version="5"), Technology("CSS", version="3"), Technology("JavaScript")],
                "https://example.com", page_count=4,
                role="Индивидуальный учебный проект",
                outcome="Собраны карточки проектов, стек технологий и контактная информация.",
                tags=["портфолио", "учебный проект"],
                context="Нужно было показать учебные проекты и упростить просмотр работ.",
                solution="Создать адаптивную витрину с карточками, технологиями и подробностями кейса.",
                process="Сбор требований, построение структуры страниц, разработка интерфейса и ручная проверка.",
                featured=True, cover_image="./assets/covers/portfolio-studio.webp",
            ),
            WebAppProject(
                "CRM для клининговой компании",
                "Демо-запись для проверки карточек, поиска и статусов.",
                "2026-09-22", "В разработке",
                [Technology("Python"), Technology("Flask"), Technology("SQLite", "СУБД")],
                repository_url="https://github.com/example/cleaning-crm",
                backend_stack="Flask, SQLite", role="Учебный пример",
                outcome="Показаны связи между клиентами, заказами и сотрудниками.",
                tags=["CRM", "автоматизация"],
                cover_image="./assets/covers/cleaning-crm.webp",
            ),
            WebAppProject(
                "Карта городских дворов",
                "Демо-запись интерактивного проекта с картой.",
                "2026-09-25", "Завершён",
                [Technology("JavaScript"), Technology("Leaflet.js")],
                "https://example.com/map",
                repository_url="https://github.com/example/courtyards",
                backend_stack="REST API", role="Учебный пример",
                outcome="Инфраструктурные объекты представлены на интерактивной карте.",
                tags=["карта", "городская среда"],
                cover_image="./assets/covers/city-courtyards.webp",
            ),
        ]
        for p in demo:
            self.portfolio.add(p)

    def _load_startup_data(self):
        if self.data_path and self.data_path.exists():
            try:
                self._read_data(self.data_path)
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
                self.data_path = None
                self._demo_data()
                self.refresh()
                error_text = str(exc)
                self.root.after_idle(lambda: messagebox.showerror(
                    "Не удалось открыть данные",
                    f"База данных повреждена или имеет неверный формат.\n{error_text}\n\nИсходный файл оставлен без изменений; открыт демонстрационный набор.",
                    parent=self.root))
                return
        else:
            legacy_json = self.data_path.with_name("portfolio_data.json") if self.data_path else Path(__file__).with_name("portfolio_data.json")
            if legacy_json.exists():
                try:
                    self._read_data(legacy_json)
                    sqlite_path = default_data_path()
                    self.data_path = sqlite_path
                    if self.save(silent=True):
                        self._set_details("Существующий JSON перенесён в SQLite. JSON сохранён как резервная копия.")
                    else:
                        self.data_path = legacy_json
                        self._set_details("Не удалось перенести JSON в SQLite. Продолжена работа с исходным JSON.")
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    self.data_path = None
                    self._demo_data()
                    error_text = str(exc)
                    self.root.after_idle(lambda text=error_text: messagebox.showerror("Ошибка переноса", f"Не удалось перенести JSON в SQLite. Исходный файл не изменён.\n{text}", parent=self.root))
            else:
                self._demo_data()
                self.save(silent=True)
        self.refresh()

    def _set_details(self, value: str) -> None:
        if not hasattr(self, "details_label"):
            return
        self.details_label.configure(state="normal")
        self.details_label.delete("1.0", "end")
        self.details_label.insert("1.0", value)
        self.details_label.configure(state="disabled")
        self.details_label.yview_moveto(0)

    def _portfolio_snapshot(self):
        """Capture the in-memory fields mutated by normal portfolio actions."""
        projects = list(self.portfolio.projects)
        return projects, self.portfolio.next_id, {
            project.project_id: project.sort_order for project in projects
        }

    def _persist_portfolio_change(self, snapshot) -> bool:
        """Persist a completed mutation or restore the previous in-memory state."""
        if not self.data_path or self.save(silent=True):
            return True
        projects, next_id, sort_orders = snapshot
        self.portfolio.projects = projects
        self.portfolio.next_id = next_id
        for project in projects:
            project.sort_order = sort_orders[project.project_id]
        self.refresh()
        return False

    def refresh(self):
        if not hasattr(self, "tree"):
            return
        selected = self.selected(False)
        selected_id = selected.project_id if selected else None
        kind, status = self.type_filter.get(), self.status_filter.get()
        tag = self.tag_filter.get()
        tag_values = sorted({label for project in self.portfolio.projects for label in project.tags}, key=str.casefold)
        self.tag_combo.configure(values=("Все теги", *tag_values))
        if tag != "Все теги" and tag.casefold() not in {label.casefold() for label in tag_values}:
            self.tag_filter.set("Все теги")
            tag = "Все теги"
        rows = self.portfolio.search(self.query.get())
        self.visible = [p for p in rows if (kind == "Все типы" or p.project_type == kind)
                        and (status == "Все статусы" or p.status == status)
                        and (tag == "Все теги" or any(value.casefold() == tag.casefold() for value in p.tags))
                        and (not self.featured_only.get() or p.featured)]
        self._sort_visible()
        visible_ids = {p.project_id for p in self.visible}
        if selected_id not in visible_ids:
            selected_id = self.visible[0].project_id if self.visible else None
        self._render_visible(selected_id)
        self._render_project_cards()
        self.count_label.config(text=(f"{len(self.visible)} / {len(self.portfolio.projects)}"
                                      if getattr(self, "_layout_density", "comfortable") != "comfortable"
                                      else f"Показано {len(self.visible)} из {len(self.portfolio.projects)}"))
        if not self.visible:
            has_projects = bool(self.portfolio.projects)
            self.empty_state_title.configure(text=("По этим условиям проектов нет" if has_projects
                                                   else "Ваше портфолио начинается с первого кейса"))
            self.empty_state_description.configure(text=("Измените запрос или сбросьте фильтры, чтобы снова увидеть проекты."
                                                          if has_projects else "Добавьте проект, чтобы сохранить описание, изображения и ссылки."))
            self.empty_state_action.configure(text=("Сбросить фильтры" if has_projects else "Добавить первый проект"),
                                               command=(self.reset_filters if has_projects else self.add))
            self.tree.grid_remove()
            self.tree_vertical_scroll.grid_remove()
            self.tree_horizontal_scroll.grid_remove()
            self.table_view.pack_forget()
            self.card_view.pack_forget()
            self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
            self._set_details("")
            self.detail_media.pack_forget()
            self.detail_cover.pack_forget()
        else:
            self.empty_state.place_forget()
            self.tree.grid()
            self.tree_vertical_scroll.grid()
            self.tree_horizontal_scroll.grid()
            self._set_project_view(getattr(self, "view_mode", "table"))
        self.footer.config(text=(f"{self.developer.full_name} · автосохранение: {self.data_path.name}"
                                 if self.data_path else f"{self.developer.full_name} · демонстрационный набор"))

    def _set_project_view(self, mode: str) -> None:
        """Switch between a visual case gallery and the sortable table."""
        if mode not in {"cards", "table"} or not hasattr(self, "table_view"):
            return
        self.view_mode = mode
        self.card_view.pack_forget()
        self.table_view.pack_forget()
        (self.card_view if mode == "cards" else self.table_view).pack(fill="both", expand=True)
        self.card_view_button.configure(style="Primary.TButton" if mode == "cards" else "TButton")
        self.table_view_button.configure(style="Primary.TButton" if mode == "table" else "TButton")
        self.card_canvas.yview_moveto(0)

    def _select_card_project(self, project_id: int, *, open_details: bool = False) -> None:
        item = str(project_id)
        if item not in self.tree.get_children():
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.show_details()
        if open_details:
            self.open_details_window()

    def _edit_card_project(self, project_id: int) -> None:
        self._select_card_project(project_id)
        self.edit()

    def _scroll_project_cards(self, event):
        self.card_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def _bind_project_card_wheel(self, widget) -> None:
        """Forward Windows wheel events from nested card controls to the gallery."""
        widget.bind("<MouseWheel>", self._scroll_project_cards, add="+")
        for child in widget.winfo_children():
            self._bind_project_card_wheel(child)

    def _render_project_cards(self) -> None:
        if not hasattr(self, "card_grid"):
            return
        for child in self.card_grid.winfo_children():
            child.destroy()
        window_width = max(320, int(self.root.winfo_width()))
        card_columns, card_art_size = desktop_project_card_layout(window_width)
        self._card_layout_signature = (card_columns, card_art_size)
        for column in range(2):
            self.card_grid.columnconfigure(column, weight=1 if column < card_columns else 0,
                                          uniform="project-cards" if column < card_columns else "")
        for index, project in enumerate(getattr(self, "visible", ())):
            card = ttk.Frame(self.card_grid, style="Surface.TFrame", padding=12,
                             relief="solid", borderwidth=1)
            card.grid(row=index // card_columns, column=index % card_columns, sticky="nsew",
                      padx=(0, 10), pady=(0, 10))
            card.columnconfigure(0, weight=1)
            cover = ttk.Label(card, text="ВИЗУАЛЬНЫЙ КЕЙС", anchor="center",
                              style="Surface.TLabel")
            cover.grid(row=0, column=0, sticky="ew")
            self._show_cover(cover, project.cover_image_data, project.cover_image,
                             card_art_size, empty_text="ВИЗУАЛЬНЫЙ КЕЙС",
                             position=normalize_cover_position(project.cover_position))
            heading = ttk.Frame(card, style="Surface.TFrame")
            heading.grid(row=1, column=0, sticky="ew", pady=(10, 4))
            heading.columnconfigure(0, weight=1)
            ttk.Label(heading, text=project.title, style="Surface.TLabel",
                      font=("Segoe UI", 14, "bold"), wraplength=440,
                      justify="left").grid(row=0, column=0, sticky="w")
            ttk.Label(heading, text=project.status.upper(), style="Muted.TLabel",
                      padding=(7, 4)).grid(row=0, column=1, sticky="ne", padx=(8, 0))
            ttk.Label(card, text=f"{project.project_type}   ·   {project.created_at}",
                      style="Muted.TLabel", wraplength=480,
                      justify="left").grid(row=2, column=0, sticky="w", pady=(0, 6))
            summary = project.outcome or project.description
            ttk.Label(card, text=summary, style="Surface.TLabel", wraplength=480,
                      justify="left").grid(row=3, column=0, sticky="ew", pady=(0, 8))
            stack = ", ".join(technology.get_info()
                               for technology in project.technologies) or "Стек не указан"
            ttk.Label(card, text=stack, style="Muted.TLabel", wraplength=480,
                      justify="left").grid(row=4, column=0, sticky="w", pady=(0, 9))
            actions = ttk.Frame(card, style="Surface.TFrame")
            actions.grid(row=5, column=0, sticky="ew")
            ttk.Button(actions, text="Открыть кейс  →",
                       command=lambda pid=project.project_id: self._select_card_project(
                           pid, open_details=True), style="Primary.TButton").pack(side="left")
            ttk.Button(actions, text="Изменить",
                       command=lambda pid=project.project_id: self._edit_card_project(pid),
                       style="Compact.TButton").pack(side="left", padx=(7, 0))
            self._bind_project_card_wheel(card)

    def _sort_visible(self):
        keys = {
            "title": lambda p: p.title.casefold(),
            "type": lambda p: p.project_type.casefold(),
            "status": lambda p: p.status.casefold(),
            "date": lambda p: p.created_at,
            "pages": lambda p: getattr(p, "page_count", 0),
            "tech": lambda p: ", ".join(t.get_info() for t in p.technologies).casefold(),
            "featured": lambda p: (not p.featured, p.sort_order or p.project_id, p.title.casefold()),
        }
        self.visible.sort(key=keys[self.sort_column], reverse=not self.sort_ascending)

    def _render_visible(self, selected_id=None):
        self.tree.delete(*self.tree.get_children())
        for row_index, p in enumerate(self.visible):
            self.tree.insert("", "end", iid=str(p.project_id), values=(
                ("★ " if p.featured else "") + p.title, p.project_type, p.status,
                p.created_at, getattr(p, "page_count", "—"),
                ", ".join(t.get_info() for t in p.technologies), "Да" if p.featured else ""),
                tags=desktop_table_row_tags(row_index))
        if selected_id is not None and str(selected_id) in self.tree.get_children():
            self.tree.selection_set(str(selected_id))
            self.tree.focus(str(selected_id))
            self.show_details()

    def reset_filters(self):
        self.query.set("")
        self.type_filter.set("Все типы")
        self.status_filter.set("Все статусы")
        self.tag_filter.set("Все теги")
        self.featured_only.set(False)
        self.refresh()

    def selected(self, notify=True):
        sel = self.tree.selection()
        if not sel:
            if notify:
                messagebox.showinfo("Выбор проекта", "Сначала выберите проект.", parent=self.root)
            return None
        pid = int(sel[0])
        return next((p for p in self.portfolio.projects if p.project_id == pid), None)

    def show_details(self):
        p = self.selected(False)
        if p:
            extra = f"\nКоличество страниц: {p.page_count}" if isinstance(p, LandingProject) else f"\nСерверная часть: {p.backend_stack or 'не указана'}"
            links = f"\nДемо: {p.demo_url or 'не указано'}"
            if isinstance(p, WebAppProject):
                links += f"\nРепозиторий: {p.repository_url or 'не указан'}"
            tags = ", ".join(p.tags) or "не указаны"
            story = "".join(f"\n\n{heading}:\n{content}" for heading, content in (
                ("Контекст задачи", p.context), ("Решение", p.solution),
                ("Этапы работы", p.process), ("Метрики", p.metrics)) if content)
            gallery_notes = "".join(f"\nИзображение галереи №{i}: {image['alt']}" for i, image in enumerate(p.gallery_images, 1))
            self._set_details(f"{p.get_info()}\nМоя роль: {p.role or 'не указана'}\nРезультат: {p.outcome or 'не указан'}{story}{gallery_notes}\nТеги: {tags}\nСоздан: {p.created_at}{extra}{links}")
            self.detail_gallery_items = desktop_project_media_items(p)
            if self.detail_gallery_items:
                self.detail_gallery_index = 0
                if not self.detail_media.winfo_manager():
                    self.detail_media.pack(side="right", padx=(12, 0))
                self._show_gallery_image()
            else:
                self.detail_media.pack_forget()
        else:
            self.detail_media.pack_forget()

    def _show_gallery_image(self, direction: int = 0):
        if not self.detail_gallery_items:
            return
        self.detail_gallery_index = (self.detail_gallery_index + direction) % len(self.detail_gallery_items)
        data, path, description, position = self.detail_gallery_items[self.detail_gallery_index]
        self._show_cover(self.detail_cover, data, path, desktop_detail_art_size(self._layout_density),
                         empty_text=description, position=position)
        self.detail_gallery_caption.configure(text=description)
        self.detail_gallery_counter.configure(text=f"{self.detail_gallery_index + 1} / {len(self.detail_gallery_items)}")
        self.detail_gallery_previous.configure(state="normal" if len(self.detail_gallery_items) > 1 else "disabled")
        self.detail_gallery_next.configure(state="normal" if len(self.detail_gallery_items) > 1 else "disabled")

    def _cover_source(self, cover_data: str, cover_path: str):
        if cover_data:
            if not is_valid_cover_image(cover_data, data_url=True):
                return None
            header, encoded = cover_data.split(",", 1)
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, base64.binascii.Error):
                return None
            return io.BytesIO(raw)
        if not is_valid_cover_image(cover_path):
            return None
        project_root = RESOURCE_ROOT
        file_name = Path(cover_path).name
        file_name = BUILTIN_COVER_ALIASES.get(file_name, file_name)
        # Imported web demo records use ./assets/covers/... too. Resolve them
        # inside the bundled web asset tree when the desktop copy has no
        # duplicate desktop-only cover folder.
        for covers_root in (
            project_root / "assets" / "covers",
            project_root / "web" / "assets" / "covers",
        ):
            covers_root = covers_root.resolve()
            path = (covers_root / file_name).resolve()
            try:
                path.relative_to(covers_root)
            except ValueError:
                continue
            if path.is_file():
                return path
        return None

    def _show_cover(self, widget, cover_data, cover_path, size, empty_text="Без обложки", position=None):
        widget.configure(image="", text=empty_text)
        widget.image = None
        try:
            source = self._cover_source(cover_data, cover_path)
            if source is None:
                return
            if Image is not None and ImageTk is not None:
                with Image.open(source) as opened:
                    if opened.format not in {"PNG", "JPEG", "WEBP"} or opened.width * opened.height > 30_000_000:
                        return
                    if position and ImageOps is not None:
                        x, y = position.split()
                        opened = ImageOps.fit(opened.convert("RGB"), size, method=Image.Resampling.LANCZOS,
                            centering=(int(x[:-1]) / 100, int(y[:-1]) / 100))
                    else:
                        opened.thumbnail(size, Image.Resampling.LANCZOS)
                    preview = ImageTk.PhotoImage(opened.convert("RGB"), master=widget)
            elif (cover_data.startswith("data:image/png;") if cover_data else str(source).lower().endswith(".png")):
                preview = tk.PhotoImage(master=widget, data=cover_data.split(",", 1)[1]) if cover_data else tk.PhotoImage(master=widget, file=str(source))
                factor = max(1, (preview.width() + size[0] - 1) // size[0], (preview.height() + size[1] - 1) // size[1])
                if factor > 1:
                    preview = preview.subsample(factor, factor)
            else:
                widget.configure(text="Для предпросмотра JPG/WebP установите Pillow")
                return
            widget.configure(image=preview, text="")
            widget.image = preview
        except _COVER_ERRORS:
            widget.configure(text="Не удалось прочитать обложку")

    def add(self):
        self.edit_dialog()

    def edit(self):
        p = self.selected()
        if p:
            self.edit_dialog(p)

    def edit_dialog(self, old=None):
        win = tk.Toplevel(self.root)
        win.title("Редактировать проект" if old else "Добавить проект")
        win.transient(self.root)
        win.grab_set()
        screen_width, screen_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        (dialog_width, dialog_height), dialog_minimum = fit_window_dimensions(
            screen_width, screen_height, (1280, 860), (720, 480)
        )
        win.geometry(f"{dialog_width}x{dialog_height}")
        win.minsize(*dialog_minimum)
        actions = ttk.Frame(win, padding=(16, 10), takefocus=False)
        actions.pack(side="bottom", fill="x")
        body = ttk.Frame(win, takefocus=False)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, highlightthickness=0, borderwidth=0,
                           background=DESKTOP_PALETTE["background"], takefocus=False)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview, takefocus=False)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        frame = ttk.Frame(canvas, padding=16, takefocus=False)
        frame_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(frame_window, width=event.width))
        frame.columnconfigure(1, weight=1)
        initial_kind = old.project_type if old else self.TYPES[0]
        kind = tk.StringVar(value=initial_kind)
        ttk.Label(frame, text="Тип", takefocus=False).grid(row=0, column=0, sticky="w", pady=4)
        kind_widget = ttk.Combobox(frame, textvariable=kind, values=self.TYPES, state="readonly", width=44)
        kind_widget.grid(row=0, column=1, sticky="ew", pady=4)
        values = {
            "Название *": old.title if old else "", "Описание *": old.description if old else "",
            "Дата (ГГГГ-ММ-ДД)": old.created_at if old else date.today().isoformat(),
            "Статус": old.status if old else "В разработке", "Демо URL": old.demo_url if old else "",
            "Технологии через запятую": ", ".join(t.name for t in old.technologies) if old else "",
            "Теги через запятую": ", ".join(old.tags) if old else "",
            "Моя роль в проекте": old.role if old else "",
            "Результат / польза": old.outcome if old else "",
            "Контекст задачи": old.context if old else "",
            "Решение": old.solution if old else "",
            "Этапы процесса": old.process if old else "",
            "Метрики результата": old.metrics if old else "",
            "Количество страниц": str(getattr(old, "page_count", 1)),
            "Ссылка на репозиторий": getattr(old, "repository_url", ""),
            "Серверная часть": getattr(old, "backend_stack", "")}
        fields, field_labels = {}, {}
        # The cover panel needs its own ~260 px column in addition to the
        # project fields. Decide from the actual dialog width, not the monitor
        # width, or it gets clipped on common 1366 px displays.
        # Keep the cover section in normal document flow for the standard
        # dialog width. The form's text column should never push it beyond the
        # canvas edge; only a genuinely wider dialog may use a side column.
        narrow_layout = dialog_width < 1900
        featured = tk.BooleanVar(value=old.featured if old else False)
        cover_image = tk.StringVar(value=old.cover_image if old else "")
        cover_image_data = tk.StringVar(value=old.cover_image_data if old else "")
        cover_position = tk.StringVar(value=normalize_cover_position(old.cover_position) if old else "50% 46%")
        cover_position_mobile = tk.StringVar(value=normalize_cover_position(old.cover_position_mobile) if old and old.cover_position_mobile else "")
        cover_crop_mode = tk.StringVar(value="desktop")
        crop_mode_loading = {"active": False}
        gallery_images = copy.deepcopy(old.gallery_images) if old else []

        for row, (label, value) in enumerate(values.items(), start=2):
            field_labels[label] = ttk.Label(frame, text=label, takefocus=False)
            field_labels[label].grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=value)
            fields[label] = var
            if label in {"Описание *", "Контекст задачи", "Решение", "Этапы процесса",
                         "Результат / польза", "Метрики результата"}:
                # Descriptions and outcome evidence are prose, so keep them
                # comfortably readable and editable without forcing one long line.
                text_height = 3 if label == "Описание *" else 2
                widget = tk.Text(frame, width=47, height=text_height, wrap="word", undo=True,
                                 background=DESKTOP_PALETTE["surface"],
                                 foreground=DESKTOP_PALETTE["ink"],
                                 insertbackground=DESKTOP_PALETTE["ink"],
                                 highlightthickness=2,
                                 highlightbackground=DESKTOP_PALETTE["border"],
                                 highlightcolor=DESKTOP_PALETTE["accent"],
                                 relief="flat", borderwidth=0,
                                 takefocus=True)
                widget.insert("1.0", value)
                widget.bind("<KeyRelease>", lambda _event, target=widget, variable=var: variable.set(target.get("1.0", "end-1c")))
            elif label == "Статус":
                widget = ttk.Combobox(frame, textvariable=var, values=self.STATUSES, state="readonly", width=44)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=47)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            fields[label + "__widget"] = widget
        case_guide = ttk.LabelFrame(frame, text="История кейса — необязательно", padding=10,
                                    style="Surface.TLabelframe", takefocus=False)
        case_guide.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        case_guide.columnconfigure((0, 1), weight=1, uniform="case-guide")
        guide_summary = ttk.Frame(case_guide, style="Surface.TFrame", takefocus=False)
        guide_summary.grid(row=0, column=0, columnspan=2, sticky="ew")
        guide_summary.columnconfigure(0, weight=1)
        ttk.Label(guide_summary, text="Опишите только то, что можете подтвердить.",
                  style="Muted.TLabel", takefocus=False).grid(row=0, column=0, sticky="w")
        case_guide_count = ttk.Label(guide_summary, text="0 из 6", style="Surface.TLabel",
                                     font=("Segoe UI", 9, "bold"), takefocus=False)
        case_guide_count.grid(row=0, column=1, sticky="e", padx=(12, 0))
        case_guide_progress = ttk.Progressbar(case_guide, maximum=6, mode="determinate",
                                              style="CaseGuide.Horizontal.TProgressbar",
                                              takefocus=False)
        case_guide_progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 5))
        guide_description = ttk.Label(
            case_guide,
            text="Задача и контекст · Ваша роль · Решение · Этапы · Результат/метрики · Визуальные доказательства",
            style="Muted.TLabel", wraplength=680, justify="left", takefocus=False)
        guide_description.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        case_guide.bind("<Configure>",
                        lambda event: guide_description.configure(wraplength=max(240, event.width - 24)),
                        add="+")
        guide_items = ("Задача и контекст", "Ваша роль", "Выбранное решение",
                       "Этапы работы", "Результат или подтверждённые метрики",
                       "Обложка или изображения процесса")
        case_guide_labels = []
        for index, item in enumerate(guide_items):
            guide_label = ttk.Label(case_guide, text=f"○  {item}", style="Muted.TLabel",
                                    wraplength=320, takefocus=False)
            guide_label.grid(row=3 + index // 2, column=index % 2, sticky="w",
                             padx=(0, 12), pady=2)
            case_guide_labels.append(guide_label)

        def refresh_case_story_guide(*_):
            states = case_story_completion_states(
                fields["Контекст задачи"].get(), fields["Моя роль в проекте"].get(),
                fields["Решение"].get(), fields["Этапы процесса"].get(),
                fields["Результат / польза"].get(), fields["Метрики результата"].get(),
                bool(cover_image.get() or cover_image_data.get() or gallery_images),
            )
            completed = sum(states)
            case_guide_count.configure(text=f"{completed} из 6")
            case_guide_progress.configure(value=completed)
            for label, item, done in zip(case_guide_labels, guide_items, states):
                label.configure(text=f"{'✓' if done else '○'}  {item}",
                                foreground=(DESKTOP_PALETTE["ink"] if done
                                            else DESKTOP_PALETTE["muted"]))

        for key in ("Контекст задачи", "Моя роль в проекте", "Решение", "Этапы процесса",
                    "Результат / польза", "Метрики результата"):
            fields[key].trace_add("write", refresh_case_story_guide)
        cover_image.trace_add("write", refresh_case_story_guide)
        cover_image_data.trace_add("write", refresh_case_story_guide)
        refresh_case_story_guide()
        featured_widget = ttk.Checkbutton(frame, text="Добавить в избранные проекты", variable=featured)
        featured_widget.grid(
            row=len(values)+2, column=1, sticky="w", pady=(8, 0))
        cover_panel = ttk.LabelFrame(frame, text="Обложка проекта", padding=10, takefocus=False)
        if narrow_layout:
            cover_panel.grid(row=len(values) + 3, column=0, columnspan=2, sticky="ew", pady=(14, 4))
            cover_panel.columnconfigure(0, weight=1)
        else:
            cover_panel.grid(row=0, column=2, rowspan=len(values) + 3, sticky="n", padx=(18, 0), pady=4)
        cover_preview = ttk.Label(cover_panel, text="Без обложки", anchor="center", width=28,
                                  takefocus=False)
        cover_preview.pack(fill="both", pady=(0, 8))
        cover_preview_image = None
        crop_group = ttk.LabelFrame(cover_panel, text="Кадрирование обложки", padding=(8, 5))
        crop_group.pack(fill="x", pady=(0, 8))
        mode_row = ttk.Frame(crop_group)
        mode_row.pack(fill="x", pady=(0, 4))
        def selected_cover_position_var():
            return cover_position_mobile if cover_crop_mode.get() == "mobile" else cover_position
        def selected_cover_position():
            return selected_cover_position_var().get() or cover_position.get()
        def update_cover_crop_x(value):
            if crop_mode_loading["active"]:
                return
            variable = selected_cover_position_var()
            current = selected_cover_position().split()
            variable.set(f"{round(float(value))}% {current[1]}")
        def update_cover_crop_y(value):
            if crop_mode_loading["active"]:
                return
            variable = selected_cover_position_var()
            current = selected_cover_position().split()
            variable.set(f"{current[0]} {round(float(value))}%")
        def switch_cover_crop_mode():
            crop_mode_loading["active"] = True
            try:
                position = selected_cover_position().split()
                crop_x.set(int(position[0][:-1]))
                crop_y.set(int(position[1][:-1]))
            finally:
                crop_mode_loading["active"] = False
            refresh_cover_preview()
        ttk.Radiobutton(mode_row, text="Компьютер", variable=cover_crop_mode, value="desktop",
                        command=switch_cover_crop_mode).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(mode_row, text="Телефон", variable=cover_crop_mode, value="mobile",
                        command=switch_cover_crop_mode).pack(side="left")
        ttk.Label(crop_group, text="Телефонный кадр наследует положение компьютера, пока вы его не измените.",
                  wraplength=220, justify="left").pack(anchor="w", pady=(0, 4))
        ttk.Label(crop_group, text="По горизонтали").pack(anchor="w")
        crop_x = ttk.Scale(crop_group, from_=0, to=100, orient="horizontal",
                           command=update_cover_crop_x)
        crop_x.set(int(cover_position.get().split()[0][:-1]))
        crop_x.pack(fill="x")
        ttk.Label(crop_group, text="По вертикали").pack(anchor="w", pady=(4, 0))
        crop_y = ttk.Scale(crop_group, from_=0, to=100, orient="horizontal",
                           command=update_cover_crop_y)
        crop_y.set(int(cover_position.get().split()[1][:-1]))
        crop_y.pack(fill="x")
        cover_position.trace_add("write", lambda *_args: refresh_cover_preview())
        cover_position_mobile.trace_add("write", lambda *_args: refresh_cover_preview())
        def refresh_cover_preview():
            nonlocal cover_preview_image
            size = (230, 104) if cover_crop_mode.get() == "mobile" else (230, 145)
            self._show_cover(cover_preview, cover_image_data.get(), cover_image.get(), size,
                             position=selected_cover_position())
            cover_preview_image = cover_preview.image
        def choose_cover():
            file_path = filedialog.askopenfilename(
                parent=win, title="Выберите обложку проекта",
                filetypes=(("Изображения", "*.png *.jpg *.jpeg *.webp"), ("Все файлы", "*.*")))
            if not file_path:
                return
            try:
                data_url = encode_cover_image(file_path)
                cover_image.set("")
                cover_image_data.set(data_url)
                refresh_cover_preview()
            except _COVER_ERRORS as exc:
                messagebox.showerror("Не удалось добавить обложку", str(exc), parent=win)
        def remove_cover():
            cover_image.set("")
            cover_image_data.set("")
            refresh_cover_preview()
        def manage_gallery():
            draft = copy.deepcopy(gallery_images)
            editor = tk.Toplevel(win)
            editor.title("Галерея проекта")
            editor.transient(win)
            screen_width, screen_height = editor.winfo_screenwidth(), editor.winfo_screenheight()
            (editor_width, editor_height), editor_minimum = fit_window_dimensions(
                screen_width, screen_height, (860, 560), (680, 460)
            )
            editor.geometry(f"{editor_width}x{editor_height}")
            editor.minsize(*editor_minimum)
            wide_layout = screen_width >= 1000
            editor.columnconfigure(0, weight=1)
            editor.rowconfigure(0, weight=1)
            viewport = ttk.Frame(editor)
            viewport.grid(row=0, column=0, sticky="nsew")
            canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0,
                               background=DESKTOP_PALETTE["background"])
            gallery_scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=gallery_scrollbar.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            gallery_scrollbar.grid(row=0, column=1, sticky="ns")
            viewport.rowconfigure(0, weight=1)
            viewport.columnconfigure(0, weight=1)
            layout_frame = ttk.Frame(canvas)
            layout_window = canvas.create_window((0, 0), window=layout_frame, anchor="nw")
            layout_frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda event: canvas.itemconfigure(layout_window, width=event.width))
            if wide_layout:
                layout_frame.columnconfigure(1, weight=1)
                layout_frame.rowconfigure(0, weight=1)
            else:
                layout_frame.columnconfigure(0, weight=1)
            list_panel = ttk.Frame(layout_frame, padding=14)
            list_panel.grid(row=0, column=0, rowspan=1 if wide_layout else 2, sticky="nsew")
            ttk.Label(list_panel, text=f"Изображения · до {GALLERY_MAX_IMAGES}", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
            image_list = tk.Listbox(list_panel, width=27, height=17 if wide_layout else 8, exportselection=False)
            empty_hint = ttk.Label(list_panel,
                text="В галерее пока пусто.\nДобавьте кадры проекта, чтобы показать важные детали.",
                justify="center", wraplength=190, padding=12, style="Muted.TLabel")
            form_panel = ttk.Frame(layout_frame, padding=(0, 14, 14, 14))
            form_panel.grid(row=0 if wide_layout else 1, column=1 if wide_layout else 0, sticky="nsew")
            form_panel.columnconfigure(0, weight=1)
            preview = ttk.Label(form_panel, text="Выберите изображение", anchor="center", style="Surface.TLabel")
            preview.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            alt_label = ttk.Label(form_panel, text="Описание для экранных дикторов")
            alt_label.grid(row=1, column=0, sticky="w")
            alt_var = tk.StringVar()
            alt_entry = ttk.Entry(form_panel, textvariable=alt_var)
            alt_entry.grid(row=2, column=0, sticky="ew", pady=(4, 12))
            crop_label = ttk.Label(form_panel, text="Кадрирование · расположение объекта")
            crop_label.grid(row=3, column=0, sticky="w")
            x_var, y_var = tk.IntVar(value=50), tk.IntVar(value=50)
            x_label = ttk.Label(form_panel, text="По горизонтали")
            x_label.grid(row=4, column=0, sticky="w")
            x_scale = tk.Scale(form_panel, from_=0, to=100, orient="horizontal", showvalue=True, variable=x_var)
            x_scale.grid(row=5, column=0, sticky="ew")
            y_label = ttk.Label(form_panel, text="По вертикали")
            y_label.grid(row=6, column=0, sticky="w")
            y_scale = tk.Scale(form_panel, from_=0, to=100, orient="horizontal", showvalue=True, variable=y_var)
            y_scale.grid(row=7, column=0, sticky="ew")
            detail_widgets = (alt_label, alt_entry, crop_label, x_label, x_scale, y_label, y_scale)
            preview.image = None
            selected = [None]

            def sync_image():
                index = selected[0]
                if index is not None and index < len(draft):
                    draft[index]["alt"] = alt_var.get().strip()
                    draft[index]["position"] = f"{x_var.get()}% {y_var.get()}%"

            def select_image(_event=None):
                sync_image()
                chosen = image_list.curselection()
                selected[0] = chosen[0] if chosen else None
                index = selected[0]
                if index is None:
                    preview.configure(text="В галерее пока нет деталей.\nДобавьте изображения, чтобы настроить описание и кадрирование.", image="")
                    preview.image = None
                    alt_var.set("")
                    alt_entry.configure(state="disabled")
                    x_scale.configure(state="disabled")
                    y_scale.configure(state="disabled")
                    for widget in detail_widgets:
                        widget.grid_remove()
                    return
                item = draft[index]
                for widget in detail_widgets:
                    widget.grid()
                alt_entry.configure(state="normal")
                x_scale.configure(state="normal")
                y_scale.configure(state="normal")
                alt_var.set(item["alt"])
                try:
                    x, y = item["position"].split()
                    x_var.set(int(x[:-1])); y_var.set(int(y[:-1]))
                except (ValueError, IndexError):
                    x_var.set(50); y_var.set(50)
                self._show_cover(preview, item["image_data"], "", (520, 230), empty_text="", position=item["position"])
                preview.image = getattr(preview, "image", None)

            def update_crop(_value=None):
                index = selected[0]
                if index is None:
                    return
                item = draft[index]
                item["position"] = f"{x_var.get()}% {y_var.get()}%"
                self._show_cover(preview, item["image_data"], "", (520, 230), empty_text="", position=item["position"])

            def refresh_list(select_index=None):
                sync_image()
                image_list.delete(0, "end")
                for index, item in enumerate(draft, 1):
                    image_list.insert("end", f"{index}. {item['alt'] or 'Добавьте описание'}")
                if draft:
                    empty_hint.pack_forget()
                    if not image_list.winfo_manager():
                        image_list.pack(fill="both", expand=True)
                    order_actions.pack(fill="x")
                    remove_button.pack(fill="x", pady=2)
                else:
                    image_list.pack_forget()
                    empty_hint.pack(fill="both", expand=True)
                    order_actions.pack_forget()
                    remove_button.pack_forget()
                if select_index is not None and draft:
                    select_index = max(0, min(select_index, len(draft) - 1))
                    image_list.selection_set(select_index)
                    image_list.activate(select_index)
                    select_image()
                elif not draft:
                    selected[0] = None
                    select_image()
                index = selected[0]
                has_selection = index is not None and bool(draft)
                move_up_button.configure(state="normal" if has_selection and index > 0 else "disabled")
                move_down_button.configure(state="normal" if has_selection and index < len(draft) - 1 else "disabled")
                remove_button.configure(state="normal" if has_selection else "disabled")

            def add_images():
                paths = filedialog.askopenfilenames(parent=editor, title="Добавьте детали проекта",
                    filetypes=(("Изображения", "*.png *.jpg *.jpeg *.webp"), ("Все файлы", "*.*")))
                if not paths:
                    return
                if len(draft) + len(paths) > GALLERY_MAX_IMAGES:
                    messagebox.showwarning("Лимит галереи", f"Можно хранить до {GALLERY_MAX_IMAGES} изображений. Добавлю доступное количество.", parent=editor)
                    paths = paths[:max(0, GALLERY_MAX_IMAGES-len(draft))]
                for path in paths:
                    try:
                        used_chars = sum(len(image["image_data"]) for image in draft)
                        remaining_chars = GALLERY_MAX_TOTAL_DATA_CHARS - used_chars
                        encoded = encode_gallery_image(path, remaining_chars)
                    except _COVER_ERRORS as exc:
                        messagebox.showerror("Не удалось добавить изображение", str(exc), parent=editor)
                        continue
                    label = simpledialog.askstring("Описание изображения", "Коротко опишите, что изображено:",
                        initialvalue=Path(path).stem.replace("_", " ")[:180], parent=editor)
                    if label is None:
                        continue
                    draft.append({"image_data": encoded, "alt": label.strip(), "position": "50% 50%"})
                refresh_list(len(draft)-1)

            def remove_image():
                index = selected[0]
                if index is None:
                    return
                draft.pop(index)
                refresh_list(index)

            def move_image(direction):
                index = selected[0]
                target = index + direction if index is not None else -1
                if target < 0 or target >= len(draft):
                    return
                sync_image()
                draft[index], draft[target] = draft[target], draft[index]
                refresh_list(target)

            image_list.bind("<<ListboxSelect>>", select_image)
            x_scale.configure(command=update_crop)
            y_scale.configure(command=update_crop)
            list_actions = ttk.Frame(list_panel)
            list_actions.pack(fill="x", pady=(8, 0))
            add_button = ttk.Button(list_actions, text="＋ Добавить", command=add_images)
            add_button.pack(fill="x", pady=2)
            order_actions = ttk.Frame(list_actions)
            order_actions.pack(fill="x")
            move_up_button = ttk.Button(order_actions, text="↑ Выше", command=lambda: move_image(-1))
            move_up_button.pack(side="left", fill="x", expand=True, padx=(0, 2), pady=2)
            move_down_button = ttk.Button(order_actions, text="↓ Ниже", command=lambda: move_image(1))
            move_down_button.pack(side="left", fill="x", expand=True, padx=(2, 0), pady=2)
            remove_button = ttk.Button(list_actions, text="Удалить", command=remove_image)
            remove_button.pack(fill="x", pady=2)
            footer = ttk.Frame(editor, padding=12)
            footer.grid(row=1, column=0, sticky="ew")

            def save_gallery():
                sync_image()
                try:
                    normalized = normalize_gallery_images(draft)
                except ValueError as exc:
                    messagebox.showerror("Проверьте галерею", str(exc), parent=editor)
                    return
                gallery_images[:] = normalized
                gallery_button.configure(text=f"Галерея · {len(gallery_images)} из {GALLERY_MAX_IMAGES}")
                refresh_case_story_guide()
                editor.destroy()

            ttk.Button(footer, text="Отмена", command=editor.destroy).pack(side="left")
            ttk.Button(footer, text="Сохранить галерею", style="Primary.TButton", command=save_gallery).pack(side="right")
            refresh_list(0 if draft else None)
            def reveal_focused_field(event):
                widget = event.widget
                if not str(widget).startswith(str(layout_frame)):
                    return
                canvas.update_idletasks()
                region = canvas.bbox("all")
                if not region:
                    return
                viewport_top = canvas.canvasy(0)
                widget_top = widget.winfo_rooty() - canvas.winfo_rooty() + viewport_top
                widget_bottom = widget_top + widget.winfo_height()
                viewport_height = max(1, canvas.winfo_height())
                content_height = max(1, region[3] - region[1])
                if widget_top < viewport_top:
                    canvas.yview_moveto(max(0, widget_top / content_height))
                elif widget_bottom > viewport_top + viewport_height:
                    canvas.yview_moveto(max(0, (widget_bottom - viewport_height) / content_height))

            def scroll_gallery(event):
                if event.delta:
                    canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return "break"

            canvas.bind("<MouseWheel>", scroll_gallery, add="+")
            def bind_gallery_events(widget):
                widget.bind("<FocusIn>", reveal_focused_field, add="+")
                widget.bind("<MouseWheel>", scroll_gallery, add="+")
                for child in widget.winfo_children():
                    bind_gallery_events(child)
            bind_gallery_events(layout_frame)
            editor.after_idle(image_list.focus_set if draft else add_button.focus_set)
            editor.bind("<Escape>", lambda _event: editor.destroy())
            editor.protocol("WM_DELETE_WINDOW", editor.destroy)
        choose_cover_button = ttk.Button(cover_panel, text="Выбрать изображение…", command=choose_cover)
        choose_cover_button.pack(fill="x", pady=2)
        remove_cover_button = ttk.Button(cover_panel, text="Убрать обложку", command=remove_cover)
        remove_cover_button.pack(fill="x", pady=2)
        gallery_button = ttk.Button(cover_panel, text=f"Галерея · {len(gallery_images)} из {GALLERY_MAX_IMAGES}", command=manage_gallery)
        gallery_button.pack(fill="x", pady=(8, 2))
        refresh_cover_preview()
        type_specific = {
            "Количество страниц": kind,
            "Ссылка на репозиторий": kind,
            "Серверная часть": kind,
        }
        def update_type_fields(*_):
            landing = kind.get() == self.TYPES[0]
            visible_labels = {"Количество страниц"} if landing else {"Ссылка на репозиторий", "Серверная часть"}
            for label in type_specific:
                if label in visible_labels:
                    field_labels[label].grid()
                    fields[label + "__widget"].grid()
                else:
                    field_labels[label].grid_remove()
                    fields[label + "__widget"].grid_remove()
        kind.trace_add("write", update_type_fields)
        update_type_fields()
        def save_form():
            try:
                for label, variable in fields.items():
                    widget = fields.get(label + "__widget")
                    if isinstance(widget, tk.Text):
                        variable.set(widget.get("1.0", "end-1c"))
                title, desc = fields["Название *"].get().strip(), fields["Описание *"].get().strip()
                created = fields["Дата (ГГГГ-ММ-ДД)"].get().strip()
                demo, repo = fields["Демо URL"].get().strip(), fields["Ссылка на репозиторий"].get().strip()
                status = fields["Статус"].get()
                pages = validate_project_input(title, desc, created, status, demo, repo,
                                               kind.get(), fields["Количество страниц"].get())
                lost_fields = project_type_change_loss_fields(
                    initial_kind, kind.get(), fields["Количество страниц"].get(),
                    fields["Ссылка на репозиторий"].get(),
                    fields["Серверная часть"].get(), isinstance(old, LandingProject))
                if lost_fields and not messagebox.askyesno(
                        "Подтвердите смену типа",
                        "При сохранении проекта с новым типом не сохранятся поля:\n\n"
                        + "\n".join(f"• {label}" for label in lost_fields)
                        + "\n\nВыберите «Нет», чтобы вернуться к форме. Запись не изменится; переключите тип обратно, чтобы сохранить эти поля.",
                        parent=win, default=messagebox.NO):
                    return
                previous_tech = {t.name.casefold(): t for t in old.technologies} if old else {}
                tech = [previous_tech.get(x.strip().casefold(), Technology(x.strip()))
                        for x in fields["Технологии через запятую"].get().split(",") if x.strip()]
                base = dict(title=title, description=desc, created_at=created, status=status,
                            technologies=tech, demo_url=demo,
                            role=normalize_case_text(fields["Моя роль в проекте"].get(), "Ваша роль", 120),
                            outcome=normalize_case_text(fields["Результат / польза"].get(), "Результат", 500),
                            context=normalize_case_text(fields["Контекст задачи"].get(), "Контекст задачи", 500),
                            solution=normalize_case_text(fields["Решение"].get(), "Решение", 700),
                            process=normalize_case_text(fields["Этапы процесса"].get(), "Этапы процесса", 1500),
                            metrics=normalize_case_text(fields["Метрики результата"].get(), "Метрики результата", 300),
                            tags=normalize_tags(fields["Теги через запятую"].get()), featured=featured.get(),
                            cover_image=cover_image.get(), cover_image_data=cover_image_data.get(),
                            cover_position=normalize_cover_position(cover_position.get()),
                            cover_position_mobile=(normalize_cover_position(cover_position_mobile.get())
                                                    if cover_position_mobile.get() else None),
                            gallery_images=normalize_gallery_images(gallery_images))
                if kind.get() == self.TYPES[0]:
                    new = LandingProject(**base, page_count=pages)
                else:
                    new = WebAppProject(**base, repository_url=repo, backend_stack=fields["Серверная часть"].get().strip())
                previous_state = self._portfolio_snapshot()
                if old:
                    new.project_id = old.project_id
                    new.sort_order = old.sort_order or old.project_id
                    self.portfolio.projects[self.portfolio.projects.index(old)] = new
                else:
                    self.portfolio.add(new)
                if not self._persist_portfolio_change(previous_state):
                    return
                win.destroy()
                self.refresh()
                if str(new.project_id) in self.tree.get_children():
                    self.tree.selection_set(str(new.project_id))
                    self.tree.focus(str(new.project_id))
                    self.show_details()
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Проверьте данные", str(exc), parent=win)
        cancel_button = ttk.Button(actions, text="Отмена", command=win.destroy)
        cancel_button.pack(side="left")
        save_button = ttk.Button(actions, text="Сохранить", style="Primary.TButton", command=save_form)
        save_button.pack(side="right")

        def reveal_widget(widget):
            if not widget.winfo_exists() or not str(widget).startswith(str(frame)):
                return
            anchor_placement = grid_anchor_in(frame, widget)
            if anchor_placement is None:
                return
            anchor, grid_info = anchor_placement
            frame.update_idletasks()
            canvas.update_idletasks()
            region = canvas.bbox("all")
            if not region:
                return
            viewport_top = canvas.canvasy(0)
            row = int(grid_info.get("row", 0))
            column = int(grid_info.get("column", 0))
            rowspan = int(grid_info.get("rowspan", 1))
            columnspan = int(grid_info.get("columnspan", 1))
            cell = frame.grid_bbox(column, row, column + columnspan - 1,
                                   row + rowspan - 1)
            # Tkinter grid_bbox returns (x, y, width, height), not bottom-right coordinates.
            widget_top = cell[1] + widget.winfo_rooty() - anchor.winfo_rooty()
            widget_height = widget.winfo_height()
            viewport_height = max(1, canvas.winfo_height())
            content_height = max(1, region[3] - region[1])
            fraction = canvas_focus_view_fraction(
                viewport_top, viewport_height, content_height, widget_top, widget_height
            )
            if fraction is not None:
                canvas.yview_moveto(fraction)
            canvas.update_idletasks()

        def reveal_focused_field(event):
            reveal_widget(event.widget)

        def scroll_form(event):
            if event.delta:
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

        def scroll_multiline(event, widget):
            target = desktop_text_wheel_target(event.delta, widget.yview())
            if target == "form":
                return scroll_form(event)
            if target == "text":
                widget.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll_form, add="+")

        def bind_form_events(widget):
            widget.bind("<FocusIn>", reveal_focused_field, add="+")
            if isinstance(widget, tk.Text):
                widget.bind("<MouseWheel>", lambda event, target=widget: scroll_multiline(event, target), add="+")
            else:
                widget.bind("<MouseWheel>", scroll_form, add="+")
            for child in widget.winfo_children():
                bind_form_events(child)

        bind_form_events(frame)

        def move_form_focus(event, backwards=False, current_widget=None):
            controls = [kind_widget]
            controls.extend(fields[label + "__widget"] for label in values)
            controls.extend((featured_widget, choose_cover_button, remove_cover_button,
                             gallery_button, cancel_button, save_button))
            controls = [widget for widget in controls
                        if widget.winfo_exists() and widget.winfo_ismapped()]
            source_widget = current_widget if current_widget is not None else event.widget
            current_path = str(source_widget)
            current_index = next(
                (
                    index
                    for index, widget in enumerate(controls)
                    if str(widget) == current_path or current_path.startswith(str(widget) + ".")
                ),
                None,
            )
            if current_index is None or not controls:
                return None
            offset = -1 if backwards else 1
            target = controls[(current_index + offset) % len(controls)]
            reveal_widget(target)
            target.focus_set()
            return "break"

        focusable_controls = [kind_widget, *(fields[label + "__widget"] for label in values),
                              featured_widget, choose_cover_button, remove_cover_button,
                              gallery_button, cancel_button, save_button]
        for widget in focusable_controls:
            if isinstance(widget, tk.Text):
                # Match the physical key event before Text's class binding. Tk's
                # Text class otherwise inserts a tab character into the editor.
                widget.bind(
                    "<KeyPress>",
                    lambda event, current=widget: (
                        move_form_focus(
                            event,
                            backwards=bool(event.state & 0x0001),
                            current_widget=current,
                        ) if event.keysym == "Tab" else None
                    ),
                    add="+",
                )
                continue
            widget.bind("<Tab>",
                        lambda event, current=widget: move_form_focus(event, current_widget=current),
                        add="+")
            widget.bind("<Shift-Tab>",
                        lambda event, current=widget: move_form_focus(
                            event, backwards=True, current_widget=current),
                        add="+")
        # Keep a dialog-level fallback after Tk's class binding. Some themed
        # controls do not expose their instance event widget consistently from
        # injected keyboard input, while the toplevel binding still sees it.
        win.bind("<Tab>", move_form_focus, add="+")
        win.bind("<Shift-Tab>", lambda event: move_form_focus(event, backwards=True), add="+")

        win.after_idle(fields["Название *__widget"].focus_set)
        win.bind("<Escape>", lambda _event: win.destroy())
        win.bind("<Control-Return>", lambda _event: save_form())
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    def delete(self):
        p = self.selected()
        if p and messagebox.askyesno("Подтверждение", f"Удалить «{p.title}»?", parent=self.root):
            previous_state = self._portfolio_snapshot()
            self.portfolio.delete(p.project_id)
            if not self._persist_portfolio_change(previous_state):
                return
            self.refresh()
            self._set_details("Проект удалён.")

    def duplicate_selected(self):
        source = self.selected()
        if not source:
            return
        previous_state = self._portfolio_snapshot()
        duplicate = self.portfolio.duplicate(source.project_id)
        if duplicate is None:
            return
        if not self._persist_portfolio_change(previous_state):
            return
        self.refresh()
        if str(duplicate.project_id) in self.tree.get_children():
            self.tree.selection_set(str(duplicate.project_id))
            self.tree.focus(str(duplicate.project_id))
            self.show_details()
        self._set_details(f"Создана копия «{duplicate.title}». Проверьте её и добавьте свои ссылки.")

    def sort_by(self, column):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column, self.sort_ascending = column, True
        self._sort_visible()
        for key, title in zip(self.tree["columns"], self.COLUMNS):
            suffix = (" ↑" if self.sort_ascending else " ↓") if key == column else ""
            self.tree.heading(key, text=title + suffix)
        selected = self.selected(False)
        self._render_visible(selected.project_id if selected else None)

    def move_selected(self, direction):
        project = self.selected()
        if not project:
            return
        previous_state = self._portfolio_snapshot()
        previous_sort = self.sort_column, self.sort_ascending
        if not self.portfolio.move(project.project_id, direction):
            return
        self.sort_column, self.sort_ascending = "featured", True
        if not self._persist_portfolio_change(previous_state):
            self.sort_column, self.sort_ascending = previous_sort
            self.refresh()
            return
        self.refresh()
        if str(project.project_id) in self.tree.get_children():
            self.tree.selection_set(str(project.project_id))
            self.tree.focus(str(project.project_id))

    def open_link(self):
        p = self.selected()
        if p:
            link = p.get_main_link()
            if link and is_placeholder_url(link):
                messagebox.showinfo("Учебная ссылка", "Это адрес-заглушка из демонстрационных данных. Укажите реальный адрес проекта при редактировании.", parent=self.root)
            elif link:
                webbrowser.open(link)
            else:
                messagebox.showinfo("Ссылка отсутствует", "У проекта не задана основная ссылка.", parent=self.root)

    def record(self, p):
        data = {"id": p.project_id, "type": p.project_type, "title": p.title, "description": p.description,
                "created_at": p.created_at, "status": p.status, "technologies": [asdict(t) for t in p.technologies],
                "demo_url": p.demo_url, "role": p.role, "outcome": p.outcome, "tags": p.tags,
                "sort_order": p.sort_order or p.project_id, "featured": p.featured,
                "context": p.context, "solution": p.solution, "process": p.process, "metrics": p.metrics,
                "cover_image": p.cover_image, "cover_image_data": p.cover_image_data,
                "cover_position": normalize_cover_position(p.cover_position),
                "gallery_images": p.gallery_images}
        if p.cover_position_mobile is not None:
            data["cover_position_mobile"] = normalize_cover_position(p.cover_position_mobile)
        if isinstance(p, LandingProject):
            data["page_count"] = p.page_count
        if isinstance(p, WebAppProject):
            data.update(repository_url=p.repository_url, backend_stack=p.backend_stack)
        return data

    def save(self, silent=False):
        if not self.data_path:
            return self.save_as()
        try:
            data = {"schema_version": DATA_SCHEMA_VERSION, "title": self.portfolio.title,
                    "next_id": self.portfolio.next_id, "developer": asdict(self.developer),
                    "projects": [self.record(p) for p in self.portfolio.projects]}
            if self.data_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                validate_portable_transfer_payload(data)
                SQLiteStore(self.data_path).save(data)
            else:
                payload = serialize_portable_json(data)
                temporary = self.data_path.with_suffix(self.data_path.suffix + ".tmp")
                temporary.write_text(payload, encoding="utf-8")
                temporary.replace(self.data_path)
            if not silent:
                messagebox.showinfo("Сохранено", f"Файл сохранён:\n{self.data_path}", parent=self.root)
            self.refresh()
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)
            return False

    def _read_data(self, path, set_active_store=True, apply=True):
        path = Path(path)
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            data = SQLiteStore(path).load()
        else:
            if path.stat().st_size > PORTFOLIO_IMPORT_MAX_BYTES:
                raise ValueError("Резервная копия больше 64 МиБ. Выберите файл меньшего размера.")
            with path.open("rb") as source:
                payload = source.read(PORTFOLIO_IMPORT_MAX_BYTES + 1)
            if len(payload) > PORTFOLIO_IMPORT_MAX_BYTES:
                raise ValueError("Резервная копия больше 64 МиБ. Выберите файл меньшего размера.")
            try:
                data = json.loads(payload.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise ValueError("Файл должен быть JSON в кодировке UTF-8.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
            raise ValueError("Ожидается JSON-объект со списком projects.")
        if len(data["projects"]) > PORTFOLIO_IMPORT_MAX_PROJECTS:
            raise ValueError(f"В резервной копии может быть не больше {PORTFOLIO_IMPORT_MAX_PROJECTS} проектов.")
        version = data.get("schema_version", 1)
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError("В резервной копии указана некорректная версия формата.")
        if version > DATA_SCHEMA_VERSION or version < 1:
            raise ValueError(f"Версия данных {version} не поддерживается.")
        declared_next_id = data.get("next_id", 1)
        if (isinstance(declared_next_id, bool) or not isinstance(declared_next_id, int)
                or not 1 <= declared_next_id <= PORTFOLIO_MAX_SAFE_INTEGER):
            raise ValueError("В резервной копии указан некорректный следующий ID проекта.")
        portfolio_title = data.get("title", "Портфолио веб-разработчика")
        if not isinstance(portfolio_title, str):
            raise ValueError("Название портфолио должно быть текстом.")
        portfolio_title = normalize_case_text(portfolio_title, "Название портфолио", 120) or "Портфолио веб-разработчика"
        raw_developer = data.get("developer", {})
        if not isinstance(raw_developer, dict):
            raise ValueError("Поле developer должно быть объектом.")
        developer = Developer(**normalize_developer_data(raw_developer))
        items, ids = [], set()
        imported_image_count = imported_image_data_chars = imported_image_pixels = 0
        for index, row in enumerate(data["projects"], start=1):
            if not isinstance(row, dict):
                raise ValueError(f"Запись проекта №{index} должна быть объектом.")
            title_value, description_value = row.get("title", ""), row.get("description", "")
            if not isinstance(title_value, str) or not isinstance(description_value, str):
                raise ValueError(f"Название и описание проекта №{index} должны быть текстом.")
            title = normalize_case_text(title_value, "Название проекта", 90)
            description = normalize_case_text(description_value, "Короткое описание", 500)
            if not title or not description:
                raise ValueError(f"У проекта №{index} не заполнено название или описание.")
            project_date = row.get("created_at", "")
            if not isinstance(project_date, str):
                raise ValueError(f"Дата проекта «{title}» должна быть текстом.")
            if date.fromisoformat(project_date).isoformat() != project_date:
                raise ValueError(f"У проекта «{title}» дата должна иметь формат ГГГГ-ММ-ДД.")
            status = row.get("status", "Завершён")
            if status not in self.STATUSES:
                raise ValueError(f"У проекта «{title}» неизвестный статус: {status}.")
            cover_image = str(row.get("cover_image", ""))
            cover_image_data = str(row.get("cover_image_data", ""))
            cover_position = normalize_cover_position(row.get("cover_position", "50% 46%"))
            raw_mobile_position = row.get("cover_position_mobile")
            cover_position_mobile = (
                normalize_cover_position(raw_mobile_position) if raw_mobile_position is not None else None
            )
            if not is_valid_cover_image(cover_image) or not is_valid_cover_image(cover_image_data, data_url=True):
                raise ValueError(f"У проекта «{title}» обложка должна быть корректным локальным PNG, JPEG или WebP до 2 МиБ и 24 Мп.")
            project_id = row.get("id", row.get("project_id", index))
            if (isinstance(project_id, bool) or not isinstance(project_id, int)
                    or not 1 <= project_id <= PORTFOLIO_MAX_SAFE_INTEGER or project_id in ids):
                raise ValueError(f"У проекта «{title}» некорректный или повторяющийся ID.")
            ids.add(project_id)
            sort_order = row.get("sort_order", project_id)
            if (isinstance(sort_order, bool) or not isinstance(sort_order, int)
                    or not 1 <= sort_order <= PORTFOLIO_MAX_SAFE_INTEGER):
                raise ValueError(f"Порядок проекта «{title}» должен быть положительным целым числом.")
            featured = row.get("featured", False)
            if not isinstance(featured, bool):
                raise ValueError(f"Поле featured проекта «{title}» должно быть логическим значением.")
            gallery_images = normalize_gallery_images(row.get("gallery_images", []))
            images = ([cover_image_data] if cover_image_data else []) + [item["image_data"] for item in gallery_images]
            imported_image_count += len(images)
            imported_image_data_chars += sum(len(image) for image in images)
            if imported_image_count > PORTFOLIO_IMPORT_MAX_IMAGES:
                raise ValueError(f"В резервной копии может быть не больше {PORTFOLIO_IMPORT_MAX_IMAGES} изображений.")
            if imported_image_data_chars > PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS:
                raise ValueError("Общий размер изображений в резервной копии превышает 24 млн символов (около 18 МиБ медиа).")
            for image_data in images:
                imported_image_pixels += embedded_image_pixel_count(image_data)
                if imported_image_pixels > PORTFOLIO_IMPORT_MAX_TOTAL_IMAGE_PIXELS:
                    raise ValueError("Суммарное разрешение изображений в резервной копии превышает 120 мегапикселей.")
            raw_tech = row.get("technologies", [])
            if not isinstance(raw_tech, list):
                raise ValueError(f"Список технологий проекта «{title}» задан неверно.")
            if len(raw_tech) > 40:
                raise ValueError(f"У проекта «{title}» может быть не больше 40 технологий.")
            technologies = []
            for tech_index, item in enumerate(raw_tech, start=1):
                if not isinstance(item, dict):
                    raise ValueError(f"Технология №{tech_index} проекта «{title}» должна быть объектом.")
                name = normalize_case_text(item.get("name"), f"Название технологии №{tech_index}", 60)
                if not name:
                    raise ValueError(f"У проекта «{title}» есть технология без названия.")
                category = normalize_case_text(item.get("category", "Инструмент"),
                                               f"Категория технологии №{tech_index}", 60) or "Инструмент"
                version = normalize_case_text(item.get("version", ""),
                                              f"Версия технологии №{tech_index}", 40)
                technologies.append(Technology(name=name, category=category, version=version))
            common = dict(title=title, description=description, created_at=project_date, status=status,
                          technologies=technologies, demo_url=str(row.get("demo_url", "")),
                          project_id=project_id, role=normalize_case_text(row.get("role", ""), "Ваша роль", 120),
                          outcome=normalize_case_text(row.get("outcome", ""), "Результат", 500), tags=normalize_tags(row.get("tags", [])),
                          context=normalize_case_text(row.get("context"), "Контекст задачи", 500),
                          solution=normalize_case_text(row.get("solution"), "Решение", 700),
                          process=normalize_case_text(row.get("process"), "Этапы процесса", 1500),
                          metrics=normalize_case_text(row.get("metrics"), "Метрики результата", 300),
                          featured=featured, sort_order=sort_order,
                          cover_image=cover_image, cover_image_data=cover_image_data,
                          cover_position=cover_position,
                          cover_position_mobile=cover_position_mobile,
                          gallery_images=gallery_images)
            if row.get("type") == self.TYPES[0]:
                raw_page_count = row.get("page_count", 1)
                if isinstance(raw_page_count, bool) or not isinstance(raw_page_count, (int, float)) or (
                    isinstance(raw_page_count, float) and not raw_page_count.is_integer()
                ):
                    raise ValueError(f"Количество страниц у проекта «{title}» должно быть целым числом.")
                page_count = int(raw_page_count)
                if page_count < 1:
                    raise ValueError(f"Количество страниц у проекта «{title}» должно быть больше нуля.")
                project = LandingProject(**common, page_count=page_count)
            elif row.get("type") == self.TYPES[1]:
                project = WebAppProject(**common, repository_url=str(row.get("repository_url", "")),
                                         backend_stack=str(row.get("backend_stack", "")))
            else:
                raise ValueError(f"У проекта «{title}» неизвестный тип.")
            for label, url in (("Демо URL", project.demo_url),
                               ("Ссылка на репозиторий", getattr(project, "repository_url", ""))):
                parsed = urlparse(url)
                if url and (parsed.scheme.lower() not in ("http", "https") or not parsed.hostname
                            or parsed.username is not None or parsed.password is not None):
                    raise ValueError(f"{label} проекта «{title}» не является безопасной корректной ссылкой.")
            items.append(project)
        next_id = max(int(data.get("next_id", 1)), max(ids, default=0) + 1)
        portfolio = Portfolio(str(data.get("title", "Портфолио веб-разработчика")), items, next_id)
        if apply:
            self.portfolio, self.developer = portfolio, developer
            if set_active_store:
                self.data_path = path
            self.refresh()
            self._set_details("Данные загружены. Выберите проект для просмотра.")
        return portfolio, developer

    def save_as(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".sqlite3", filetypes=[("SQLite", "*.sqlite3"), ("JSON", "*.json")], initialfile="portfolio.sqlite3")
        if not path:
            return False
        previous_path = self.data_path
        self.data_path = Path(path)
        if not self.save():
            self.data_path = previous_path
            return False
        return True

    def _choose_import_strategy(self, candidate, file_name):
        current_by_id = {project.project_id: project for project in self.portfolio.projects}
        conflicts = [(project.project_id, current_by_id[project.project_id].title, project.title)
                     for project in candidate.projects if project.project_id in current_by_id]
        win = tk.Toplevel(self.root)
        win.title("Предварительный просмотр JSON")
        win.transient(self.root)
        win.resizable(True, True)
        (width, height), minimum = fit_window_dimensions(
            win.winfo_screenwidth(), win.winfo_screenheight(), (720, 540), (560, 430)
        )
        win.minsize(*minimum)
        x = max(0, (win.winfo_screenwidth() - width) // 2)
        y = max(0, (win.winfo_screenheight() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        result = {"strategy": None}
        ttk.Style(win).configure("Eyebrow.TLabel", foreground=DESKTOP_PALETTE["muted"], font=("Segoe UI", 9, "bold"))

        def choose(strategy):
            result["strategy"] = strategy
            win.destroy()

        body = ttk.Frame(win, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="ПРЕДПРОСМОТР ФАЙЛА", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(body, text="Перед импортом", font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(6, 2))
        ttk.Label(body, text=file_name, foreground=DESKTOP_PALETTE["muted"]).pack(anchor="w", pady=(0, 14))
        ttk.Label(body, text=(f"В файле: {len(candidate.projects)} {project_count_label(len(candidate.projects))}. "
                              f"Сейчас: {len(self.portfolio.projects)} {project_count_label(len(self.portfolio.projects))}. "
                              f"Новых: {len(candidate.projects) - len(conflicts)}. Совпадений ID: {len(conflicts)}."),
                  wraplength=660, justify="left").pack(anchor="w", fill="x", pady=(0, 16))
        if conflicts:
            table_frame = ttk.Frame(body)
            table_frame.pack(fill="both", expand=True)
            table = ttk.Treeview(table_frame, columns=("id", "current", "incoming"), show="headings", height=min(8, len(conflicts)))
            table.heading("id", text="ID")
            table.heading("current", text="В портфолио")
            table.heading("incoming", text="В JSON")
            table.column("id", width=55, stretch=False, anchor="center")
            table.column("current", width=240, minwidth=140)
            table.column("incoming", width=240, minwidth=140)
            scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
            table.configure(yscrollcommand=scrollbar.set)
            table.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            for project_id, current_title, incoming_title in conflicts:
                table.insert("", "end", values=(project_id, current_title, incoming_title))
        else:
            ttk.Label(body, text="Совпадающих ID нет. Записи можно объединить без замены.",
                      wraplength=650, justify="left").pack(anchor="w", fill="x", pady=(0, 14))
        ttk.Label(body, text="Полная замена сначала попросит выбрать место для JSON-резервной копии.",
                  foreground=DESKTOP_PALETTE["muted"], wraplength=650, justify="left").pack(anchor="w", pady=(14, 12))
        actions = ttk.Frame(body)
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Отмена", command=lambda: choose(None)).pack(side="left")
        if conflicts:
            ttk.Button(actions, text="Добавить совпадения копиями", command=lambda: choose("copy")).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Объединить, оставить мои", style="Primary.TButton",
                   command=lambda: choose("keep-current")).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Заменить всё…", style="Danger.TButton",
                   command=lambda: choose("replace")).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", lambda: choose(None))
        win.bind("<Escape>", lambda _event: choose(None))
        win.grab_set()
        win.focus_set()
        self.root.wait_window(win)
        return result["strategy"]

    def _backup_before_import_replace(self, source_path):
        initial_dir = self.data_path.parent if self.data_path else Path(source_path).parent
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                            filetypes=[("JSON", "*.json")], initialdir=str(initial_dir),
                                            initialfile="folio-before-import.json",
                                            title="Сохраните текущую копию перед заменой")
        if not path:
            return False
        target = Path(path)
        protected = {Path(source_path).resolve()}
        if self.data_path:
            protected.add(Path(self.data_path).resolve())
        if target.resolve() in protected:
            messagebox.showerror("Небезопасный путь", "Резервную копию нельзя сохранить поверх исходного JSON или активной базы данных.", parent=self.root)
            return False
        data = {"schema_version": DATA_SCHEMA_VERSION, "title": self.portfolio.title,
                "next_id": self.portfolio.next_id, "developer": asdict(self.developer),
                "projects": [self.record(project) for project in self.portfolio.projects]}
        payload = serialize_portable_json(data)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(target)
        return True

    def load(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("База SQLite и JSON", "*.sqlite3 *.sqlite *.db *.json"), ("SQLite", "*.sqlite3 *.sqlite *.db"), ("JSON", "*.json")])
        if not path:
            return
        try:
            source_path = Path(path)
            if source_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                self._read_data(source_path, set_active_store=True)
                messagebox.showinfo("База данных", "Выбранная база данных открыта.", parent=self.root)
                return
            candidate, incoming_developer = self._read_data(source_path, set_active_store=False, apply=False)
            strategy = self._choose_import_strategy(candidate, source_path.name)
            if strategy is None:
                return
            if strategy == "replace":
                if not self._backup_before_import_replace(source_path):
                    return
                next_portfolio, next_developer = candidate, incoming_developer
                summary = (f"Полная замена: импортировано {len(candidate.projects)} "
                           f"{project_count_label(len(candidate.projects))}.")
            else:
                next_portfolio, stats = merge_portfolio_import(self.portfolio, candidate, strategy)
                next_developer = self.developer
                summary = (f"Объединение завершено: добавлено {stats['added']}, копий {stats['copied']}, "
                           f"оставлено локальных совпадений {stats['skipped']}.")
            previous_portfolio, previous_developer = self.portfolio, self.developer
            self.portfolio, self.developer = next_portfolio, next_developer
            if not self.save(silent=True):
                self.portfolio, self.developer = previous_portfolio, previous_developer
                self.refresh()
                return
            messagebox.showinfo("Импорт данных", summary, parent=self.root)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Ошибка загрузки", f"Не удалось открыть файл:\n{exc}", parent=self.root)

    def _write_json_export(self, path):
        target = Path(path)
        if self.data_path and target.resolve() == Path(self.data_path).resolve():
            raise ValueError("Нельзя экспортировать JSON поверх активного файла данных. Выберите другой путь.")
        data = {"schema_version": DATA_SCHEMA_VERSION, "title": self.portfolio.title,
                "next_id": self.portfolio.next_id, "developer": asdict(self.developer),
                "projects": [self.record(p) for p in self.portfolio.projects]}
        payload = serialize_portable_json(data)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=target.parent,
                                             prefix=f".{target.name}.", suffix=".tmp", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(payload)
            os.replace(temporary_path, target)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def export_json(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="portfolio-export.json")
        if not path:
            return
        try:
            self._write_json_export(path)
            messagebox.showinfo("Экспорт JSON", f"Файл создан:\n{path}", parent=self.root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="projects.csv")
        if not path:
            return
        fields = ["id", "sort_order", "type", "title", "description", "context", "role", "solution", "process", "outcome", "metrics", "tags", "featured",
                  "created_at", "status", "technologies", "demo_url", "page_count", "repository_url", "backend_stack"]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
                writer.writeheader()
                for p in self.portfolio.projects:
                    r = self.record(p)
                    r["technologies"] = ", ".join(t["name"] for t in r["technologies"])
                    r["tags"] = ", ".join(r["tags"])
                    r["featured"] = "Да" if r["featured"] else ""
                    writer.writerow({key: r.get(key, "") for key in fields})
            messagebox.showinfo("Экспорт", f"CSV создан:\n{path}", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def export_markdown(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".md",
            filetypes=[("Markdown", "*.md")], initialfile="portfolio.md")
        if not path:
            return
        try:
            Path(path).write_text(render_portfolio_markdown(self.portfolio, self.developer), encoding="utf-8")
            messagebox.showinfo("Экспорт", f"Markdown-файл создан:\n{path}", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def edit_developer_profile(self):
        win = tk.Toplevel(self.root)
        win.title("Профиль автора")
        win.transient(self.root)
        screen_width, screen_height = win.winfo_screenwidth(), win.winfo_screenheight()
        (width, height), minimum = fit_window_dimensions(
            screen_width, screen_height, (560, 650), (480, 440)
        )
        x = max(0, (win.winfo_screenwidth() - width) // 2)
        y = max(0, (win.winfo_screenheight() - height) // 2)
        win.resizable(True, True)
        win.minsize(*minimum)
        win.geometry(f"{width}x{height}+{x}+{y}")

        actions = ttk.Frame(win, padding=(24, 10))
        actions.pack(fill="x", side="bottom")
        viewport = ttk.Frame(win)
        viewport.pack(fill="both", expand=True)
        canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0,
                           background=DESKTOP_PALETTE["background"])
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        body = ttk.Frame(canvas, padding=24)
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(body_window, width=event.width))
        ttk.Label(body, text="ПРОФИЛЬ АВТОРА", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(body, text="Как представить вас в портфолио?",
                  font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(7, 6))
        ttk.Label(body, text="Контакты остаются локальными. Включённые контакты появятся в Markdown-экспорте.",
                  wraplength=505, justify="left", style="Muted.TLabel").pack(anchor="w", pady=(0, 16))

        form = ttk.Frame(body)
        form.pack(fill="both", expand=True)
        values = {}
        for key, label, value in (
            ("full_name", "Имя", self.developer.full_name),
            ("specialization", "Специализация", self.developer.specialization),
            ("email", "Email", self.developer.email),
            ("website_url", "Личный сайт", self.developer.website_url),
            ("github_url", "GitHub", self.developer.github_url),
        ):
            ttk.Label(form, text=label).pack(anchor="w", pady=(5, 3))
            entry = ttk.Entry(form)
            entry.insert(0, value)
            entry.pack(fill="x", ipady=4)
            values[key] = entry

        ttk.Label(form, text="Короткое вступление", style="TLabel").pack(anchor="w", pady=(9, 3))
        introduction = tk.Text(form, height=4, wrap="word", font=("Segoe UI", 10),
                               relief="solid", borderwidth=1, padx=8, pady=7, undo=True)
        introduction.insert("1.0", self.developer.introduction)
        introduction.pack(fill="x")
        values["introduction"] = introduction

        share_flags = {}
        for key, label in (
            ("include_email", "Показывать email в экспорте"),
            ("include_website", "Показывать личный сайт в экспорте"),
            ("include_github", "Показывать GitHub в экспорте"),
        ):
            flag = tk.BooleanVar(value=getattr(self.developer, key))
            ttk.Checkbutton(form, text=label, variable=flag).pack(anchor="w", pady=(5, 0))
            share_flags[key] = flag

        def save_profile():
            raw = {key: widget.get().strip() for key, widget in values.items() if key != "introduction"}
            raw["introduction"] = values["introduction"].get("1.0", "end-1c")
            raw.update({key: flag.get() for key, flag in share_flags.items()})
            try:
                next_profile = Developer(**normalize_developer_data(raw))
            except ValueError as exc:
                messagebox.showerror("Проверьте профиль", str(exc), parent=win)
                return
            previous = self.developer
            self.developer = next_profile
            if not self.save(silent=True):
                self.developer = previous
                self.refresh()
                return
            win.destroy()
            messagebox.showinfo("Профиль сохранён", "Настройки профиля сохранены локально.", parent=self.root)

        ttk.Button(actions, text="Отмена", command=win.destroy).pack(side="left")
        ttk.Button(actions, text="Сохранить профиль", style="Primary.TButton",
                   command=save_profile).pack(side="right")

        def reveal_focused_field(event):
            widget = event.widget
            if not str(widget).startswith(str(body)):
                return
            canvas.update_idletasks()
            region = canvas.bbox("all")
            if not region:
                return
            viewport_top = canvas.canvasy(0)
            widget_top = widget.winfo_rooty() - canvas.winfo_rooty() + viewport_top
            widget_bottom = widget_top + widget.winfo_height()
            viewport_height = max(1, canvas.winfo_height())
            content_height = max(1, region[3] - region[1])
            if widget_top < viewport_top:
                canvas.yview_moveto(max(0, widget_top / content_height))
            elif widget_bottom > viewport_top + viewport_height:
                canvas.yview_moveto(max(0, (widget_bottom - viewport_height) / content_height))

        def scroll_profile(event):
            if event.delta:
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll_profile, add="+")
        def bind_profile_events(widget):
            widget.bind("<FocusIn>", reveal_focused_field, add="+")
            widget.bind("<MouseWheel>", scroll_profile, add="+")
            for child in widget.winfo_children():
                bind_profile_events(child)
        bind_profile_events(body)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.bind("<Escape>", lambda _event: win.destroy())
        win.bind("<Control-Return>", lambda _event: save_profile())
        win.after_idle(values["full_name"].focus_set)

    def about(self):
        win = tk.Toplevel(self.root)
        win.title("О программе")
        win.transient(self.root)
        canvas = tk.Canvas(win, width=160, height=105, bg="#0f172a", highlightthickness=0)
        canvas.pack(padx=20, pady=15)
        canvas.create_oval(48, 12, 112, 76, fill="#38bdf8", outline="")
        canvas.create_text(80, 44, text="</>", fill="#0f172a", font=("Consolas", 21, "bold"))
        ttk.Label(win, text="Портфолио веб-разработчика", font=("Segoe UI", 13, "bold")).pack()
        ttk.Label(win, text="Учебный проект по ООП · модули 4–5\nPython · Tkinter · SQLite · JSON / CSV", justify="center").pack(padx=20, pady=10)
        ttk.Button(win, text="Вернуться к программе", command=win.destroy).pack(pady=(0, 16))


def main():
    root = tk.Tk()
    PortfolioApp(root)
    try:
        root.state("zoomed")
    except tk.TclError:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()

