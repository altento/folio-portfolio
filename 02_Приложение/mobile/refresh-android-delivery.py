from __future__ import annotations



import hashlib

import shutil

import zipfile

from pathlib import Path





ROOT = Path(__file__).resolve().parent.parent

MOBILE = ROOT / "mobile"

PACKAGE_MOBILE = (

    ROOT

    / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"

    / "02_Приложение"

    / "mobile"

)

BUILT_APK = MOBILE / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

APK_NAME = "folio-android-debug.apk"

PHONE_ZIP = ROOT / "folio-android-debug-for-phone.zip"

CURRENT_MARKER = "### Текущая сборка для Android — web/PWA v118 private storage guidance"

PREVIOUS_MARKERS = (
    "### Текущая сборка для Android — web/PWA v117 showcase empty facts",

    "### Текущая сборка для Android — web/PWA v115 mobile readability",
    "### Текущая сборка для Android — web/PWA v116 short-landscape sidebar scroll",
    "### Текущая сборка для Android — web/PWA v114 local-data backup exclusions",
    "### Текущая сборка для Android — web/PWA v114 showcase preview accessibility",
    "### Текущая сборка для Android — web/PWA v112 shared cover focal point",
    "### Текущая сборка для Android — web/PWA v111 cross-device export guard",

    "### Текущая сборка для Android — web/PWA v110 cross-device JSON contract",

    "### Текущая сборка для Android — web/PWA v109 import limits, focus and accessible gallery",

    "### Текущая сборка для Android — web/PWA v108 import limits and focus preservation",

    "### Текущая сборка для Android — web/PWA v107 keyboard step focus",

    "### Текущая сборка для Android — web/PWA v106 mobile case form accessibility",

    "### Текущая сборка для Android — web/PWA v105 mobile case form wizard",

    "### Текущая сборка для Android — web/PWA v104 favorite sort clarity",

    "### Текущая сборка для Android — web/PWA v103 offline navigation",

    "### Текущая сборка для Android — web/PWA v102 mobile catalog disclosure",

    "### Текущая сборка для Android — web/PWA v101 import safety and mobile targets",

)





def sha256(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as stream:

        for block in iter(lambda: stream.read(1024 * 1024), b""):

            digest.update(block)

    return digest.hexdigest()





def main() -> None:

    if not BUILT_APK.is_file():

        raise FileNotFoundError(f"Debug APK not found: {BUILT_APK}")



    apk = MOBILE / APK_NAME

    shutil.copy2(BUILT_APK, apk)

    digest = sha256(apk)

    install_text = (

        "Установка folio на Android\n\n"

        "1. Распакуйте архив на телефоне.\n"

        f"2. Откройте {APK_NAME} и подтвердите установку из выбранного источника, если Android спросит.\n"

        "3. Запустите «folio». Данные остаются на устройстве; для переноса используйте экспорт/импорт JSON.\n\n"

        "Сборка: 02.11.2026, Android debug на основе web/PWA v118. Настройки предупреждают, что приватный браузерный сеанс может удалить локальные данные после закрытия; для постоянной работы рекомендуется обычный профиль и регулярная JSON-копия вне профиля. Это предупреждение не заменяет отдельную проверку реального private mode. Web regression — 53/53, Python/SQLite — 81/81. Резервное копирование Android отключено: allowBackup=false, legacy backup rules и современные cloud/device-transfer правила исключают пользовательские хранилища. Перенос выполняется явным JSON-экспортом.\n"

        "APK v118 собран, установлен поверх приложения на Android Emulator API 36 с сохранением данных и запущен; экран настроек визуально подтвердил новое предупреждение. Доказательство: `служебные_файлы/qa_02-11-2026/android-v118-private-storage/`. Физический телефон, реальная экранная клавиатура, TalkBack/TTS и private-mode поведение не проверялись.\n"

        "Это debug-сборка для проверки, не для Google Play.\n"

        "SHA-256 APK указан в SHA256.txt.\n"

    )

    (MOBILE / "УСТАНОВКА.txt").write_text(install_text, encoding="utf-8")

    (MOBILE / "SHA256.txt").write_text(f"{digest}  {APK_NAME}\n", encoding="ascii")



    readme_path = MOBILE / "README.md"

    readme = readme_path.read_text(encoding="utf-8-sig")

    section = (

        f"{CURRENT_MARKER} (02.11.2026)\n\n"

        "Web/PWA v118 добавляет предупреждение о риске удаления IndexedDB в приватном сеансе; private-mode поведение отдельно не симулировалось. Web suite: 53/53; Python/SQLite: 81/81. Android debug собран из тех же файлов, установлен поверх приложения на AVD API 36 без очистки данных и запущен; warning на экране настроек виден. Android Auto Backup отключён, все локальные пользовательские хранилища исключены из cloud backup/device transfer. Результаты: `служебные_файлы/qa_02-11-2026/android-v118-private-storage/`. Физический телефон, TalkBack/TTS и системное увеличение остаются открытыми.\n\n"

        f"SHA-256 APK: `{digest}`. Это debug APK, не для магазина.\n"

    )

    if CURRENT_MARKER in readme:
        start = readme.index(CURRENT_MARKER)
        next_heading = readme.find("\n#", start + len(CURRENT_MARKER))
        readme = readme[:start].rstrip() + "\n\n" + section + (
            "\n" + readme[next_heading + 1 :] if next_heading >= 0 else ""
        )
    else:
        previous_marker = next((marker for marker in PREVIOUS_MARKERS if marker in readme), None)
        if previous_marker:
            start = readme.index(previous_marker)
            readme = readme[:start].rstrip() + "\n\n" + section + "\n\n" + readme[start:]
        else:
            readme = readme.rstrip() + "\n\n" + section
    readme_path.write_text(readme, encoding="utf-8")



    PACKAGE_MOBILE.mkdir(parents=True, exist_ok=True)

    for name in (APK_NAME, "README.md", "УСТАНОВКА.txt", "SHA256.txt"):

        shutil.copy2(MOBILE / name, PACKAGE_MOBILE / name)



    temporary_zip = PHONE_ZIP.with_suffix(".zip.tmp")

    members = (APK_NAME, "УСТАНОВКА.txt", "SHA256.txt")

    with zipfile.ZipFile(

        temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6

    ) as archive:

        for name in members:

            archive.write(MOBILE / name, name)

    temporary_zip.replace(PHONE_ZIP)



    with zipfile.ZipFile(PHONE_ZIP) as archive:

        if set(archive.namelist()) != set(members):

            raise RuntimeError("Phone archive has an unexpected member set")

        if archive.testzip() is not None:

            raise RuntimeError("Phone archive CRC check failed")

        if hashlib.sha256(archive.read(APK_NAME)).hexdigest() != digest:

            raise RuntimeError("APK hash inside phone archive does not match the source APK")

    print(

        f"PASS: phone package refreshed; APK SHA-256={digest}; "

        f"ZIP size={PHONE_ZIP.stat().st_size} bytes"

    )





if __name__ == "__main__":

    main()

