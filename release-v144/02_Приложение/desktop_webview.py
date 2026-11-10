"""Windows desktop host for Folio's shared, responsive web interface.

The app is served only on a fixed loopback origin so WebView2 IndexedDB and the
service worker persist across launches. Existing Tk/SQLite data is exposed as a
read-only one-time seed; this module never writes to that legacy database.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import threading

from sqlite_storage import SQLiteStore, SQLiteStoreError


APP_TITLE = "folio — личное портфолио"
DESKTOP_PORT = 41764
LOOPBACK = "127.0.0.1"
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
WEB_ROOT = RESOURCE_ROOT / "web"
STATIC_FILES = {
    "index.html", "styles.css", "app.js", "core.js", "preferences.js", "backup-status.js",
    "native-export.js", "native-startup.js", "demo.json", "manifest.webmanifest",
    "offline.html", "sw.js",
}
STATIC_DIRECTORIES = {"assets", "icons"}
MAX_SEED_BYTES = 64 * 1024 * 1024
RECOVERY_FILENAME = "folio-recovery-v1.json"
DOWNLOADS_KNOWN_FOLDER_ID = "{374DE290-123F-4565-9164-39C4925E467B}"


def default_profile_dir() -> Path:
    """Use the same local app-data directory as the legacy Windows app."""
    local_app_data = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return local_app_data / "Folio"


def _static_request_allowed(path: Path, web_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(web_root.resolve())
    except (OSError, ValueError):
        return False
    if relative == Path("."):
        return True
    first = relative.parts[0]
    if first in STATIC_DIRECTORIES:
        return len(relative.parts) > 1 and not any(part.startswith(".") for part in relative.parts)
    return len(relative.parts) == 1 and first in STATIC_FILES


def _default_downloads_directory(*, registry_module=None, fallback: Path | None = None) -> Path:
    """Resolve Windows' configured Downloads Known Folder, with a home fallback."""
    fallback = fallback or (Path.home() / "Downloads")
    if registry_module is None:
        if os.name != "nt":
            return fallback
        try:
            import winreg as registry_module
        except ImportError:
            return fallback
    try:
        with registry_module.OpenKey(
            registry_module.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            for value_name in (DOWNLOADS_KNOWN_FOLDER_ID, "Downloads"):
                try:
                    configured, _ = registry_module.QueryValueEx(key, value_name)
                    resolved = Path(os.path.expandvars(str(configured))).expanduser()
                    if resolved.is_absolute():
                        return resolved
                except OSError:
                    continue
    except (OSError, TypeError, ValueError):
        pass
    return fallback


def make_request_handler(web_root: Path, data_path: Path, port: int):
    recovery_path = Path(data_path).resolve().parent / RECOVERY_FILENAME

    class FolioRequestHandler(SimpleHTTPRequestHandler):
        server_version = "FolioLocal/1"
        sys_version = ""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_root), **kwargs)

        def _host_is_local(self) -> bool:
            return self.headers.get("Host", "").lower() == f"{LOOPBACK}:{port}"

        def do_GET(self) -> None:
            if not self._host_is_local():
                self.send_error(403)
                return
            request_path = unquote(urlsplit(self.path).path)
            if request_path == "/desktop-seed.json":
                self._send_legacy_seed()
                return
            if request_path == "/desktop-recovery.json":
                self._send_recovery_snapshot()
                return
            super().do_GET()

        def send_head(self):
            translated = Path(self.translate_path(self.path))
            if not self._host_is_local() or not _static_request_allowed(translated, web_root):
                self.send_error(404)
                return None
            return super().send_head()

        def do_HEAD(self) -> None:
            if not self._host_is_local():
                self.send_error(403)
                return
            super().do_HEAD()

        def _send_legacy_seed(self) -> None:
            try:
                payload = SQLiteStore(data_path).load()
                body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            except FileNotFoundError:
                self.send_response(204)
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            except (SQLiteStoreError, OSError, ValueError):
                body = json.dumps({
                    "error": "Старая база портфолио не прошла проверку. Она оставлена без изменений; восстановите данные из JSON-копии.",
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.end_headers()
                self.wfile.write(body)
                return
            if len(body) > MAX_SEED_BYTES:
                body = json.dumps({
                    "error": "Старая база слишком велика для безопасного переноса одним шагом; экспортируйте JSON из прежней версии.",
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(413)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def _send_recovery_snapshot(self) -> None:
            try:
                body = recovery_path.read_bytes()
            except FileNotFoundError:
                self.send_response(204)
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            except OSError:
                body = json.dumps({
                    "error": "Локальную копию восстановления не удалось прочитать.",
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(500)
            else:
                if len(body) > MAX_SEED_BYTES:
                    body = json.dumps({
                        "error": "Локальная копия восстановления превышает допустимый размер.",
                    }, ensure_ascii=False).encode("utf-8")
                    self.send_response(413)
                else:
                    try:
                        snapshot = json.loads(body.decode("utf-8"))
                        valid = (
                            isinstance(snapshot, dict)
                            and snapshot.get("format") == "folio-local-recovery"
                            and snapshot.get("version") == 1
                            and isinstance(snapshot.get("saved_at"), str)
                            and isinstance(snapshot.get("portfolio"), dict)
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        valid = False
                    if not valid:
                        body = json.dumps({
                            "error": "Локальная копия восстановления повреждена. Исходная SQLite-база не загружена.",
                        }, ensure_ascii=False).encode("utf-8")
                        self.send_response(500)
                    else:
                        self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def list_directory(self, path):
            self.send_error(404)
            return None

        def log_message(self, _format, *args):
            return

    return FolioRequestHandler


class DesktopFileApi:
    """Expose local file export and recovery-copy operations to the desktop WebView."""

    def __init__(self, profile_dir: str | Path | None = None):
        self.profile_dir = Path(profile_dir) if profile_dir is not None else default_profile_dir()

    def save_file(self, name: str, content: str, mime_type: str = "application/octet-stream") -> str:
        safe_name = Path(str(name)).name
        if not safe_name or safe_name in {".", ".."}:
            raise ValueError("Некорректное имя файла.")
        if len(str(content).encode("utf-8")) > 64 * 1024 * 1024:
            raise ValueError("Файл превышает допустимый размер 64 МиБ.")
        export_dir = Path(os.environ.get("FOLIO_EXPORT_DIR") or _default_downloads_directory())
        export_dir.mkdir(parents=True, exist_ok=True)
        destination = export_dir / safe_name
        stem, suffix = destination.stem, destination.suffix
        counter = 1
        while destination.exists():
            destination = export_dir / f"{stem} ({counter}){suffix}"
            counter += 1
        destination.write_text(str(content), encoding="utf-8", newline="")
        return str(destination)

    def save_recovery_snapshot(self, content: str) -> dict[str, str]:
        """Atomically persist a private, local recovery copy outside WebView storage."""
        encoded = str(content).encode("utf-8")
        if len(encoded) > MAX_SEED_BYTES:
            raise ValueError("Локальная копия восстановления превышает допустимый размер 64 МиБ.")
        try:
            portfolio = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Локальная копия восстановления содержит некорректный JSON.") from exc
        if (
            not isinstance(portfolio, dict)
            or not isinstance(portfolio.get("title"), str)
            or not isinstance(portfolio.get("developer"), dict)
            or not isinstance(portfolio.get("projects"), list)
            or type(portfolio.get("next_id")) is not int
        ):
            raise ValueError("Структура локальной копии восстановления некорректна.")

        saved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        snapshot = {
            "format": "folio-local-recovery",
            "version": 1,
            "saved_at": saved_at,
            "portfolio": portfolio,
        }
        body = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_SEED_BYTES:
            raise ValueError("Локальная копия восстановления превышает допустимый размер 64 МиБ.")

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        destination = self.profile_dir / RECOVERY_FILENAME
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        return {"saved_at": saved_at}


def create_local_server(web_root: Path = WEB_ROOT, data_path: Path | None = None,
                        port: int = DESKTOP_PORT) -> ThreadingHTTPServer:
    web_root = web_root.resolve()
    if not (web_root / "index.html").is_file():
        raise FileNotFoundError(f"Не найдена веб-версия Folio: {web_root}")
    database = Path(data_path) if data_path is not None else default_profile_dir() / "portfolio_data.sqlite3"
    server = ThreadingHTTPServer((LOOPBACK, port), SimpleHTTPRequestHandler)
    server.RequestHandlerClass = make_request_handler(web_root, database, server.server_port)
    server.daemon_threads = True
    return server


def run_app(profile_dir: Path | None = None, *, port: int = DESKTOP_PORT) -> None:
    try:
        import webview
    except ImportError as error:
        raise RuntimeError("Для новой настольной версии не установлена зависимость pywebview.") from error

    profile = Path(profile_dir) if profile_dir is not None else default_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    webview_data = profile / "WebView2"
    webview_data.mkdir(parents=True, exist_ok=True)
    data_path = profile / "portfolio_data.sqlite3"
    server = create_local_server(data_path=data_path, port=port)
    server_thread = threading.Thread(target=server.serve_forever, name="folio-loopback-server", daemon=True)
    server_thread.start()
    window = None
    try:
        file_api = DesktopFileApi(profile)
        window = webview.create_window(
            APP_TITLE,
            f"http://{LOOPBACK}:{port}/?folio-desktop=1",
            width=1440,
            height=940,
            min_size=(960, 640),
            resizable=True,
            text_select=True,
            js_api=file_api,
        )
        webview.start(gui="edgechromium", private_mode=False, storage_path=str(webview_data))
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Локальное настольное приложение Folio")
    parser.add_argument("--profile-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=DESKTOP_PORT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        run_app(args.profile_dir, port=args.port)
    except OSError as error:
        if getattr(sys, "frozen", False):
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                "Не удалось запустить локальную оболочку Folio. Проверьте, что приложение уже не открыто, и повторите запуск.",
                APP_TITLE,
                0x10,
            )
        else:
            print(f"Folio не запустилось: {error}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        if getattr(sys, "frozen", False):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(error), APP_TITLE, 0x10)
        else:
            print(f"Folio не запустилось: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
