from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
APK = ROOT / "mobile" / "folio-android-debug.apk"
SDK = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or Path(os.environ["LOCALAPPDATA"]) / "Android" / "Sdk")
ADB = SDK / "platform-tools" / "adb.exe"


def adb(serial: str, *args: str, check: bool = True, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        [str(ADB), "-s", serial, *args],
        capture_output=True,
        check=check,
    )
    if binary:
        return result.stdout
    return (result.stdout + result.stderr).decode("utf-8", errors="replace").strip()


def installed_version(serial: str) -> tuple[int | None, str | None]:
    result = str(adb(serial, "shell", "dumpsys", "package", "ru.folio.portfolio", check=False))
    code = re.search(r"versionCode=(\d+)", result)
    name = re.search(r"versionName=([^\s]+)", result)
    return (int(code.group(1)) if code else None, name.group(1) if name else None)


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Android screen capture is not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def main() -> None:
    if not APK.is_file() or not ADB.is_file():
        raise FileNotFoundError("APK or Android Debug Bridge is missing")
    OUT.mkdir(parents=True, exist_ok=True)

    devices = str(subprocess.run([str(ADB), "devices"], capture_output=True, check=True).stdout.decode("utf-8", errors="replace"))
    serials = re.findall(r"^(emulator-\d+)\s+device\b", devices, re.MULTILINE)
    if len(serials) != 1:
        raise RuntimeError(f"Expected one ready QA emulator; found {serials!r}")
    serial = serials[0]
    if str(adb(serial, "shell", "getprop", "sys.boot_completed")) != "1":
        raise RuntimeError("The QA emulator has not completed boot")

    before_code, before_name = installed_version(serial)
    with tempfile.TemporaryDirectory(prefix="folio-v154-apk-") as raw_temp:
        temp_apk = Path(raw_temp) / "folio-v154.apk"
        shutil.copy2(APK, temp_apk)
        install_output = subprocess.run([str(ADB), "-s", serial, "install", "-r", str(temp_apk)], capture_output=True, check=True)
    install_text = (install_output.stdout + install_output.stderr).decode("utf-8", errors="replace").strip()
    after_code, after_name = installed_version(serial)
    if after_code != 29 or after_name != "0.3.17":
        raise RuntimeError(f"Unexpected installed version: code={after_code}, name={after_name}")

    with zipfile.ZipFile(APK) as archive:
        html = archive.read("assets/public/index.html").decode("utf-8")
        service_worker = archive.read("assets/public/sw.js").decode("utf-8")
        styles = archive.read("assets/public/styles.css").decode("utf-8")
    embedded_assets_match = (
        'id="update-notice"' in html
        and 'aria-labelledby="update-notice-title"' in html
        and 'role="status"' in html
        and "folio-shell-v154-mobile-touch-targets" in service_worker
        and "min-height:44px" in styles
    )
    if not embedded_assets_match:
        raise RuntimeError("APK does not contain the v154 update notice assets")

    start_output = str(adb(serial, "shell", "am", "start", "-n", "ru.folio.portfolio/.MainActivity"))
    time.sleep(8)
    pid = str(adb(serial, "shell", "pidof", "ru.folio.portfolio", check=False)).strip()
    xml_path = "/sdcard/folio-v154-window.xml"

    def accessibility_tree() -> tuple[str, list[str], list[dict[str, str]]]:
        dump = str(adb(serial, "shell", "uiautomator", "dump", xml_path, check=False))
        raw = adb(serial, "exec-out", "cat", xml_path, check=False, binary=True)
        values: list[str] = []
        nodes: list[dict[str, str]] = []
        if isinstance(raw, bytes) and raw.strip().startswith(b"<?xml"):
            tree = ElementTree.fromstring(raw)
            for node in tree.iter("node"):
                text = node.attrib.get("text", "").strip()
                description = node.attrib.get("content-desc", "").strip()
                if text or description:
                    values.append(text or description)
                nodes.append(dict(node.attrib))
        return dump, values, nodes

    tree_dump, tree_text, tree_nodes = accessibility_tree()
    key = "Ваши проекты, собранные в одном месте."
    for _ in range(12):
        if any(key in value or "Доступно обновление приложения" in value for value in tree_text):
            break
        time.sleep(2)
        tree_dump, tree_text, tree_nodes = accessibility_tree()
    clickable_nodes = [node for node in tree_nodes if node.get("clickable") == "true"]
    clickable = len(clickable_nodes)
    unnamed_clickable = sum(not node.get("text", "").strip() and not node.get("content-desc", "").strip() for node in clickable_nodes)
    title_visible = any(key in value for value in tree_text)
    update_notice_visible_before = any("Доступно обновление приложения" in value for value in tree_text)

    screenshot_data = adb(serial, "exec-out", "screencap", "-p", binary=True)
    if not isinstance(screenshot_data, bytes):
        raise RuntimeError("Could not capture emulator screen")
    screenshot = OUT / ("android-v154-update-banner.png" if update_notice_visible_before else "android-v154-dashboard-after-update.png")
    screenshot.write_bytes(screenshot_data)
    width, height = png_size(screenshot_data)

    reload_node = next((node for node in tree_nodes if node.get("text", "").strip() == "Перезапустить" and node.get("clickable") == "true"), None)
    reload_bounds = reload_node.get("bounds", "") if reload_node else ""
    update_notice_cleared = not update_notice_visible_before
    post_reload_title_visible = title_visible
    post_reload_screenshot = screenshot
    post_reload_size = (width, height)
    if reload_node:
        coordinates = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", reload_bounds)
        if not coordinates:
            raise RuntimeError(f"Could not parse reload button bounds: {reload_bounds!r}")
        left, top, right, bottom = (int(value) for value in coordinates.groups())
        adb(serial, "shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
        time.sleep(6)
        _, after_text, after_nodes = accessibility_tree()
        for _ in range(12):
            if any(key in value for value in after_text):
                break
            time.sleep(2)
            _, after_text, after_nodes = accessibility_tree()
        post_reload_title_visible = any(key in value for value in after_text)
        update_notice_cleared = not any("Доступно обновление приложения" in value for value in after_text)
        pid = str(adb(serial, "shell", "pidof", "ru.folio.portfolio", check=False)).strip()
        post_reload_data = adb(serial, "exec-out", "screencap", "-p", binary=True)
        if not isinstance(post_reload_data, bytes):
            raise RuntimeError("Could not capture post-update emulator screen")
        post_reload_screenshot = OUT / "android-v154-dashboard-after-update.png"
        post_reload_screenshot.write_bytes(post_reload_data)
        post_reload_size = png_size(post_reload_data)

    screenshots = []
    for shot, dims in ((screenshot, (width, height)), (post_reload_screenshot, post_reload_size)):
        if any(item["file"] == shot.name for item in screenshots):
            continue
        data = shot.read_bytes()
        screenshots.append({"file": shot.name, "width": dims[0], "height": dims[1], "sha256": hashlib.sha256(data).hexdigest()})

    first_install_evidence = []
    for name, stage in (("dashboard.png", "first launch with update notice"),
                        ("dashboard-after-update.png", "dashboard after applying update")):
        shot = OUT / name
        if shot.is_file() and all(item["file"] != name for item in screenshots):
            data = shot.read_bytes()
            dims = png_size(data)
            item = {"file": name, "width": dims[0], "height": dims[1],
                    "sha256": hashlib.sha256(data).hexdigest(), "stage": stage}
            screenshots.append(item)
            first_install_evidence.append(item)

    saved_tree = OUT / "window-after-update.xml"
    tree_evidence = None
    if saved_tree.is_file():
        tree_evidence = {"file": saved_tree.name, "size_bytes": saved_tree.stat().st_size,
                         "sha256": hashlib.sha256(saved_tree.read_bytes()).hexdigest()}
    apk_digest = hashlib.sha256(APK.read_bytes()).hexdigest()

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "emulator": serial,
        "app_package": "ru.folio.portfolio",
        "installed_before": {"version_code": before_code, "version_name": before_name},
        "install_command": "adb install -r (no uninstall, clear-data, or wipe-data)",
        "install_output": install_text,
        "installed_after": {"version_code": after_code, "version_name": after_name},
        "install_mode": "upgrade over existing app" if before_code is not None else "fresh install",
        "embedded_v154_assets": embedded_assets_match,
        "launch_output": start_output,
        "app_process_running": bool(pid),
        "dashboard_title_before_update_in_accessibility_tree": title_visible,
        "update_notice_visible_before_reload": update_notice_visible_before,
        "update_reload_button_bounds": reload_bounds or None,
        "update_notice_cleared_after_reload": update_notice_cleared,
        "dashboard_title_after_reload_in_accessibility_tree": post_reload_title_visible,
        "named_clickable_controls": clickable - unnamed_clickable,
        "unnamed_clickable_controls": unnamed_clickable,
        "uiautomator_dump_result": tree_dump,
        "uiautomator_evidence": tree_evidence,
        "first_install_update_transition_evidence": first_install_evidence,
        "apk_sha256": apk_digest,
        "screenshots": screenshots,
        "data_scope": "dedicated FolioQA_API36 emulator; no physical phone or user browser profile used",
        "limits": ["This verifies emulator install and launch, not physical-device compatibility or TalkBack speech and gesture acceptance."],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "install_output"}, ensure_ascii=False, indent=2))
    if not embedded_assets_match or not pid or unnamed_clickable or not title_visible or not post_reload_title_visible or not update_notice_cleared:
        raise SystemExit("Android v154 smoke requires review")


if __name__ == "__main__":
    main()

