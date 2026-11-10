"""Transactional SQLite storage for the portfolio application's JSON payload.

The public API intentionally mirrors the application's file store:

    store.save(payload)
    payload = store.load()

Project records are kept both as searchable columns and as their complete JSON
object, so fields added by later app versions survive a SQLite round-trip.
Pillow is used to verify embedded images; image-bearing payloads fail closed if it is unavailable.
"""

from __future__ import annotations

import base64
from datetime import date
import io
import json
import re
import sqlite3
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:  # Text-only portfolios remain usable without the optional image dependency.
    Image = None


SCHEMA_VERSION = 1
_GALLERY_MAX_IMAGES = 10
_GALLERY_MAX_TOTAL_DATA_CHARS = 8_000_000
_GALLERY_MAX_IMAGE_DATA_CHARS = 1_600_000
_PORTFOLIO_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_PORTFOLIO_MAX_PROJECTS = 130_000
_PORTFOLIO_MAX_IMAGES = 250
_PORTFOLIO_MAX_IMAGE_DATA_CHARS = 24_000_000
_PORTFOLIO_MAX_IMAGE_PIXELS = 24_000_000
_PORTFOLIO_MAX_TOTAL_IMAGE_PIXELS = 120_000_000
_PORTFOLIO_MAX_JSON_BYTES = 64 * 1024 * 1024
_COVER_MAX_DATA_CHARS = 2_800_000
_COVER_MAX_BYTES = 2 * 1024 * 1024
_GALLERY_MAX_IMAGE_BYTES = 1_200_000
_IMAGE_DATA_PATTERN = re.compile(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})")
_APPLICATION_ID = 0x50525446  # ASCII "PRTF"
_TABLE_COLUMNS = {
    "metadata": ("key", "value_json"),
    "projects": (
        "project_id", "project_type", "title", "description", "status",
        "created_at", "search_text", "payload_json",
    ),
}
_METADATA_KEYS = {"title", "next_id", "developer"}
_PROJECT_REQUIRED = {"id", "type", "title", "description", "created_at", "status", "technologies"}


class SQLiteStoreError(ValueError):
    """Raised when the SQLite file or its stored payload is invalid."""


class SQLiteStore:
    """Read and write the portfolio payload using a versioned SQLite file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, data: dict[str, Any]) -> None:
        """Validate and atomically replace the stored portfolio contents."""
        normalized = _validate_payload(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path, timeout=10.0)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            _prepare_schema(connection)
            connection.execute("DELETE FROM projects")
            connection.execute("DELETE FROM metadata")
            for key in ("title", "next_id", "developer"):
                connection.execute(
                    "INSERT INTO metadata(key, value_json) VALUES (?, ?)",
                    (key, _json_dump(normalized[key])),
                )
            for project in normalized["projects"]:
                connection.execute(
                    """INSERT INTO projects
                       (project_id, project_type, title, description, status,
                        created_at, search_text, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        project["id"], project["type"], project["title"],
                        project["description"], project["status"],
                        project["created_at"], _search_text(project),
                        _json_dump(project),
                    ),
                )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
            connection.commit()
        except SQLiteStoreError:
            if connection is not None:
                connection.rollback()
            raise
        except sqlite3.DatabaseError as exc:
            if connection is not None:
                connection.rollback()
            raise SQLiteStoreError(f"Не удалось сохранить SQLite-базу: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    def load(self) -> dict[str, Any]:
        """Load and validate the portfolio payload from an existing database."""
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        uri = self.path.resolve().as_uri() + "?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=10.0)
            try:
                connection.row_factory = sqlite3.Row
                _validate_database(connection)
                metadata_rows = connection.execute(
                    "SELECT key, value_json FROM metadata ORDER BY key"
                ).fetchall()
                metadata: dict[str, Any] = {}
                for row in metadata_rows:
                    key = row["key"]
                    if key in metadata:
                        raise SQLiteStoreError(f"Повторяется ключ метаданных: {key!r}.")
                    try:
                        metadata[key] = json.loads(row["value_json"])
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise SQLiteStoreError(f"Повреждены метаданные {key!r}.") from exc

                if set(metadata) != _METADATA_KEYS:
                    raise SQLiteStoreError("Набор ключей metadata не соответствует схеме.")

                projects: list[dict[str, Any]] = []
                rows = connection.execute(
                    """SELECT project_id, project_type, title, description, status,
                              created_at, search_text, payload_json
                       FROM projects ORDER BY project_id"""
                ).fetchall()
                for row_number, row in enumerate(rows, start=1):
                    try:
                        project = json.loads(row["payload_json"])
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise SQLiteStoreError(
                            f"Повреждён JSON проекта в строке {row_number}."
                        ) from exc
                    _validate_project(project, row_number)
                    expected_columns = (
                        project["id"], project["type"], project["title"],
                        project["description"], project["status"],
                        project["created_at"], _search_text(project),
                    )
                    actual_columns = tuple(row[key] for key in (
                        "project_id", "project_type", "title", "description",
                        "status", "created_at", "search_text",
                    ))
                    if actual_columns != expected_columns:
                        raise SQLiteStoreError(
                            f"Столбцы и JSON проекта в строке {row_number} расходятся."
                        )
                    projects.append(project)

                payload = {
                    "schema_version": SCHEMA_VERSION,
                    "title": metadata["title"],
                    "next_id": metadata["next_id"],
                    "developer": metadata["developer"],
                    "projects": projects,
                }
                return _validate_payload(payload)
            finally:
                connection.close()
        except SQLiteStoreError:
            raise
        except sqlite3.DatabaseError as exc:
            raise SQLiteStoreError(f"SQLite-база повреждена или не читается: {exc}") from exc


def _prepare_schema(connection: sqlite3.Connection) -> None:
    """Create a fresh schema or reject a database owned by another format."""
    user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if not tables and user_version == 0 and application_id == 0:
        connection.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)"
        )
        connection.execute(
            """CREATE TABLE projects (
                project_id INTEGER PRIMARY KEY,
                project_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                search_text TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )"""
        )
        connection.execute("CREATE INDEX idx_projects_title ON projects(title COLLATE NOCASE)")
        connection.execute("CREATE INDEX idx_projects_status ON projects(status)")
        return
    if user_version != SCHEMA_VERSION or application_id != _APPLICATION_ID:
        raise SQLiteStoreError(
            "Файл уже содержит базу другого формата или неподдерживаемую версию SQLite-схемы."
        )
    _validate_database(connection)


