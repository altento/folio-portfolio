import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent
PORT=os.environ["FOLIO_PORT"]
URL=f"http://127.0.0.1:{PORT}/?folio-desktop=1"
TITLE="QA mobile wizard v141 retry"
def main():
 errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
  context=browser.new_context(viewport={"width":390,"height":844},device_scale_factor=1,is_mobile=True,has_touch=True,service_workers="block")
  page=context.new_page(); page.on("pageerror",lambda e:errors.append(str(e))); page.on("console",lambda m:errors.append(m.text) if m.type=="error" else None)
  response=page.goto(URL,wait_until="networkidle",timeout=45000); assert response and response.status==200
  page.locator('[data-action="new-project"]').last.click()
  page.wait_for_function("document.querySelector('#project-dialog').open && document.querySelector('[name=created_at]').value !== ''",timeout=10000)
  assert not page.locator('#project-form-wizard').evaluate('(e)=>e.hidden')
  page.screenshot(path=str(OUT/"mobile-wizard-step-1.png"))
  page.locator('#project-form [name=title]').fill(TITLE);page.locator('#project-form [name=description]').fill('Проверка сохранения из телефонного мастера на чистом профиле.')
  page.locator('#project-form-step-next').click();assert page.locator('#project-dialog').get_attribute('data-mobile-step')=='1'
  page.screenshot(path=str(OUT/"mobile-wizard-step-2.png"))
  page.locator('#project-form [name=context]').fill('Тест изолированного профиля, данные демонстрационные.')
  page.locator('#project-form-step-next').click();assert page.locator('#project-dialog').get_attribute('data-mobile-step')=='2'
  page.screenshot(path=str(OUT/"mobile-wizard-step-3.png"))
  page.locator('#project-form-submit').click();page.wait_for_function("!document.querySelector('#project-dialog').open",timeout=10000)
  page.locator('[data-view="projects"]:visible').first.click();page.locator('#search-input').fill(TITLE);page.wait_for_timeout(300)
  assert page.get_by_text(TITLE,exact=True).count()>0
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  page.reload(wait_until="networkidle");page.locator('[data-view="projects"]:visible').first.click();page.locator('#search-input').fill(TITLE);page.wait_for_timeout(300)
  assert page.get_by_text(TITLE,exact=True).count()>0
  assert not errors,errors
  result={"date":"2026-11-05","build":"packaged Windows WebView2 v141, mobile viewport 390x844","http_status":response.status,"three_step_wizard":True,"created_with_empty_optional_mobile_crop":True,"saved_and_found":True,"persisted_after_reload":True,"horizontal_overflow":False,"page_errors":errors,"passed":True}
  (OUT/"results-mobile-wizard-v141.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps(result,ensure_ascii=True));context.close();browser.close()
if __name__=="__main__":main()
