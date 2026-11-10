from __future__ import annotations

import base64
from contextlib import closing
import io
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
import sqlite_storage as storage  # noqa: E402
from sqlite_storage import SQLiteStore, SQLiteStoreError  # noqa: E402


def sample_payload() -> dict:
    return {
        "schema_version": 1,
        "title": "Портфолио веб-разработчика",
        "next_id": 8,
        "developer": {"full_name": "Даниил Головин", "specialization": "Веб-разработчик"},
        "projects": [
            {
                "id": 2,
                "sort_order": 2,
                "type": "Веб-приложение",
                "title": "CRM для студии",
                "description": "Панель управления клиентами",
                "created_at": "2026-10-20",
                "status": "В разработке",
                "technologies": [
                    {"name": "Python", "category": "Инструмент", "version": "3.13"},
                    {"name": "SQLite", "category": "СУБД", "version": "3"},
                ],
                "demo_url": "https://example.com/demo",
                "role": "Разработчик",
                "outcome": "Сокращён ручной учёт клиентов",
                "context": "Небольшая команда ведёт заказы вручную.",
                "solution": "Единая CRM с клиентами и заказами.",
                "process": "Модель данных, формы и проверка сценариев.",
                "metrics": "Время обработки проверено на демонстрационном наборе.",
                "tags": ["Учёт", "CRM"],
                "featured": True,
                "cover_image": "./assets/covers/portfolio-studio.png",
                "cover_image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==",
                "repository_url": "https://github.com/example/crm",
                "backend_stack": "Flask, SQLite",
                "custom_future_field": {"retained": ["значение", 42]},
            },
            {
                "id": 7,
                "type": "Сайт / лендинг",
                "title": "Страница мероприятия",
                "description": "Адаптивная страница на русском языке",
                "created_at": "2026-10-24",
                "status": "Завершён",
                "technologies": [{"name": "HTML", "category": "Инструмент", "version": "5"}],
                "demo_url": "",
                "role": "Автор",
                "outcome": "Поддерживает мобильную ширину",
                "featured": False,
                "page_count": 3,
            },
        ],
    }


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "portfolio.sqlite3"
        self.store = SQLiteStore(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_round_trip_preserves_payload_and_searchable_project_columns(self) -> None:
        payload = sample_payload()
        self.store.save(payload)

        loaded = self.store.load()
        self.assertEqual(loaded, payload)
        with closing(sqlite3.connect(self.db_path)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            rows = connection.execute(
                "SELECT project_id, title, status, search_text FROM projects ORDER BY project_id"
            ).fetchall()
        self.assertEqual(version, 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][:3], (2, "CRM для студии", "В разработке"))
        self.assertIn("sqlite", rows[0][3])
        self.assertIn("flask", rows[0][3])
        self.assertIn("42", rows[0][3])

    def test_author_profile_extensions_round_trip_and_legacy_shape_remains_valid(self) -> None:
        payload = sample_payload()
        payload["developer"].update({"introduction": "Делаю удобные интерфейсы", "email": "hello@example.net",
            "website_url": "https://portfolio.example", "github_url": "", "include_email": True,
            "include_website": False, "include_github": False})
        self.store.save(payload)
        self.assertEqual(self.store.load()["developer"], payload["developer"])
        legacy = sample_payload()
        legacy["developer"] = {"full_name": "Имя", "specialization": "Frontend"}
        self.store.save(legacy)
        self.assertEqual(self.store.load()["developer"], legacy["developer"])

    def test_accessible_gallery_images_round_trip_and_invalid_gallery_is_rejected(self) -> None:
        payload = sample_payload()
        data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        payload["projects"][0]["gallery_images"] = [{"image_data": data, "alt": "Экран профиля", "position": "28% 72%"}]
        self.store.save(payload)
        self.assertEqual(self.store.load()["projects"][0]["gallery_images"], payload["projects"][0]["gallery_images"])
        expanded = [{"image_data": data, "alt": f"Экран {i}", "position": "50% 50%"} for i in range(10)]
        accepted = sample_payload()
        accepted["projects"][0]["gallery_images"] = expanded
        self.store.save(accepted)
        self.assertEqual(len(self.store.load()["projects"][0]["gallery_images"]), 10)
        oversized = "data:image/png;base64," + "A" * 1_333_312
        for invalid in ([{"image_data": data, "alt": ""}], [{"image_data": data, "alt": "Экран", "position": "101% 50%"}],
                        [{"image_data": data, "alt": "Экран"}] * 11,
                        [{"image_data": oversized, "alt": f"Деталь {i}", "position": "50% 50%"} for i in range(6)]):
            broken = sample_payload()
            broken["projects"][0]["gallery_images"] = invalid
            with self.subTest(gallery_count=len(invalid)), self.assertRaises(SQLiteStoreError):
                self.store.save(broken)

    def test_cover_focal_point_round_trips_and_rejects_out_of_range_values(self) -> None:
        payload = sample_payload()
        payload["projects"][0]["cover_position"] = "18% 82%"
        payload["projects"][0]["cover_position_mobile"] = "14% 91%"
        self.store.save(payload)
        self.assertEqual(self.store.load()["projects"][0]["cover_position"], "18% 82%")
        self.assertEqual(self.store.load()["projects"][0]["cover_position_mobile"], "14% 91%")
        invalid = sample_payload()
        invalid["projects"][0]["cover_position"] = "101% 50%"
        with self.assertRaisesRegex(SQLiteStoreError, "кадрирования обложки"):
            self.store.save(invalid)
        invalid_mobile = sample_payload()
        invalid_mobile["projects"][0]["cover_position_mobile"] = "101% 50%"
        with self.assertRaisesRegex(SQLiteStoreError, "кадрирования обложки для телефона"):
            self.store.save(invalid_mobile)

    def test_sqlite_rejects_corrupt_or_oversized_embedded_images(self) -> None:
        corrupt = sample_payload()
        corrupt["projects"][0]["cover_image_data"] = "data:image/png;base64,AA=="
        with self.assertRaisesRegex(SQLiteStoreError, "повреждено|не читается"):
            self.store.save(corrupt)

        image_bytes = io.BytesIO()
        Image.new("L", (5000, 5000), 1).save(image_bytes, format="PNG", optimize=True)
        oversized = sample_payload()
        oversized["projects"][0]["cover_image_data"] = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
        with self.assertRaisesRegex(SQLiteStoreError, "24 мегапикселя"):
            self.store.save(oversized)
        self.assertFalse(self.db_path.exists())

    def test_sqlite_enforces_portfolio_wide_image_count(self) -> None:
        payload = sample_payload()
        base = payload["projects"][0]
        data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        payload["projects"] = [
            {**base, "id": index + 1, "sort_order": index + 1,
             "cover_image_data": "", "gallery_images": [
                 {"image_data": data, "alt": f"Экран {image + 1}", "position": "50% 50%"}
                 for image in range(10)]}
            for index in range(26)
        ]
        payload["next_id"] = 27
        with self.assertRaisesRegex(SQLiteStoreError, "не больше 250 изображений"):
            self.store.save(payload)

    def test_sqlite_enforces_portfolio_wide_decoded_pixel_budget(self) -> None:
        image_bytes = io.BytesIO()
        Image.new("1", (6000, 4000), 0).save(image_bytes, format="PNG", optimize=True)
        data = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
        payload = sample_payload()
        base = payload["projects"][0]
        payload["projects"] = [
            {**base, "id": index + 1, "sort_order": index + 1,
             "cover_image_data": "", "gallery_images": [
                 {"image_data": data, "alt": f"Экран {index + 1}", "position": "50% 50%"}]}
            for index in range(6)
        ]
        payload["next_id"] = 7
        with self.assertRaisesRegex(SQLiteStoreError, "120 мегапикселей"):
            self.store.save(payload)
        self.assertFalse(self.db_path.exists())

    def test_sqlite_rejects_payloads_that_cannot_fit_a_portable_json_backup(self) -> None:
        with patch.object(storage, "_PORTFOLIO_MAX_JSON_BYTES", 1):
            with self.assertRaisesRegex(SQLiteStoreError, "лимит JSON-резервной копии 64 МиБ"):
                self.store.save(sample_payload())
        self.assertFalse(self.db_path.exists())

    def test_invalid_cover_asset_is_rejected(self) -> None:
        bad = sample_payload()
        bad["projects"][0]["cover_image"] = "../../private.png"
        with self.assertRaisesRegex(SQLiteStoreError, "обложк"):
            self.store.save(bad)

    def test_tags_round_trip_and_malformed_tags_are_rejected(self) -> None:
        payload = sample_payload()
        self.store.save(payload)
        self.assertEqual(self.store.load()["projects"][0]["tags"], ["Учёт", "CRM"])
        self.assertEqual(self.store.load()["projects"][0]["context"], "Небольшая команда ведёт заказы вручную.")
        for tags in (["x" * 33], ["повтор", " Повтор "], [""], ["\n"]):
            invalid = sample_payload()
            invalid["projects"][0]["tags"] = tags
            with self.subTest(tags=tags), self.assertRaises(SQLiteStoreError):
                self.store.save(invalid)

    def test_invalid_manual_order_is_rejected(self) -> None:
        invalid = sample_payload()
        invalid["projects"][0]["sort_order"] = True
        with self.assertRaisesRegex(SQLiteStoreError, "Порядок"):
            self.store.save(invalid)
        for page_count in (1.5, True, "3", 0):
            invalid = sample_payload()
            invalid["projects"][1]["page_count"] = page_count
            with self.subTest(page_count=page_count), self.assertRaisesRegex(SQLiteStoreError, "Количество страниц"):
                self.store.save(invalid)

    def test_sqlite_rejects_invalid_dates_and_technology_contract(self) -> None:
        original = sample_payload()
        self.store.save(original)
        cases = []
        invalid_date = sample_payload()
        invalid_date["projects"][0]["created_at"] = "2026-02-30"
        cases.append((invalid_date, "Дата проекта"))
        too_many = sample_payload()
        too_many["projects"][0]["technologies"] = [{"name": f"Tool {n}"} for n in range(41)]
        cases.append((too_many, "списком до 40"))
        for field, value in (("name", "x" * 61), ("category", "x" * 61), ("version", "x" * 41),
                             ("category", 3)):
            invalid_technology = sample_payload()
            invalid_technology["projects"][0]["technologies"][0][field] = value
            cases.append((invalid_technology, f"Поле '{field}' технологии"))

        for invalid, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(SQLiteStoreError, message):
                self.store.save(invalid)
            self.assertEqual(self.store.load(), original)

    def test_oversized_narrative_field_is_rejected(self) -> None:
        invalid = sample_payload()
        invalid["projects"][0]["process"] = "x" * 1501
        with self.assertRaisesRegex(SQLiteStoreError, "process"):
            self.store.save(invalid)

    def test_save_replaces_data_as_a_whole(self) -> None:
        first = sample_payload()
        self.store.save(first)
        updated = {**first, "title": "Новая версия", "projects": []}
        self.store.save(updated)

        self.assertEqual(self.store.load(), updated)

    def test_invalid_payload_is_rejected_before_existing_data_changes(self) -> None:
        original = sample_payload()
        self.store.save(original)
        invalid = sample_payload()
        invalid["projects"][1]["id"] = True

        with self.assertRaises(SQLiteStoreError):
            self.store.save(invalid)

        self.assertEqual(self.store.load(), original)

    def test_invalid_project_type_status_and_links_are_rejected_without_data_loss(self) -> None:
        original = sample_payload()
        self.store.save(original)
        cases = []
        unknown_type = sample_payload()
        unknown_type["projects"][0]["type"] = "Неизвестный тип"
        cases.append((unknown_type, "тип"))
        unknown_status = sample_payload()
        unknown_status["projects"][0]["status"] = "Неизвестный статус"
        cases.append((unknown_status, "статус"))
        credential_url = sample_payload()
        credential_url["projects"][0]["demo_url"] = "https://user:secret@example.com/demo"
        cases.append((credential_url, "HTTP"))
        malformed_url = sample_payload()
        malformed_url["projects"][0]["repository_url"] = "javascript:alert(1)"
        cases.append((malformed_url, "HTTP"))
        invalid_featured = sample_payload()
        invalid_featured["projects"][0]["featured"] = "false"
        cases.append((invalid_featured, "featured"))

        for invalid, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(SQLiteStoreError, message):
                self.store.save(invalid)
            self.assertEqual(self.store.load(), original)

    def test_unsupported_schema_version_is_rejected(self) -> None:
        self.store.save(sample_payload())
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute("PRAGMA user_version = 99")
            connection.commit()

        with self.assertRaisesRegex(SQLiteStoreError, "не поддерживается"):
            self.store.load()

    def test_corrupt_sqlite_file_is_rejected(self) -> None:
        self.db_path.write_bytes(b"this is not a SQLite database")

        with self.assertRaises(SQLiteStoreError):
            self.store.load()

    def test_malformed_project_json_is_rejected(self) -> None:
        self.store.save(sample_payload())
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                "UPDATE projects SET payload_json = ? WHERE project_id = 2", ("{bad json",)
            )
            connection.commit()

        with self.assertRaisesRegex(SQLiteStoreError, "Повреждён JSON проекта"):
            self.store.load()

    def test_wrong_payload_shape_is_rejected(self) -> None:
        bad = sample_payload()
        bad["developer"] = []

        with self.assertRaisesRegex(SQLiteStoreError, "developer"):
            self.store.save(bad)

    def test_unknown_sqlite_database_is_not_overwritten(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
            connection.commit()

        with self.assertRaises(SQLiteStoreError):
            self.store.save(sample_payload())
        with closing(sqlite3.connect(self.db_path)) as connection:
            names = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        self.assertEqual(names, [("unrelated",)])


if __name__ == "__main__":
    unittest.main()

