from __future__ import annotations
import hashlib, json, re, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r"C:\Users\Windows-10\.cache\folio-android-sdk\platform-tools\adb.exe")
APK = ROOT / "mobile" / "folio-android-debug.apk"
OUT = Path(__file__).resolve().parent
DEVICE = "emulator-5554"
PACKAGE = "ru.folio.portfolio"

def adb(*args: str) -> str:
    return subprocess.run([str(ADB), "-s", DEVICE, *args], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()

def main() -> None:
    devices = subprocess.run([str(ADB), "devices", "-l"], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    if not re.search(rf"(?m)^{re.escape(DEVICE)}\s+device\b", devices):
        raise RuntimeError(f"Expected Android emulator {DEVICE} to be available:\n{devices}")
    install = adb("install", "-r", str(APK))
    adb("shell", "svc", "wifi", "disable")
    adb("shell", "svc", "data", "disable")
    adb("shell", "settings", "put", "global", "airplane_mode_on", "1")
    broadcast = subprocess.run([str(ADB), "-s", DEVICE, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    adb("shell", "am", "force-stop", PACKAGE)
    launch = adb("shell", "monkey", "-p", PACKAGE, "1")
    time.sleep(5)
    foreground = adb("shell", "dumpsys", "activity", "activities")
    connectivity = adb("shell", "dumpsys", "connectivity")
    airplane = adb("shell", "settings", "get", "global", "airplane_mode_on")
    screenshot = subprocess.run([str(ADB), "-s", DEVICE, "exec-out", "screencap", "-p"], check=True, capture_output=True).stdout
    image_path = OUT / "android-v114-cold-offline-home.png"
    image_path.write_bytes(screenshot)
    package_info = adb("shell", "dumpsys", "package", PACKAGE)
    results = {
        "build": "Android debug APK containing web/PWA v114",
        "device": DEVICE,
        "api_level": adb("shell", "getprop", "ro.build.version.sdk"),
        "install": install,
        "launch": launch,
        "package_installed": PACKAGE in adb("shell", "pm", "list", "packages", "-3"),
        "foreground_contains_package": PACKAGE in foreground,
        "airplane_mode_setting": airplane,
        "airplane_mode_broadcast": broadcast.stdout.strip() or broadcast.stderr.strip(),
        "network_active": bool(re.search(r"(?m)^\s*Active default network:", connectivity)) and "Active default network: none" not in connectivity,
        "version_name": next((line.strip() for line in package_info.splitlines() if "versionName=" in line), None),
        "apk_sha256": hashlib.sha256(APK.read_bytes()).hexdigest(),
        "screenshot": image_path.name,
        "screenshot_bytes": len(screenshot),
        "screenshot_sha256": hashlib.sha256(screenshot).hexdigest(),
        "screenshot_png_signature_valid": screenshot.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    results["status"] = "PASS" if all((results["package_installed"], results["foreground_contains_package"], results["airplane_mode_setting"] == "1", not results["network_active"], results["screenshot_png_signature_valid"])) else "FAIL"
    (OUT / "android-v114-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if results["status"] != "PASS": raise SystemExit(1)

if __name__ == "__main__": main()
