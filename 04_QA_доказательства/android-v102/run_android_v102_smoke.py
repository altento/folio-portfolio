from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r"C:\Users\Windows-10\.cache\folio-android-sdk\platform-tools\adb.exe")
APK = ROOT / "mobile" / "folio-android-debug.apk"
OUT = Path(__file__).resolve().parent
DEVICE = "emulator-5554"
PACKAGE = "ru.folio.portfolio"


def adb(*args: str) -> str:
    return subprocess.run([str(ADB), "-s", DEVICE, *args], check=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def main() -> None:
    devices = subprocess.run([str(ADB), "devices", "-l"], check=True, capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout
    if not re.search(rf"(?m)^{re.escape(DEVICE)}\s+device\b", devices):
        raise RuntimeError(f"Expected Android emulator {DEVICE} to be available:\n{devices}")
    install = adb("install", "-r", str(APK))
    clear_data = adb("shell", "pm", "clear", PACKAGE)
    adb("shell", "svc", "wifi", "disable")
    adb("shell", "svc", "data", "disable")
    adb("shell", "am", "force-stop", PACKAGE)
    launch = adb("shell", "monkey", "-p", PACKAGE, "1")
    time.sleep(5)
    version_info = adb("shell", "dumpsys", "package", PACKAGE)
    foreground_info = adb("shell", "dumpsys", "activity", "activities")
    wifi_state = adb("shell", "settings", "get", "global", "wifi_on")
    mobile_data_state = adb("shell", "settings", "get", "global", "mobile_data")
    screenshot = subprocess.run([str(ADB), "-s", DEVICE, "exec-out", "screencap", "-p"],
                                check=True, capture_output=True).stdout
    image_path = OUT / "android-v102-cold-offline-home.png"
    image_path.write_bytes(screenshot)
    image_hash = hashlib.sha256(screenshot).hexdigest()
    apk_hash = hashlib.sha256(APK.read_bytes()).hexdigest()
    results = {
        "build": "Android debug APK from web/PWA v102",
        "device": DEVICE,
        "api_level": adb("shell", "getprop", "ro.build.version.sdk"),
        "install": install,
        "clear_test_emulator_data": clear_data,
        "launch": launch,
        "package_installed": PACKAGE in adb("shell", "pm", "list", "packages", "-3"),
        "foreground_contains_package": PACKAGE in foreground_info,
        "wifi_global_setting": wifi_state,
        "mobile_data_global_setting": mobile_data_state,
        "offline_requested": wifi_state == "0" and mobile_data_state == "0",
        "version_name": next((line.strip() for line in version_info.splitlines() if "versionName=" in line), None),
        "apk_sha256": apk_hash,
        "screenshot": image_path.name,
        "screenshot_bytes": len(screenshot),
        "screenshot_sha256": image_hash,
        "screenshot_png_signature_valid": screenshot.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    results["status"] = "PASS" if all((results["package_installed"], results["foreground_contains_package"],
                                        results["offline_requested"], results["screenshot_png_signature_valid"])) else "FAIL"
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if results["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
