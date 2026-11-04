from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent
URL="http://127.0.0.1:8766/"
def main():
 errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(channel="chrome",headless=True)
  context=browser.new_context(viewport={"width":1440,"height":1000},service_workers="allow")
  page=context.new_page()
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.on("console",lambda msg:errors.append(msg.text) if msg.type=="error" else None)
  response=page.goto(URL,wait_until="networkidle",timeout=30000)
  if response is None or response.status!=200: raise AssertionError("PWA failed to load")
  page.wait_for_timeout(900)
  cache_names=page.evaluate("caches.keys()")
  page.locator('[data-view="showcase"]:visible').first.click()
  page.locator('[data-action="preview-static"]:visible').click()
  page.locator("#showcase-preview-dialog").wait_for(state="visible")
  frame=page.locator("#showcase-preview-frame")
  page.wait_for_function("document.querySelector('#showcase-preview-frame')?.contentDocument?.readyState==='complete'")
  html_before=frame.get_attribute("srcdoc")
  desktop=page.evaluate("""() => ({frameWidth:document.querySelector('#showcase-preview-frame').getBoundingClientRect().width,viewport:document.querySelector('#showcase-preview-frame').contentWindow.innerWidth,document:document.querySelector('#showcase-preview-frame').contentDocument.documentElement.scrollWidth,pressed:document.querySelector('.preview-size-button[data-preview-size=desktop][aria-pressed=true]')!==null})""")
  if desktop["viewport"]<=700 or desktop["document"]>desktop["viewport"] or not desktop["pressed"]: raise AssertionError(f"Bad desktop preview: {desktop}")
  page.screenshot(path=str(OUT/"showcase-preview-v87-desktop-1440.png"))
  mobile_button=page.locator('.preview-size-button[data-preview-size="mobile"]')
  if mobile_button.get_attribute("aria-pressed")!="false": raise AssertionError("Initial mobile pressed state is wrong")
  mobile_button.click()
  page.wait_for_function("document.querySelector('#showcase-preview-frame')?.contentWindow?.innerWidth<=390")
  mobile=page.evaluate("""() => ({frameWidth:document.querySelector('#showcase-preview-frame').getBoundingClientRect().width,viewport:document.querySelector('#showcase-preview-frame').contentWindow.innerWidth,document:document.querySelector('#showcase-preview-frame').contentDocument.documentElement.scrollWidth,pressed:document.querySelector('.preview-size-button[data-preview-size=mobile][aria-pressed=true]')!==null,status:document.querySelector('#showcase-preview-size-status').textContent})""")
  if mobile["viewport"]>390 or mobile["viewport"]<320 or mobile["document"]>mobile["viewport"] or not mobile["pressed"]: raise AssertionError(f"Bad mobile preview: {mobile}")
  if html_before!=frame.get_attribute("srcdoc"): raise AssertionError("Viewport switch mutated the exported HTML")
  page.screenshot(path=str(OUT/"showcase-preview-v87-mobile-390.png"))
  controls=page.evaluate("""() => [...document.querySelectorAll('.preview-size-button')].map(b=>({name:b.innerText.trim(),pressed:b.getAttribute('aria-pressed'),height:b.getBoundingClientRect().height}))""")
  if any(not item["name"] or item["height"]<44 for item in controls): raise AssertionError(f"Bad control: {controls}")
  context.set_offline(True)
  offline_response=page.reload(wait_until="load",timeout=30000)
  if offline_response is None or offline_response.status!=200: raise AssertionError("Cached app did not reload offline")
  page.locator('[data-view="showcase"]:visible').first.click()
  page.locator('[data-action="preview-static"]:visible').click()
  page.locator("#showcase-preview-dialog").wait_for(state="visible")
  page.locator('.preview-size-button[data-preview-size="mobile"]').click()
  page.wait_for_function("document.querySelector('#showcase-preview-frame')?.contentWindow?.innerWidth<=390")
  offline=page.evaluate("""() => ({viewport:document.querySelector('#showcase-preview-frame').contentWindow.innerWidth,document:document.querySelector('#showcase-preview-frame').contentDocument.documentElement.scrollWidth,pressed:document.querySelector('.preview-size-button[data-preview-size=mobile][aria-pressed=true]')!==null,cache:[...performance.getEntriesByType('resource')].map(x=>x.name).filter(x=>!x.startsWith(location.origin))})""")
  if offline["document"]>offline["viewport"] or not offline["pressed"] or offline["cache"]: raise AssertionError(f"Bad offline preview: {offline}")
  if errors: raise AssertionError(f"Browser errors: {errors}")
  result={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"result":"PASS","cache_names":cache_names,"desktop":desktop,"mobile":mobile,"offline":offline,"controls":controls,"preview_html_unchanged":True,"browser_errors":errors,"screenshots":["showcase-preview-v87-desktop-1440.png","showcase-preview-v87-mobile-390.png"]}
  (OUT/"showcase-preview-v87-results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  browser.close()
 print("PASS: desktop/mobile showcase preview, responsive width, accessible state and touch targets, unchanged export HTML, and no browser errors.")
if __name__=="__main__": main()