def _validate_database(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        raise SQLiteStoreError(
            f"Версия SQLite-схемы {version} не поддерживается (ожидается {SCHEMA_VERSION})."
        )
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    if application_id != _APPLICATION_ID:
        raise SQLiteStoreError("SQLite-файл не распознан как база портфолио.")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SQLiteStoreError(f"Проверка целостности SQLite не пройдена: {integrity}.")
    tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if tables != set(_TABLE_COLUMNS):
        raise SQLiteStoreError("Набор таблиц SQLite не соответствует схеме портфолио.")
    for table, expected in _TABLE_COLUMNS.items():
        actual = tuple(
            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
        )
        if actual != expected:
            raise SQLiteStoreError(f"Структура таблицы {table!r} не соответствует схеме.")


def _validate_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SQLiteStoreError("Данные портфолио должны быть JSON-объектом.")
    if any(not isinstance(key, str) for key in data):
        raise SQLiteStoreError("Ключи payload должны быть строками.")
    required = {"title", "next_id", "developer", "projects"}
    if not required.issubset(data):
        missing = ", ".join(sorted(required - set(data)))
        raise SQLiteStoreError(f"В данных портфолио отсутствуют поля: {missing}.")
    title = data["title"]
    next_id = data["next_id"]
    developer = data["developer"]
    projects = data["projects"]
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
        raise SQLiteStoreError("title должен содержать от 1 до 120 символов.")
    if (isinstance(next_id, bool) or not isinstance(next_id, int)
            or not 1 <= next_id <= _PORTFOLIO_MAX_SAFE_INTEGER):
        raise SQLiteStoreError("next_id должен быть положительным целым числом.")
    if not isinstance(developer, dict):
        raise SQLiteStoreError("developer должен быть объектом.")
    _validate_developer(developer)
    if not isinstance(projects, list) or len(projects) > _PORTFOLIO_MAX_PROJECTS:
        raise SQLiteStoreError("projects должен быть списком.")
    seen: set[int] = set()
    image_count = image_data_chars = total_image_pixels = 0
    for row_number, project in enumerate(projects, start=1):
        _validate_project(project, row_number)
        project_id = project["id"]
        if project_id in seen:
            raise SQLiteStoreError(f"ID проекта {project_id} повторяется.")
        seen.add(project_id)
        embedded = []
        cover_data = project.get("cover_image_data", "")
        if cover_data:
            embedded.append((cover_data, _COVER_MAX_DATA_CHARS, _COVER_MAX_BYTES,
                             f"Обложка проекта №{row_number}"))
        for image_number, image in enumerate(project.get("gallery_images", []), start=1):
            embedded.append((image["image_data"], _GALLERY_MAX_IMAGE_DATA_CHARS,
                             _GALLERY_MAX_IMAGE_BYTES,
                             f"Изображение №{image_number} проекта №{row_number}"))
        image_count += len(embedded)
        if image_count > _PORTFOLIO_MAX_IMAGES:
            raise SQLiteStoreError(f"В портфолио может быть не больше {_PORTFOLIO_MAX_IMAGES} изображений.")
        for data_url, char_limit, byte_limit, label in embedded:
            image_data_chars += len(data_url)
            if image_data_chars > _PORTFOLIO_MAX_IMAGE_DATA_CHARS:
                raise SQLiteStoreError("Общий объём изображений в портфолио превышает лимит 24 млн символов.")
            pixels = _embedded_image_pixel_count(data_url, char_limit, byte_limit, label)
            total_image_pixels += pixels
            if total_image_pixels > _PORTFOLIO_MAX_TOTAL_IMAGE_PIXELS:
                raise SQLiteStoreError("Суммарное разрешение изображений в портфолио превышает 120 мегапикселей.")
    if next_id <= max(seen, default=0):
        raise SQLiteStoreError("next_id должен быть больше ID всех проектов.")
    version = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise SQLiteStoreError(f"Версия payload не поддерживается: {version!r}.")
    # Deep-copy through JSON so callers cannot smuggle unserializable Python values
    # into the database, and so returned data is the same plain structure as JSON.
    try:
        normalized = json.loads(_json_dump(data))
    except (TypeError, ValueError) as exc:
        raise SQLiteStoreError(f"Payload не является корректным JSON: {exc}") from exc
    normalized["schema_version"] = SCHEMA_VERSION
    if len(json.dumps(normalized, ensure_ascii=False, indent=2).encode("utf-8")) > _PORTFOLIO_MAX_JSON_BYTES:
        raise SQLiteStoreError("Портфолио превышает общий лимит JSON-резервной копии 64 МиБ.")
    return normalized


def _validate_developer(developer: dict[str, Any]) -> None:
    allowed = {"full_name", "specialization", "introduction", "email", "website_url", "github_url",
               "include_email", "include_website", "include_github"}
    if set(developer) - allowed:
        raise SQLiteStoreError("developer содержит неизвестные поля.")
    limits = {"full_name": 90, "specialization": 90, "introduction": 800,
              "email": 254, "website_url": 300, "github_url": 300}
    for key, value in developer.items():
        if key in limits:
            if not isinstance(value, str):
                raise SQLiteStoreError(f"developer.{key} должен быть текстом.")
            if len(value.strip()) > limits[key]:
                raise SQLiteStoreError(f"developer.{key} превышает {limits[key]} символов.")
            if any((ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in value):
                raise SQLiteStoreError(f"developer.{key} содержит управляющие символы.")
        elif not isinstance(value, bool):
            raise SQLiteStoreError(f"developer.{key} должен быть логическим значением.")
    email = developer.get("email", "").strip()
    if email and not re.fullmatch(r"[^\s@<>]+@[^\s@<>.]+(?:\.[^\s@<>.]+)+", email):
        raise SQLiteStoreError("developer.email имеет неверный формат.")
    for key in ("website_url", "github_url"):
        value = developer.get(key, "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise SQLiteStoreError(f"developer.{key} должен быть ссылкой HTTP или HTTPS без логина и пароля.")


def _validate_project(project: Any, row_number: int) -> None:
    if not isinstance(project, dict):
        raise SQLiteStoreError(f"Проект №{row_number} должен быть объектом.")
    if any(not isinstance(key, str) for key in project):
        raise SQLiteStoreError(f"Ключи проекта №{row_number} должны быть строками.")
    missing = _PROJECT_REQUIRED - set(project)
    if missing:
        raise SQLiteStoreError(
            f"В проекте №{row_number} отсутствуют поля: {', '.join(sorted(missing))}."
        )
    project_id = project["id"]
    if (isinstance(project_id, bool) or not isinstance(project_id, int)
            or not 1 <= project_id <= _PORTFOLIO_MAX_SAFE_INTEGER):
        raise SQLiteStoreError(f"ID проекта №{row_number} должен быть положительным целым числом.")
    sort_order = project.get("sort_order", project_id)
    if (isinstance(sort_order, bool) or not isinstance(sort_order, int)
            or not 1 <= sort_order <= _PORTFOLIO_MAX_SAFE_INTEGER):
        raise SQLiteStoreError(f"Порядок проекта №{row_number} должен быть положительным целым числом.")
    for field in ("type", "title", "description", "created_at", "status"):
        if not isinstance(project[field], str):
            raise SQLiteStoreError(f"Поле {field!r} проекта №{row_number} должно быть строкой.")
    created_at = project["created_at"]
    try:
        parsed_created_at = date.fromisoformat(created_at)
    except ValueError as exc:
        raise SQLiteStoreError(
            f"Дата проекта №{row_number} должна иметь формат ГГГГ-ММ-ДД."
        ) from exc
    if parsed_created_at.isoformat() != created_at:
        raise SQLiteStoreError(f"Дата проекта №{row_number} должна иметь формат ГГГГ-ММ-ДД.")
    if project["type"] not in {"Сайт / лендинг", "Веб-приложение"}:
        raise SQLiteStoreError(f"У проекта №{row_number} неизвестный тип.")
    if project["status"] not in {"В разработке", "Завершён", "Опубликован", "Архив"}:
        raise SQLiteStoreError(f"У проекта №{row_number} неизвестный статус.")
    limits = {"title": 90, "description": 500, "role": 120, "outcome": 500}
    for field, limit in limits.items():
        value = project.get(field, "")
        if not isinstance(value, str) or len(value.strip()) > limit:
            raise SQLiteStoreError(f"Поле {field!r} проекта №{row_number} должно содержать не больше {limit} символов.")
    if "featured" in project and not isinstance(project["featured"], bool):
        raise SQLiteStoreError(f"Поле featured проекта №{row_number} должно быть логическим значением.")
    for field in ("demo_url", "repository_url"):
        value = project.get(field, "")
        if not isinstance(value, str):
            raise SQLiteStoreError(f"Поле {field!r} проекта №{row_number} должно быть строкой.")
        value = value.strip()
        if not value:
            continue
        try:
            parsed_url = urlparse(value)
            hostname = parsed_url.hostname
        except ValueError as exc:
            raise SQLiteStoreError(f"Ссылка {field!r} проекта №{row_number} некорректна.") from exc
        if (parsed_url.scheme.lower() not in {"http", "https"} or not hostname
                or parsed_url.username or parsed_url.password):
            raise SQLiteStoreError(
                f"Ссылка {field!r} проекта №{row_number} должна быть HTTP(S)-адресом без логина и пароля."
            )
    if project["type"] == "Сайт / лендинг":
        page_count = project.get("page_count", 1)
        if isinstance(page_count, bool) or not isinstance(page_count, (int, float)) or (
            isinstance(page_count, float) and not page_count.is_integer()
        ) or page_count < 1:
            raise SQLiteStoreError(
                f"Количество страниц проекта №{row_number} должно быть положительным целым числом."
            )
    for field, limit in (("context", 500), ("solution", 700), ("process", 1500), ("metrics", 300)):
        if field not in project:
            continue
        value = project[field]
        if not isinstance(value, str) or len(value) > limit or any(
            (ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in value
        ):
            raise SQLiteStoreError(f"Поле {field!r} проекта №{row_number} содержит некорректный текст.")
    tags = project.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 20:
        raise SQLiteStoreError(f"tags проекта №{row_number} должно быть списком до 20 элементов.")
    seen_tags = set()
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 32 or any(ord(char) < 32 or ord(char) == 127 for char in tag):
            raise SQLiteStoreError(f"Некорректный тег проекта №{row_number}.")
        normalized_tag = tag.strip().casefold()
        if normalized_tag in seen_tags:
            raise SQLiteStoreError(f"Теги проекта №{row_number} не должны повторяться.")
        seen_tags.add(normalized_tag)
    if not project["title"].strip() or not project["description"].strip():
        raise SQLiteStoreError(f"У проекта №{row_number} пустое название или описание.")
    if not isinstance(project["technologies"], list) or len(project["technologies"]) > 40:
        raise SQLiteStoreError(f"technologies проекта №{row_number} должно быть списком до 40 элементов.")
    for technology_number, technology in enumerate(project["technologies"], start=1):
        if not isinstance(technology, dict):
            raise SQLiteStoreError(
                f"Технология №{technology_number} проекта №{row_number} должна быть объектом."
            )
        for field, limit, default in (("name", 60, None), ("category", 60, "Инструмент"),
                                      ("version", 40, "")):
            value = technology.get(field, default)
            if not isinstance(value, str) or len(value.strip()) > limit or any(
                (ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in value
            ):
                raise SQLiteStoreError(
                    f"Поле {field!r} технологии №{technology_number} проекта №{row_number} "
                    f"должно содержать не больше {limit} символов и не содержать управляющих символов."
                )
        if not technology["name"].strip():
            raise SQLiteStoreError(
                f"У технологии №{technology_number} проекта №{row_number} пустое название."
            )
    cover = project.get("cover_image", "")
    cover_data = project.get("cover_image_data", "")
    if not isinstance(cover, str) or (cover and not re.fullmatch(
        r"\./assets/covers/[A-Za-z0-9-]+\.(?:png|webp|jpe?g)", cover, re.IGNORECASE
    )):
        raise SQLiteStoreError(f"Некорректный локальный путь к обложке проекта №{row_number}.")
    if not isinstance(cover_data, str) or (cover_data and (
        len(cover_data) > _COVER_MAX_DATA_CHARS or not re.fullmatch(
            r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}", cover_data
        )
    )):
        raise SQLiteStoreError(f"Обложка проекта №{row_number} должна быть PNG, JPEG или WebP до 2 МиБ.")
    cover_position = project.get("cover_position", "50% 46%")
    if not isinstance(cover_position, str) or not re.fullmatch(
        r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%", cover_position
    ):
        raise SQLiteStoreError(f"Точка кадрирования обложки проекта №{row_number} некорректна.")
    cover_position_mobile = project.get("cover_position_mobile")
    if cover_position_mobile is not None and (
        not isinstance(cover_position_mobile, str) or not re.fullmatch(
            r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%", cover_position_mobile
        )
    ):
        raise SQLiteStoreError(f"Точка кадрирования обложки для телефона в проекте №{row_number} некорректна.")
    gallery = project.get("gallery_images", [])
    if not isinstance(gallery, list) or len(gallery) > _GALLERY_MAX_IMAGES:
        raise SQLiteStoreError(f"Галерея проекта №{row_number} должна содержать до {_GALLERY_MAX_IMAGES} изображений.")
    if sum(len(image.get("image_data", "")) for image in gallery if isinstance(image, dict) and isinstance(image.get("image_data", ""), str)) > _GALLERY_MAX_TOTAL_DATA_CHARS:
        raise SQLiteStoreError(f"Общий размер галереи проекта №{row_number} превышает лимит 8 млн символов (около 6 МиБ медиа).")
    for image_number, image in enumerate(gallery, start=1):
        if not isinstance(image, dict):
            raise SQLiteStoreError(f"Изображение №{image_number} проекта №{row_number} должно быть объектом.")
        data, alt, position = image.get("image_data"), image.get("alt"), image.get("position", "50% 50%")
        if not isinstance(data, str) or len(data) > _GALLERY_MAX_IMAGE_DATA_CHARS or not re.fullmatch(
            r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}", data
        ):
            raise SQLiteStoreError(f"Изображение №{image_number} проекта №{row_number} должно быть PNG, JPEG или WebP до 1,2 МиБ.")
        if not isinstance(alt, str) or not alt.strip() or len(alt.strip()) > 180 or any(
            (ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in alt
        ):
            raise SQLiteStoreError(f"Описание изображения №{image_number} проекта №{row_number} некорректно.")
        if not isinstance(position, str) or not re.fullmatch(r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%", position):
            raise SQLiteStoreError(f"Точка кадрирования изображения №{image_number} проекта №{row_number} некорректна.")


def _embedded_image_pixel_count(data_url: str, max_chars: int, max_bytes: int, label: str) -> int:
    if Image is None:
        raise SQLiteStoreError("Для проверки встроенных изображений установите Pillow.")
    match = _IMAGE_DATA_PATTERN.fullmatch(data_url)
    if not match or len(data_url) > max_chars:
        raise SQLiteStoreError(f"{label}: формат или размер изображения недопустим.")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
        if len(raw) > max_bytes:
            raise SQLiteStoreError(f"{label}: размер файла превышает допустимый предел.")
        expected_format = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}[match.group(1)]
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                if probe.format != expected_format:
                    raise SQLiteStoreError(f"{label}: формат файла не совпадает с его data URL.")
                pixels = probe.width * probe.height
                if pixels < 1 or pixels > _PORTFOLIO_MAX_IMAGE_PIXELS:
                    raise SQLiteStoreError(f"{label}: разрешение превышает 24 мегапикселя.")
                probe.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
        return pixels
    except SQLiteStoreError:
        raise
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise SQLiteStoreError(f"{label}: изображение повреждено или не читается.") from exc


def _search_text(project: dict[str, Any]) -> str:
    values: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                values.append(str(key))
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
            values.append(str(value))
        elif isinstance(value, bool):
            values.append("true" if value else "false")

    collect(project)
    return " ".join(values).casefold()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
