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

CURRENT_MARKER = '### Текущая сборка — Web/PWA v161 accessible vector controls and contrast'

PREVIOUS_MARKERS = (
    '### Историческая сборка — Web/PWA v160 доступность раскрытия мобильных фильтров',
    "### Текущая сборка — Web/PWA v159 читаемость мобильных меток",
    "### Историческая сборка — Web/PWA v158 исправление счётчика подсказок",
    "### Историческая сборка — Web/PWA v157 локальная копия восстановления",
    "### Историческая сборка — Web/PWA v156 единое объяснение локального хранения",
    "### Историческая сборка — Web/PWA v155 приватность резервной копии",
    "### Историческая сборка — Web/PWA v154 мобильные зоны нажатия",
    "### Текущая сборка — Web/PWA v154 мобильные зоны нажатия",
    "### Текущая сборка — Web/PWA v153 доступность уведомления обновления",
    "### Текущая сборка — Web/PWA v152 mobile toolbar readability",
    "### Историческая сборка — Web/PWA v151 compact short-screen form",
    "### Историческая сборка — Web/PWA v150 backup status",
    "### Текущая сборка — web/PWA v147 focus ring предпросмотра импорта",
    "### Историческая сборка — web/PWA v146 доступность импорта",
    "### Историческая сборка — Android 0.3.8 / web/PWA v145 mobile import actions",
    "### Историческая сборка — web/PWA v143 project wizard dark contrast",
    "### Историческая сборка — web/PWA v137 mobile dialog focus return",
    "### Историческая сборка — web/PWA v136 responsive cover crop preview",
    "### Историческая сборка — web/PWA v135 responsive per-device cover crop",
    "### Историческая сборка — web/PWA v134 clean desktop first run",
    "### Историческая сборка — web/PWA v133 compact cover assets",
    "### Историческая сборка — web/PWA v123 Android back navigation",
    "### Историческая сборка — web/PWA v122 mobile bottom spacing",
    "### Историческая сборка — web/PWA v121 monotonic project IDs",
    "### Историческая сборка — web/PWA v120 cover contrast labels",
    "### Историческая сборка — web/PWA v119 demo copy edit",
    "### Историческая сборка — web/PWA v117 showcase empty facts",

    "### Историческая сборка — web/PWA v115 mobile readability",
    "### Историческая сборка — web/PWA v116 short-landscape sidebar scroll",
    "### Историческая сборка — web/PWA v114 local-data backup exclusions",
    "### Историческая сборка — web/PWA v114 showcase preview accessibility",
    "### Историческая сборка — web/PWA v112 shared cover focal point",
    "### Историческая сборка — web/PWA v111 cross-device export guard",

    "### Историческая сборка — web/PWA v110 cross-device JSON contract",

    "### Историческая сборка — web/PWA v109 import limits, focus and accessible gallery",

    "### Историческая сборка — web/PWA v108 import limits and focus preservation",

    "### Историческая сборка — web/PWA v107 keyboard step focus",

    "### Историческая сборка — web/PWA v106 mobile case form accessibility",

    "### Историческая сборка — web/PWA v105 mobile case form wizard",

    "### Историческая сборка — web/PWA v104 favorite sort clarity",

    "### Историческая сборка — web/PWA v103 offline navigation",

    "### Историческая сборка — web/PWA v102 mobile catalog disclosure",

    "### Историческая сборка — web/PWA v101 import safety and mobile targets",

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

    shutil.copy2(apk, ROOT / APK_NAME)

    digest = sha256(apk)

    install_text = (
        "Установка folio на Android\n\n"
        "1. Распакуйте архив на телефоне.\n"
        f"2. Откройте {APK_NAME} и подтвердите установку из выбранного источника, если Android спросит.\n"
        "3. Запустите «folio». Данные остаются на устройстве; для переноса используйте экспорт/импорт JSON.\n\n"
        "Сборка: Web/PWA v161, Windows WebView2 v164 и Android 0.3.24 (versionCode 36). Web regression: 85/85; Android использует те же Web/PWA ресурсы v161. Service Worker cache: `folio-shell-v161-accessible-vector-controls`. Android Auto Backup отключён, пользовательские хранилища исключены из cloud backup/device transfer.\n"
        "Физический телефон, аудиопроверка TalkBack/TTS, системное увеличение и поведение private mode не проверялись. Это debug APK для проверки, не для Google Play; для магазина нужна отдельная release-подпись.\n"
        "SHA-256 APK указан в SHA256.txt.\n"
    )

    (MOBILE / "УСТАНОВКА.txt").write_text(install_text, encoding="utf-8")

    (MOBILE / "SHA256.txt").write_text(f"{digest}  {APK_NAME}\n", encoding="ascii")

    (ROOT / "SHA256.txt").write_text(f"{digest}  {APK_NAME}\n", encoding="ascii")



    readme_path = MOBILE / "README.md"

    readme = readme_path.read_text(encoding="utf-8-sig")
    readme_lines = readme.splitlines()
    if len(readme_lines) < 5 or not readme_lines[0].startswith("# folio для Android"):
        raise RuntimeError("Android README header changed; update its current-build summary explicitly.")
    readme_lines[2] = (
        "Текущий Android debug APK — 0.3.24 (versionCode 36) со встроенными Web/PWA ресурсами v161. "
        "Он установлен через `adb install -r` поверх 0.3.22 на выделенный AVD API 36 без очистки данных; "
        "баннер обновления и холодный офлайн-запуск зафиксированы. Снимки и протокол: "
        "`служебные_файлы/qa_10-11-2026/android-v161/`. UIAutomator увидел только контейнер WebView; "
        "внутреннее дерево WebView, физический телефон и речь/жесты TalkBack этим прогоном не подтверждены. "
        "APK подписан debug-ключом, это не сборка Google Play."
    )
    readme_lines[4] = f"SHA-256 APK: `{digest}`."
    readme = "\n".join(readme_lines) + "\n"
    readme = readme.replace(
        "Android 0.3.14 (versionCode 26), Web/PWA v151.",
        "Android 0.3.14 (versionCode 26), Web/PWA v151b.",
        1,
    )
    readme = readme.replace(
        "Android 0.3.15 (versionCode 27), Web/PWA v152.",
        "Android 0.3.16 (versionCode 28), Web/PWA v153.",
        1,
    )
    readme = readme.replace(
        "Текущий Android debug APK — 0.3.18 (versionCode 30) со встроенными Web/PWA ресурсами v155.",
        "Текущий Android debug APK — 0.3.19 (versionCode 31) со встроенными Web/PWA ресурсами v156.",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v158 исправление счётчика подсказок",
        "### Историческая сборка — Web/PWA v158 исправление счётчика подсказок",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v157 локальная копия восстановления",
        "### Историческая сборка — Web/PWA v157 локальная копия восстановления",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v156 единое объяснение локального хранения",
        "### Историческая сборка — Web/PWA v156 единое объяснение локального хранения",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v155 приватность резервной копии",
        "### Историческая сборка — Web/PWA v155 приватность резервной копии",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v154 мобильные зоны нажатия",
        "### Историческая сборка — Web/PWA v154 мобильные зоны нажатия",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v153 доступность уведомления обновления",
        "### Историческая сборка — Web/PWA v153 доступность уведомления обновления",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v152 mobile toolbar readability",
        "### Историческая сборка — Web/PWA v152 mobile toolbar readability",
        1,
    )
    readme = readme.replace(
        "v150 установлен поверх прежнего состояния AVD API 36 без очистки данных; холодный запуск офлайн, экран настроек и локальный статус JSON-копии подтверждены. TalkBack UIA tree: 23 clickable controls, 0 безымянных. Аудио/жесты на физическом телефоне не проверены.",
        "v151b установлен поверх прежней версии без очистки данных; на AVD API 36 проверены dashboard и компактная форма проекта при 320×568. Отдельный Playwright layout viewport проверен при 320×512. Физический телефон и TalkBack речь/жесты не проверялись.",
        1,
    )
    readme = readme.replace(
        "Web/PWA v151 ensures the first project form field is visible on compact phone screens and pressing Next focuses and scrolls to the required title. Android debug 0.3.14 / code 26. Installed over existing AVD data and checked offline at 320×568; storage stays local. Physical-device TalkBack audio/gestures remain unverified.",
        "Historical v151 first compact-form pass. Android AVD audit later found the form clipped after Android system bars reduced the WebView layout viewport; the follow-up fix and retest are recorded in v151b below.",
        1,
    )

    readme = readme.replace(
        "Android 0.2.6 (versionCode 8), Web/PWA v133.",
        "Android 0.3.14 (versionCode 26), Web/PWA v151b.",
    )

    readme = readme.replace(
        "Android 0.3.13 (versionCode 25), Web/PWA v150.",
        "Android 0.3.14 (versionCode 26), Web/PWA v151b.",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v151 compact short-screen form",
        "### Историческая сборка — Web/PWA v151 compact short-screen form",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v151b Android compact viewport",
        "### Историческая сборка — Web/PWA v151b Android compact viewport",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — Web/PWA v150 backup status",
        "### Историческая сборка — Web/PWA v150 backup status",
        1,
    )
    readme = readme.replace(
        "### Текущая сборка — web/PWA v147 focus ring предпросмотра импорта",
        "### Историческая сборка — web/PWA v147 focus ring предпросмотра импорта",
        1,
    )

    section = (

        f"{CURRENT_MARKER} (10.11.2026)\n\n"

        "Web/PWA v161 makes decorative symbols inside icon-only controls silent to screen readers and adds stable high-contrast backing for labels over artwork, including bright custom covers. Android debug 0.3.24 / code 36 is built from the same web assets and installed over 0.3.23 on the dedicated AVD without clearing app data. The update notice, launch and offline behavior are documented with screenshots and protocol in `служебные_файлы/qa_10-11-2026/android-v161/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.\n\n"

        f"SHA-256 APK: `{digest}`. Это debug APK, не для магазина.\n"

    )

    # Keep the release history unambiguous when refreshing a newer build.
    # A prior release can be listed as "current" in older README revisions;
    # demote every such heading except the release being written now.
    for heading in readme.splitlines():
        if heading.startswith("### Текущая сборка — ") and not heading.startswith(CURRENT_MARKER):
            readme = readme.replace(
                heading,
                heading.replace("### Текущая сборка — ", "### Историческая сборка — ", 1),
                1,
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

    # Remove a stale duplicate of this release if an earlier refresh inserted it
    # as history before the current heading existed.
    historical_current = CURRENT_MARKER.replace(
        "### Текущая сборка — ", "### Историческая сборка — ", 1
    )
    normalized_lines = []
    skip_historical_block = False
    for line in readme.splitlines():
        if line.startswith("### "):
            skip_historical_block = line.startswith(historical_current)
        if not skip_historical_block:
            normalized_lines.append(line)
    readme = "\n".join(normalized_lines).rstrip() + "\n"
    if readme.count(CURRENT_MARKER) != 1:
        raise RuntimeError("Android README must contain exactly one current release heading.")
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

