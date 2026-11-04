from __future__ import annotations

import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
QA = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


async def inspect_origin(page, url: str) -> dict:
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(url, wait_until="networkidle", timeout=20000)
    result = await page.evaluate("""async()=>{
      const notice=document.querySelector('#origin-security-notice');
      const out={origin:location.origin,isSecureContext:window.isSecureContext,
        indexedDBAvailable:!!window.indexedDB,serviceWorkerAvailable:('serviceWorker' in navigator),
        warningVisible:!!notice&&!notice.hidden,warningText:notice?.innerText.trim()||'',
        documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth};
      if(out.serviceWorkerAvailable){
        try{const registration=await navigator.serviceWorker.register('./sw.js');
          out.registration='success'; await registration.unregister();}
        catch(error){out.registrationError=error.name;}
      }else out.registration='api-unavailable';
      return out;
    }""")
    result["browserErrors"] = errors
    return result


async def main() -> None:
    if not CHROME.exists():
        raise RuntimeError(f"Chrome executable not found: {CHROME}")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    results = {"date": "2026-10-30", "purpose": "compare secure loopback and ordinary HTTP LAN-style origin",
               "origins": {}, "screenshots": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME),
                args=["--no-first-run", "--no-default-browser-check", "--host-resolver-rules=MAP folio.test 127.0.0.1"])
            local_context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            local_page = await local_context.new_page()
            results["origins"]["loopback"] = await inspect_origin(local_page, f"http://127.0.0.1:{port}/")
            await local_context.close()

            lan_context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            lan_page = await lan_context.new_page()
            lan_url = f"http://folio.test:{port}/"
            results["origins"]["lan_http_analogue"] = await inspect_origin(lan_page, lan_url)
            desktop_shot = QA / "mobile-http-security-warning-desktop-1440x900.png"
            await lan_page.screenshot(path=str(desktop_shot), full_page=False)
            results["screenshots"].append(desktop_shot.name)

            await lan_page.set_viewport_size({"width": 390, "height": 844})
            mobile = await lan_page.evaluate("""()=>({warningVisible:!document.querySelector('#origin-security-notice').hidden,
              documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,
              serviceWorkerAvailable:('serviceWorker' in navigator),isSecureContext:window.isSecureContext})""")
            results["origins"]["lan_http_analogue"]["mobile"] = mobile
            mobile_shot = QA / "mobile-http-security-warning-390x844.png"
            await lan_page.screenshot(path=str(mobile_shot), full_page=False)
            results["screenshots"].append(mobile_shot.name)
            await lan_context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    local = results["origins"]["loopback"]
    lan = results["origins"]["lan_http_analogue"]
    mobile = lan["mobile"]
    results["confirmed"] = bool(
        local["isSecureContext"] and local["serviceWorkerAvailable"] and local["registration"] == "success"
        and not local["warningVisible"] and local["indexedDBAvailable"]
        and lan["isSecureContext"] is False and not lan["serviceWorkerAvailable"]
        and lan["registration"] == "api-unavailable" and lan["warningVisible"] and lan["indexedDBAvailable"]
        and mobile["warningVisible"] and not mobile["serviceWorkerAvailable"]
        and mobile["documentWidth"] == mobile["viewportWidth"]
        and not local["browserErrors"] and not lan["browserErrors"]
    )
    output = QA / "web-mobile-http-security-context-v58-results.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not results["confirmed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())


