import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent
PORT=os.environ["FOLIO_PORT"]
URL=f"http://127.0.0.1:{PORT}/?folio-desktop=1"
TITLE="QA isolated flow v141 retry"
DESCRIPTION="Synthetic isolated-profile persistence and backup verification."
def main():
 errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
  context=browser.new_context(viewport={"width":1440,"height":1000},service_workers="block",accept_downloads=True)
  page=context.new_page(); page.on("pageerror",lambda e:errors.append(str(e))); page.on("console",lambda m:errors.append(m.text) if m.type=="error" else None)
  response=page.goto(URL,wait_until="networkidle",timeout=45000); assert response and response.status==200
  page.screenshot(path=str(OUT/"01-dashboard.png"),full_page=True)
  page.locator('[data-action="new-project"]').first.click()
  page.wait_for_function("document.querySelector('#project-dialog').open && document.querySelector('[name=created_at]').value !== ''",timeout=10000)
  page.locator('#project-form [name="title"]').fill(TITLE)
  page.locator('#project-form [name="description"]').fill(DESCRIPTION)
  page.locator('#project-form-submit').click(); page.wait_for_function("!document.querySelector('#project-dialog').open",timeout=10000)
  page.locator('[data-view="projects"]').first.click(); page.wait_for_timeout(250)
  search=page.locator('#search-input'); assert search.count()==1; search.fill(TITLE); page.wait_for_timeout(350)
  assert page.get_by_text(TITLE,exact=True).count()>0
  page.screenshot(path=str(OUT/"02-search-result.png"),full_page=True)
  page.locator('[data-detail]').filter(has_text=TITLE).click(timeout=5000); page.locator('#detail-dialog').wait_for(state="visible",timeout=5000)
  page.screenshot(path=str(OUT/"03-case-detail.png"))
  page.locator('#detail-dialog [data-edit]').click(); page.locator('#project-dialog').wait_for(state="visible",timeout=5000)
  assert page.locator('#project-form [name="description"]').input_value()==DESCRIPTION
  edited="Edited in isolated v141 user-flow; survives reload."
  page.locator('#project-form [name="description"]').fill(edited); page.locator('#project-form-submit').click(); page.wait_for_function("!document.querySelector('#project-dialog').open",timeout=10000)
  page.reload(wait_until="networkidle"); page.locator('[data-view="projects"]').first.click(); page.locator('#search-input').fill(TITLE); page.wait_for_timeout(350)
  assert page.get_by_text(TITLE,exact=True).count()>0
  page.locator('[data-detail]').filter(has_text=TITLE).click(timeout=5000); page.locator('#detail-dialog').wait_for(state="visible")
  assert edited in page.locator('#detail-dialog').inner_text()
  page.locator('#detail-dialog [data-close-dialog]').click()
  page.locator('[data-view="settings"]').first.click()
  with page.expect_download(timeout=10000) as info: page.locator('[data-action="export-json"]').click(timeout=5000)
  download=info.value; dest=OUT/"temporary-backup.json"; download.save_as(dest)
  payload=json.loads(dest.read_text(encoding="utf-8")); projects=payload.get("projects",[])
  match=[x for x in projects if x.get("title")==TITLE]
  assert match and match[0].get("description")==edited, {"matches":len(match)}
  dest.unlink()
  page.screenshot(path=str(OUT/"04-backup-settings.png"),full_page=True)
  assert not errors,errors
  result={"date":"2026-11-05","build":"packaged Windows WebView2 v141","http_status":response.status,"isolated_profile":True,"created_and_searched":True,"detail_and_edit":True,"persisted_after_reload":True,"json_backup_downloaded_and_verified":True,"project_count_in_backup":len(projects),"temporary_backup_deleted":not dest.exists(),"page_errors":errors,"passed":True}
  (OUT/"results-user-flow-v141.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps(result,ensure_ascii=True)); context.close(); browser.close()
if __name__=="__main__": main()
