from __future__ import annotations

import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
QA = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


async def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    source_files = [WEB / name for name in (
        "index.html", "styles.css", "app.js", "core.js", "sw.js",
        "manifest.webmanifest", "offline.html",
    )]
    source_refs = [
        path.name for path in source_files
        if "kaspersky-labs.com" in path.read_text(encoding="utf-8").lower()
    ]
    result = {
        "date": "2026-10-29",
        "version": "folio-shell-v38-showcase-themes",
        "test_origin": origin,
        "source_files_checked": [path.name for path in source_files],
        "source_files_with_kaspersky_reference": source_refs,
        "requests": [],
        "external_responses": [],
        "failed_requests": [],
        "console_errors": [],
        "page_errors": [],
    }
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROME),
                args=["--no-first-run", "--no-default-browser-check"],
            )
            context = await browser.new_context(service_workers="allow")
            page = await context.new_page()

            def record_request(request) -> None:
                result["requests"].append({
                    "url": without_query(request.url),
                    "method": request.method,
                    "resource_type": request.resource_type,
                })

            def record_response(response) -> None:
                if "kaspersky" in response.url.lower():
                    result["external_responses"].append({
                        "url": without_query(response.url),
                        "status": response.status,
                        "content_type": response.headers.get("content-type", ""),
                    })

            def record_failure(request) -> None:
                if "kaspersky" in request.url.lower():
                    result["failed_requests"].append({
                        "url": without_query(request.url),
                        "failure": request.failure,
                    })

            page.on("request", record_request)
            page.on("response", record_response)
            page.on("requestfailed", record_failure)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type == "error" else None)

            await page.goto(origin + "/", wait_until="networkidle", timeout=20000)
            result["dom_scripts"] = await page.locator("script").evaluate_all(
                "items => items.map(script => script.src ? new URL(script.src).origin + new URL(script.src).pathname : '[inline]')"
            )
            result["injected_kaspersky_script_not_in_source"] = (
                not result["source_files_with_kaspersky_reference"]
                and any("kaspersky" in script.lower() for script in result["dom_scripts"])
            )
            result["external_requests"] = [
                request for request in result["requests"]
                if not request["url"].startswith(origin + "/")
            ]
            result["external_hosts"] = sorted({
                urlsplit(request["url"]).netloc for request in result["external_requests"]
            })
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    output = QA / "browser-external-injection-audit-v38-2026-10-29.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "version": result["version"],
        "source_files_with_kaspersky_reference": result["source_files_with_kaspersky_reference"],
        "injected_kaspersky_script_not_in_source": result["injected_kaspersky_script_not_in_source"],
        "external_hosts": result["external_hosts"],
        "external_responses": result["external_responses"],
        "failed_requests": result["failed_requests"],
        "console_errors": result["console_errors"],
        "page_errors": result["page_errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
