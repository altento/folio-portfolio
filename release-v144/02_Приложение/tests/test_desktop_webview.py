from __future__ import annotations

import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from desktop_webview import DOWNLOADS_KNOWN_FOLDER_ID, DesktopFileApi, _default_downloads_directory, create_local_server
from sqlite_storage import SQLiteStore


ROOT = Path(__file__).resolve().parents[1]


class DesktopWebViewHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="folio-webview-host-")
        self.profile = Path(self.temp.name)
        self.database = self.profile / "portfolio_data.sqlite3"
        self.server = create_local_server(ROOT / "web", self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def test_serves_responsive_app_shell_on_loopback(self) -> None:
        with urlopen(f"{self.base}/?folio-desktop=1", timeout=3) as response:
            self.assertEqual(response.status, 200)
            shell = response.read()
            self.assertIn(b"<!doctype html>", shell.lower())
            self.assertIn(b"id=\"main-content\"", shell)
        with urlopen(f"{self.base}/assets/illustrations/folio-dashboard-hero-v1.webp", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertGreater(int(response.headers["Content-Length"]), 10_000)

    def test_serves_backup_module_and_resolves_and_saves_downloads(self) -> None:
        with urlopen(f"{self.base}/backup-status.js", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"inspectPortfolioBackup", response.read())

        configured_downloads = self.profile / "redirected-downloads"

        class FakeRegistry:
            HKEY_CURRENT_USER = object()

            def OpenKey(self, _hive, _path):
                return self

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def QueryValueEx(self, _key, value_name):
                if value_name != DOWNLOADS_KNOWN_FOLDER_ID:
                    raise FileNotFoundError(value_name)
                return str(configured_downloads), 0

        self.assertEqual(
            _default_downloads_directory(registry_module=FakeRegistry(), fallback=self.profile / "fallback"),
            configured_downloads,
        )
        export_dir = self.profile / "exports"
        with patch.dict(os.environ, {"FOLIO_EXPORT_DIR": str(export_dir)}):
            api = DesktopFileApi()
            first = Path(api.save_file("folio-backup.json", '{"projects":[]}'))
            second = Path(api.save_file("folio-backup.json", '{"projects":[1]}'))
        self.assertEqual(first.parent, export_dir)
        self.assertEqual(second.name, "folio-backup (1).json")
        self.assertEqual(first.read_text(encoding="utf-8"), '{"projects":[]}')
        self.assertEqual(second.read_text(encoding="utf-8"), '{"projects":[1]}')

    def test_missing_legacy_database_returns_no_content_without_creating_it(self) -> None:
        with urlopen(f"{self.base}/desktop-seed.json", timeout=3) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
            self.assertEqual(response.read(), b"")
        self.assertFalse(self.database.exists())

    def test_legacy_seed_is_read_only_and_matches_sqlite_payload(self) -> None:
        payload = json.loads((ROOT / "tests" / "fixtures" / "portable-transfer.json").read_text(encoding="utf-8"))
        store = SQLiteStore(self.database)
        store.save(payload)
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()

        with urlopen(f"{self.base}/desktop-seed.json", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
            seeded = json.loads(response.read())

        self.assertEqual(seeded, store.load())
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)

    def test_desktop_recovery_snapshot_is_served_before_legacy_seed_can_be_reused(self) -> None:
        original = json.loads((ROOT / "tests" / "fixtures" / "portable-transfer.json").read_text(encoding="utf-8"))
        SQLiteStore(self.database).save(original)
        legacy_hash = hashlib.sha256(self.database.read_bytes()).hexdigest()
        updated = json.loads(json.dumps(original))
        updated["projects"][0]["description"] = "Изменено после переноса"

        result = DesktopFileApi(self.profile).save_recovery_snapshot(json.dumps(updated, ensure_ascii=False))
        with urlopen(f"{self.base}/desktop-recovery.json", timeout=3) as response:
            snapshot = json.loads(response.read())

        self.assertEqual(response.status, 200)
        self.assertEqual(snapshot["format"], "folio-local-recovery")
        self.assertEqual(snapshot["version"], 1)
        self.assertEqual(snapshot["saved_at"], result["saved_at"])
        self.assertEqual(snapshot["portfolio"]["projects"][0]["description"], "Изменено после переноса")
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), legacy_hash)

    def test_missing_desktop_recovery_snapshot_returns_no_content(self) -> None:
        with urlopen(f"{self.base}/desktop-recovery.json", timeout=3) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
            self.assertEqual(response.read(), b"")

    def test_invalid_desktop_recovery_snapshot_is_rejected_without_writing(self) -> None:
        api = DesktopFileApi(self.profile)
        with self.assertRaises(ValueError):
            api.save_recovery_snapshot(json.dumps({"projects": []}))
        self.assertFalse((self.profile / "folio-recovery-v1.json").exists())

    def test_corrupt_desktop_recovery_snapshot_fails_closed(self) -> None:
        (self.profile / "folio-recovery-v1.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(HTTPError) as caught:
            urlopen(f"{self.base}/desktop-recovery.json", timeout=3)
        self.assertEqual(caught.exception.code, 500)
        with caught.exception as response:
            error = json.loads(response.read())
        self.assertIn("повреждена", error["error"])

    def test_corrupt_legacy_database_fails_closed_without_overwriting_it(self) -> None:
        original = b"not a SQLite database\n"
        self.database.write_bytes(original)
        with self.assertRaises(HTTPError) as caught:
            urlopen(f"{self.base}/desktop-seed.json", timeout=3)
        self.assertEqual(caught.exception.code, 500)
        self.assertEqual(self.database.read_bytes(), original)

    def test_server_rejects_unexpected_host_and_unlisted_files(self) -> None:
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request("GET", "/", headers={"Host": "attacker.example"})
        self.assertEqual(connection.getresponse().status, 403)
        connection.close()

        with self.assertRaises(HTTPError) as caught:
            urlopen(f"{self.base}/package.json", timeout=3)
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
