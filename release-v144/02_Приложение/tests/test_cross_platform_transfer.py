from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAIN_PATH = ROOT / "main.py"
SPEC = importlib.util.spec_from_file_location("folio_cross_platform_transfer_app", MAIN_PATH)
APP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


class CrossPlatformTransferTests(unittest.TestCase):
    def test_sqlite_to_web_to_desktop_to_sqlite_preserves_every_portable_field(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for the cross-runtime transfer regression.")
        fixture = ROOT / "tests" / "fixtures" / "portable-transfer.json"
        app_stub = object.__new__(APP.PortfolioApp)

        def payload_from_model(portfolio, developer):
            return {
                "schema_version": APP.DATA_SCHEMA_VERSION,
                "title": portfolio.title,
                "next_id": portfolio.next_id,
                "developer": APP.asdict(developer),
                "projects": [app_stub.record(project) for project in portfolio.projects],
            }

        with tempfile.TemporaryDirectory(prefix="folio-cross-platform-") as temp:
            temp = Path(temp)
            source_db = temp / "source.sqlite3"
            destination_db = temp / "destination.sqlite3"
            source_portfolio, source_developer = app_stub._read_data(
                fixture, set_active_store=False, apply=False
            )
            source_payload = payload_from_model(source_portfolio, source_developer)
            APP.SQLiteStore(source_db).save(source_payload)

            imported_portfolio, imported_developer = app_stub._read_data(
                source_db, set_active_store=False, apply=False
            )
            desktop_json = APP.serialize_portable_json(
                payload_from_model(imported_portfolio, imported_developer)
            )
            js = (
                "import {parsePortfolioFile,serializePortfolio} from './core.js';"
                "let text='';for await(const part of process.stdin)text+=part;"
                "process.stdout.write(JSON.stringify(serializePortfolio(parsePortfolioFile(text))));"
            )
            result = subprocess.run(
                [node, "--input-type=module", "-e", js],
                cwd=ROOT / "web",
                input=desktop_json,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            web_export = json.loads(result.stdout)
            web_file = temp / "web-export.json"
            web_file.write_text(json.dumps(web_export, ensure_ascii=False), encoding="utf-8")

            returned_portfolio, returned_developer = app_stub._read_data(
                web_file, set_active_store=False, apply=False
            )
            returned_payload = payload_from_model(returned_portfolio, returned_developer)
            APP.SQLiteStore(destination_db).save(returned_payload)
            final_payload = APP.SQLiteStore(destination_db).load()

            self.assertEqual(
                json.loads(APP.serialize_portable_json(final_payload)),
                json.loads(desktop_json),
            )


if __name__ == "__main__":
    unittest.main()

