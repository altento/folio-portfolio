from __future__ import annotations

import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.name.startswith("qa_"):
    ROOT = SCRIPT_DIR.parents[1]
    WEB = ROOT / "web"
    QA = SCRIPT_DIR
else:
    ROOT = SCRIPT_DIR.parent
    WEB = ROOT / "02_Приложение" / "web"
    QA = SCRIPT_DIR


class QuietHandler(SimpleHTTPRequestHandler):
    requests: list[tuple[str, str]] = []

    def do_GET(self):
        self.requests.append(("GET", self.path))
        super().do_GET()

    def do_POST(self):
        self.requests.append(("POST", self.path))
        self.send_error(405)

    def log_message(self, *_args):
        pass


async def select_view(page, view: str, width: int) -> None:
    selector = f".mobile-nav [data-view='{view}']" if width < 821 else f".sidebar .nav-item[data-view='{view}']"
    await page.locator(selector).click()


async def main() -> None:
    demo = json.loads((WEB / "demo.json").read_text(encoding="utf-8"))
    featured_titles = [item["title"] for item in demo["projects"] if item.get("featured") is True]
    hidden_titles = [item["title"] for item in demo["projects"] if item.get("featured") is not True]
    QuietHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result = {"version": "folio-shell-v42-touch-targets", "feature": "pre-export-review-v41", "viewports": [], "errors": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                args=["--no-first-run", "--no-default-browser-check"],
            )
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda message: result["errors"].append(message.text) if message.type == "error" else None)
            await page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle", timeout=20000)
            await page.locator(".project-card").first.wait_for(timeout=10000)

            await select_view(page, "settings", 1440)
            form = page.locator("#profile-form")
            await form.locator('[name="full_name"]').fill("QA Export Reviewer")
            await form.locator('[name="specialization"]').fill("Privacy review")
            await form.locator('[name="introduction"]').fill("Synthetic profile used to verify the export disclosure.")
            await form.locator('[name="email"]').fill("selected-contact@example.invalid")
            await form.locator('[name="include_email"]').check()
            await form.locator('[name="website_url"]').fill("https://unselected-profile-site.invalid")
            await form.locator('[name="include_website"]').uncheck()
            await form.locator('[name="github_url"]').fill("https://unselected-profile-code.invalid")
            await form.locator('[name="include_github"]').uncheck()
            await form.locator('button.button-dark').click()
            await page.get_by_text("Профиль сохранён локально").wait_for(timeout=10000)

            for width, height, label in ((1440, 900, "desktop"), (390, 844, "mobile")):
                await page.set_viewport_size({"width": width, "height": height})
                await select_view(page, "showcase", width)
                await page.locator("[data-action='export-static']").click()
                dialog = page.locator("#showcase-preview-dialog[open]")
                await dialog.wait_for(timeout=10000)
                frame = page.frame_locator("#showcase-preview-frame")
                await frame.locator("h1").wait_for(timeout=10000)
                await page.locator("#showcase-export-summary details summary").click()
                preview_text = await frame.locator("body").inner_text()
                summary_text = await page.locator("#showcase-export-summary").inner_text()
                reviewed_html = await page.locator("#showcase-preview-frame").evaluate("element => element.srcdoc")
                metrics = await page.evaluate("""()=>{
                  const dialog=document.querySelector('#showcase-preview-dialog');
                  const visible=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.visibility!=='hidden'};
                  const controls=[...dialog.querySelectorAll('button,summary')].filter(visible);
                  const name=el=>el.getAttribute('aria-label')||el.innerText.trim();
                  const buttons=[...dialog.querySelectorAll('button')].filter(visible).map(el=>{const r=el.getBoundingClientRect();return {name:name(el),x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),visible:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight,hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.className||document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.tagName}});
                  const rect=el=>{const r=el.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),bottom:Math.round(r.bottom)}};return {open:dialog.open,labelledby:dialog.getAttribute('aria-labelledby'),titleExists:!!document.getElementById(dialog.getAttribute('aria-labelledby')),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,iframeTitle:dialog.querySelector('iframe')?.title,summaryLive:dialog.querySelector('#showcase-export-summary')?.getAttribute('aria-live'),unnamed:controls.filter(el=>!name(el)).map(el=>el.outerHTML.slice(0,100)),buttons,dialogRect:rect(dialog),footerRect:rect(dialog.querySelector('.showcase-preview-actions')),iframeRect:rect(dialog.querySelector('iframe')),mobileNavRect:rect(document.querySelector('.mobile-nav'))};
                }""")
                assert metrics["open"] and metrics["titleExists"], metrics
                assert metrics["documentWidth"] == metrics["viewportWidth"], metrics
                assert metrics["iframeTitle"] and not metrics["unnamed"], metrics
                assert all(button["visible"] and button["height"] >= 44 for button in metrics["buttons"]), metrics
                assert "QA Export Reviewer" in summary_text and "selected-contact@example.invalid" in summary_text, summary_text
                assert "unselected-profile-site.invalid" not in summary_text and "unselected-profile-code.invalid" not in summary_text, summary_text
                assert all(title in summary_text and title in preview_text for title in featured_titles), (summary_text, preview_text)
                assert all(title not in summary_text and title not in preview_text for title in hidden_titles), (summary_text, preview_text)
                assert "Написать на email" in preview_text and "mailto:selected-contact@example.invalid" in reviewed_html, (preview_text, reviewed_html[:1000])
                assert "unselected-profile-site.invalid" not in reviewed_html and "unselected-profile-code.invalid" not in reviewed_html, reviewed_html[:1000]
                screenshot = QA / f"web-export-review-v41-{label}-{width}x{height}.png"
                await page.screenshot(path=str(screenshot), full_page=False)
                async with page.expect_download(timeout=10000) as download_info:
                    await page.locator("#showcase-export-download").click()
                download = await download_info.value
                exported_html = Path(await download.path()).read_text(encoding="utf-8")
                assert download.suggested_filename == "folio-showcase.html"
                assert exported_html == reviewed_html, "Downloaded HTML must be the exact HTML shown in the preview."
                assert "selected-contact@example.invalid" in exported_html
                assert "unselected-profile-site.invalid" not in exported_html and "unselected-profile-code.invalid" not in exported_html
                assert all(title in exported_html for title in featured_titles)
                assert all(title not in exported_html for title in hidden_titles)
                await page.locator("#showcase-preview-dialog").wait_for(state="hidden")
                result["viewports"].append({
                    "label": label, "viewport": {"width": width, "height": height},
                    "summary": metrics, "featured_titles": featured_titles, "excluded_titles": hidden_titles,
                    "selected_contact_included": True, "unchecked_contacts_excluded": True,
                    "download_matches_review": True, "download_filename": download.suggested_filename,
                    "screenshot": screenshot.name,
                })
            result["non_get_requests"] = [item for item in QuietHandler.requests if item[0] != "GET"]
            assert not result["errors"], result["errors"]
            assert not result["non_get_requests"], result["non_get_requests"]
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    output = QA / "web-export-review-v41-results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

