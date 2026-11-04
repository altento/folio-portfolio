from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MOBILE = ROOT / "mobile"
PACKAGE = ROOT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку" / "02_Приложение" / "mobile"
BUILT_APK = MOBILE / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
PHONE_ZIP = ROOT / "folio-android-debug-for-phone.zip"


def main() -> None:
    apk = MOBILE / "folio-android-debug.apk"
    shutil.copy2(BUILT_APK, apk)
    PACKAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(apk, PACKAGE / apk.name)
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()

    install = (
        "Установка folio на Android\n\n"
        "1. Распакуйте архив на телефоне.\n"
        "2. Откройте folio-android-debug.apk и подтвердите установку из выбранного источника, если Android спросит.\n"
        "3. Запустите «folio». Данные остаются на устройстве; для переноса используйте экспорт/импорт JSON.\n\n"
        "Сборка: 01.11.2026, web/PWA v85. Debug APK для проверки, не для Google Play. "
        "Обновление установлено и запущено на эмуляторе Android API 36 (1080×2400); физический телефон не подключён.\n"
        "SHA-256 APK указан в SHA256.txt.\n"
    )
    (MOBILE / "УСТАНОВКА.txt").write_text(install, encoding="utf-8")
    (MOBILE / "SHA256.txt").write_text(f"{digest}  {apk.name}\n", encoding="ascii")
    readme = MOBILE / "README.md"
    existing = readme.read_text(encoding="utf-8-sig")
    marker = "### Последняя проверенная сборка — web/PWA v85"
    update = (
        f"{marker} (01.11.2026)\n\n"
        "APK пересобран штатным Gradle build, установлен и запущен на Android Emulator API 36 (1080×2400). "
        "Эмуляторный экран сохранён в `04_QA_доказательства/json-interop-v85/android-emulator-v85-1080x2400.png`. "
        f"SHA-256 APK: `{digest}`. Это debug APK; физический телефон не проверялся.\n"
    )
    if marker in existing:
        existing = existing[:existing.index(marker)].rstrip() + "\n\n" + update
    else:
        existing = existing.rstrip() + "\n\n" + update
    readme.write_text(existing, encoding="utf-8")

    PACKAGE.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "УСТАНОВКА.txt", "SHA256.txt"):
        shutil.copy2(MOBILE / name, PACKAGE / name)

    temp_zip = PHONE_ZIP.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in (apk.name, "УСТАНОВКА.txt", "SHA256.txt"):
            archive.write(MOBILE / name, name)
    temp_zip.replace(PHONE_ZIP)
    with zipfile.ZipFile(PHONE_ZIP) as archive:
        if set(archive.namelist()) != {apk.name, "УСТАНОВКА.txt", "SHA256.txt"}:
            raise RuntimeError("Phone archive has an unexpected member set.")
        if hashlib.sha256(archive.read(apk.name)).hexdigest() != digest:
            raise RuntimeError("APK hash inside phone archive does not match the source APK.")
    print(f"PASS: refreshed APK and phone ZIP; SHA-256 {digest}; ZIP {PHONE_ZIP.stat().st_size} bytes")


if __name__ == "__main__":
    main()
