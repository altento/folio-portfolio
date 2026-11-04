from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ADB = Path.home() / ".cache" / "folio-android-sdk" / "platform-tools" / "adb.exe"
AAPT = Path.home() / ".cache" / "folio-android-sdk" / "build-tools" / "36.1.0" / "aapt.exe"
APK = ROOT / "mobile" / "folio-android-debug.apk"
DEVICE = "emulator-5554"
PACKAGE = "ru.folio.portfolio"


def run(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def adb(*args: str) -> str:
    return run([str(ADB), "-s", DEVICE, *args])


def main() -> None:
    devices = run([str(ADB), "devices", "-l"])
    if not re.search(rf"(?m)^{re.escape(DEVICE)}\s+device\b", devices):
        raise RuntimeError(f"Expected emulator is not available:\n{devices}")
    # aapt on this Windows SDK build misreads ZIP paths containing Cyrillic.
    with tempfile.TemporaryDirectory(prefix="folio-apk-aapt-") as temp_dir:
        inspection_apk = Path(temp_dir) / "folio.apk"
        shutil.copy2(APK, inspection_apk)
        apk_manifest = run([str(AAPT), "dump", "xmltree", str(inspection_apk), "AndroidManifest.xml"])
        legacy_xml = run([str(AAPT), "dump", "xmltree", str(inspection_apk), "res/xml/backup_rules.xml"])
        extraction_xml = run([str(AAPT), "dump", "xmltree", str(inspection_apk), "res/xml/data_extraction_rules.xml"])
    if "android:allowBackup(0x01010280)=(type 0x12)0xffffffff" in apk_manifest:
        raise RuntimeError("Compiled manifest allows backup; expected allowBackup=false")
    backup_flag = re.search(r"android:allowBackup\([^\n]+", apk_manifest)
    if not backup_flag:
        raise RuntimeError("Compiled APK manifest does not expose allowBackup")
    domains = {"root", "file", "database", "sharedpref", "external", "device_root",
               "device_file", "device_database", "device_sharedpref"}
    legacy_domains = set(re.findall(r'domain="([^"]+)"', legacy_xml))
    cloud_domains = set(re.findall(r'domain="([^"]+)"', extraction_xml.split("E: device-transfer")[0]))
    device_domains = set(re.findall(r'domain="([^"]+)"', extraction_xml.split("E: device-transfer")[-1]))
    if not domains <= legacy_domains or not domains <= cloud_domains or not domains <= device_domains:
        raise RuntimeError("Compiled APK backup XML does not exclude all app data domains")

    install = adb("install", "-r", str(APK))
    adb("shell", "svc", "wifi", "disable")
    adb("shell", "svc", "data", "disable")
    adb("shell", "settings", "put", "global", "airplane_mode_on", "1")
    broadcast_result = subprocess.run(
        [str(ADB), "-s", DEVICE, "shell", "am", "broadcast", "-a",
         "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    broadcast = (broadcast_result.stdout or broadcast_result.stderr).strip()
    adb("shell", "am", "force-stop", PACKAGE)
    launch = adb("shell", "monkey", "-p", PACKAGE, "1")
    time.sleep(5)
    activities = adb("shell", "dumpsys", "activity", "activities")
    connectivity = adb("shell", "dumpsys", "connectivity")
    package_info = adb("shell", "dumpsys", "package", PACKAGE)
    airplane = adb("shell", "settings", "get", "global", "airplane_mode_on")
    screenshot = subprocess.run([str(ADB), "-s", DEVICE, "exec-out", "screencap", "-p"],
                                check=True, capture_output=True).stdout
    image_path = OUT / "android-v115-cold-offline-home.png"
    image_path.write_bytes(screenshot)
    results = {
        "build": "Android debug APK, web/PWA v115, local data backup exclusions",
        "device": DEVICE,
        "api_level": adb("shell", "getprop", "ro.build.version.sdk"),
        "install": install,
        "launch": launch,
        "package_installed": PACKAGE in adb("shell", "pm", "list", "packages", "-3"),
        "foreground_contains_package": PACKAGE in activities,
        "airplane_mode_setting": airplane,
        "airplane_mode_broadcast": broadcast,
        "airplane_mode_broadcast_exit_code": broadcast_result.returncode,
        "network_active": bool(re.search(r"(?m)^\s*Active default network:", connectivity))
                          and "Active default network: none" not in connectivity,
        "manifest_allow_backup": backup_flag.group(0),
        "backup_rules_in_apk": legacy_domains >= domains,
        "cloud_backup_exclusions": sorted(cloud_domains),
        "device_transfer_exclusions": sorted(device_domains),
        "version_name": next((line.strip() for line in package_info.splitlines()
                               if "versionName=" in line), None),
        "apk_sha256": hashlib.sha256(APK.read_bytes()).hexdigest(),
        "screenshot": image_path.name,
        "screenshot_bytes": len(screenshot),
        "screenshot_sha256": hashlib.sha256(screenshot).hexdigest(),
        "screenshot_png_signature_valid": screenshot.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    checks = (
        results["package_installed"], results["foreground_contains_package"],
        results["airplane_mode_setting"] == "1", not results["network_active"],
        results["manifest_allow_backup"].endswith("0x0"), results["backup_rules_in_apk"],
        results["cloud_backup_exclusions"] == sorted(domains),
        results["device_transfer_exclusions"] == sorted(domains),
        results["screenshot_png_signature_valid"],
    )
    results["status"] = "PASS" if all(checks) else "FAIL"
    (OUT / "android-v115-results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if results["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

