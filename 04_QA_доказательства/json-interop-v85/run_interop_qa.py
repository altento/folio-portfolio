from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parents[1]
if (PACKAGE_ROOT / "02_Приложение").is_dir():
    APP = PACKAGE_ROOT / "02_Приложение"
    TESTS = APP / "tests"
else:
    APP = HERE.parents[3]
    TESTS = APP / "tests"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(TESTS))
from sqlite_storage import SQLiteStore  # noqa: E402
from test_sqlite_storage import sample_payload  # noqa: E402


def main() -> None:
    payload = sample_payload()
    # Future-only fields are outside the currently shared desktop/web contract.
    payload["projects"] = [
        {key: value for key, value in project.items() if key != "custom_future_field"}
        for project in payload["projects"]
    ]
    payload["projects"][1]["gallery_images"] = [{
        "image_data": "data:image/png;base64,AA==",
        "alt": "Проверочный кадр",
        "position": "20% 80%",
    }]

    web_core = APP / "web" / "core.js"
    js = (
        "import {parsePortfolioFile,serializePortfolio} from "
        + json.dumps(web_core.as_uri())
        + ";let s='';for await(const c of process.stdin)s+=c;"
        + "console.log(JSON.stringify(serializePortfolio(parsePortfolioFile(s))))"
    )
    with tempfile.TemporaryDirectory(prefix="folio-json-interop-") as directory:
        temp = Path(directory)
        desktop_db = temp / "desktop.sqlite3"
        returned_db = temp / "returned.sqlite3"
        SQLiteStore(desktop_db).save(payload)
        desktop_export = SQLiteStore(desktop_db).load()
        result = subprocess.run(
            ["node", "--input-type=module", "-e", js],
            input=json.dumps(desktop_export, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            check=True,
        )
        web_export = json.loads(result.stdout.decode("utf-8"))
        SQLiteStore(returned_db).save(web_export)
        returned = SQLiteStore(returned_db).load()

    expected_tech = [
        [{"name": item["name"], "category": item["category"], "version": item["version"]}
         for item in project["technologies"]]
        for project in desktop_export["projects"]
    ]
    actual_tech = [project["technologies"] for project in returned["projects"]]
    assert actual_tech == expected_tech, "Technology category/version changed during round-trip."
    expected_gallery = desktop_export["projects"][1]["gallery_images"]
    actual_gallery = returned["projects"][1]["gallery_images"]
    assert actual_gallery == expected_gallery, "Gallery image data changed during round-trip."
    assert [project["title"] for project in returned["projects"]] == [
        project["title"] for project in desktop_export["projects"]
    ]
    assert all(returned["developer"].get(key) == value for key, value in desktop_export["developer"].items())

    evidence = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS",
        "route": "desktop JSON payload -> SQLite -> PWA parse/serialize -> SQLite",
        "fixture": "synthetic two-project fixture derived from the project's storage tests",
        "checks": {
            "project_count": len(returned["projects"]),
            "project_titles_and_order_preserved": True,
            "developer_profile_preserved": True,
            "technology_categories_and_versions_preserved": True,
            "cover_data_preserved": returned["projects"][0].get("cover_image_data")
            == desktop_export["projects"][0].get("cover_image_data"),
            "gallery_data_alt_and_crop_preserved": actual_gallery == expected_gallery,
            "both_sqlite_writes_validated": True,
        },
    }
    output = Path(__file__).with_name("results.json")
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: JSON interoperability; evidence saved to {output}")


if __name__ == "__main__":
    main()
