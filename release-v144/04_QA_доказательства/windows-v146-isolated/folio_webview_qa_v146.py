from pathlib import Path
import sys

ROOT = Path(r"C:\Users\Windows-10\Desktop\Портфолио_веб-разработчика")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desktop_webview import run_app

if __name__ == "__main__":
    run_app(
        profile_dir=Path(r"C:\Users\Windows-10\AppData\Local\Temp\folio-webview-v146-qa-profile"),
        port=41946,
    )
