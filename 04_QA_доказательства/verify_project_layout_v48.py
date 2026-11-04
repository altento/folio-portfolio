from __future__ import annotations
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'web'
QA = Path(__file__).resolve().parent

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)
    def log_message(self, *_args):
        pass

def require(condition, message):
    if not condition:
        raise AssertionError(message)

server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{server.server_port}/'
result = {'date':'2026-10-30','version':'folio-shell-v48-compact-sort-labels','errors':[],'viewports':[],'screenshots':[]}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
        context = browser.new_context(viewport={'width':1440,'height':900}, reduced_motion='reduce')
        page = context.new_page()
        page.on('pageerror', lambda error: result['errors'].append(str(error)))
        page.on('console', lambda message: result['errors'].append(message.text) if message.type == 'error' else None)
        page.goto(base, wait_until='networkidle')
        page.locator('.nav-item[data-view="projects"]').click()
        page.locator('.view-toggle').wait_for()
        require(page.locator('.project-card').count() == 3, 'Expected three demo cards in the isolated profile.')
        require(page.locator('[data-layout-choice="cards"]').get_attribute('aria-pressed') == 'true', 'Cards must be the safe default.')
        initial_data = page.evaluate('''async () => {
          const db = await new Promise((resolve, reject) => { const r = indexedDB.open('folio-workspace'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
          const record = await new Promise((resolve, reject) => { const r = db.transaction('records').objectStore('records').get('portfolio'); r.onsuccess = () => resolve(r.result?.value); r.onerror = () => reject(r.error); });
          db.close(); return JSON.stringify(record);
        }''')
        require(bool(initial_data), 'Expected an isolated IndexedDB demo record.')
        page.screenshot(path=str(QA/'web-layout-v48-cards-1440x900.png'), full_page=True)
        result['screenshots'].append('web-layout-v48-cards-1440x900.png')
        page.locator('[data-layout-choice="list"]').click()
        require('project-list' in (page.locator('.project-grid').get_attribute('class') or ''), 'List mode class was not applied.')
        require(page.locator('[data-layout-choice="list"]').get_attribute('aria-pressed') == 'true', 'List mode must expose pressed state.')
        require(page.evaluate('document.activeElement.dataset.layoutChoice') == 'list', 'Focus must return to the selected layout button.')
        page.screenshot(path=str(QA/'web-layout-v48-list-desktop-1440x900.png'), full_page=True)
        result['screenshots'].append('web-layout-v48-list-desktop-1440x900.png')
        page.locator('#search-input').fill('CRM')
        page.wait_for_function("document.querySelectorAll('.project-card').length === 1")
        require('project-list' in (page.locator('.project-grid').get_attribute('class') or ''), 'Search rerender lost list mode.')
        require(page.locator('#search-input').input_value() == 'CRM', 'Search rerender lost the query.')
        page.locator('[data-layout-choice="cards"]').click()
        require(page.locator('.project-card').count() == 1, 'Switching layout changed filtered results.')
        require(page.locator('#search-input').input_value() == 'CRM', 'Switching layout must preserve search.')
        require(page.locator('[data-layout-choice="cards"]').get_attribute('aria-pressed') == 'true', 'Cards mode must expose pressed state.')
        page.locator('#search-input').fill('')
        page.wait_for_function("document.querySelectorAll('.project-card').length === 3")
        # Exercise the same choice through native keyboard activation: Tab from Cards to List, then Space.
        page.locator('[data-layout-choice="cards"]').focus()
        page.keyboard.press('Tab')
        require(page.evaluate('document.activeElement.dataset.layoutChoice') == 'list', 'Tab must reach the List layout control.')
        page.keyboard.press('Space')
        require(page.locator('[data-layout-choice="list"]').get_attribute('aria-pressed') == 'true', 'Space must activate List mode.')
        page.reload(wait_until='networkidle')
        page.locator('.nav-item[data-view="projects"]').click()
        require(page.locator('[data-layout-choice="list"]').get_attribute('aria-pressed') == 'true', 'Layout preference did not survive reload.')
        after_data = page.evaluate('''async () => {
          const db = await new Promise((resolve, reject) => { const r = indexedDB.open('folio-workspace'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
          const record = await new Promise((resolve, reject) => { const r = db.transaction('records').objectStore('records').get('portfolio'); r.onsuccess = () => resolve(r.result?.value); r.onerror = () => reject(r.error); });
          db.close(); return JSON.stringify(record);
        }''')
        require(initial_data == after_data, 'Changing the layout must not mutate portfolio IndexedDB data.')
        for width, height in [(1440,900),(390,844),(320,568)]:
            page.set_viewport_size({'width':width,'height':height})
            page.evaluate('window.scrollTo(0,0)')
            dims = page.evaluate('''() => ({
              viewport: innerWidth, document: document.documentElement.scrollWidth,
              cards: document.querySelectorAll('.project-card').length, sortLabel: document.querySelector('#sort-projects option:checked')?.textContent?.trim(), sortName: document.querySelector('#sort-projects')?.getAttribute('aria-label'),
              toggles: [...document.querySelectorAll('[data-layout-choice]')].map(b => {const r=b.getBoundingClientRect(); return {name:b.dataset.layoutChoice,width:Math.round(r.width),height:Math.round(r.height),pressed:b.getAttribute('aria-pressed')}})
            })''')
            require(dims['document'] == width, f'Horizontal overflow at {width}: {dims}')
            if width == 320: require(len(dims['sortLabel']) <= 12 and dims['sortName'] == 'Сортировка проектов', f'Sort label is not compact and accessible: {dims}')
            require(len(dims['toggles']) == 2 and min(x['height'] for x in dims['toggles']) >= 44, f'Layout controls are not touch-sized at {width}: {dims}')
            result['viewports'].append({'width':width,'height':height,'layout':'list','document_width':dims['document'],'cards':dims['cards'],'controls':dims['toggles'],'sort_label':dims['sortLabel'],'sort_accessible_name':dims['sortName']})
            if width in (390,320):
                name=f'web-layout-v48-list-{width}x{height}.png'
                page.screenshot(path=str(QA/name), full_page=True)
                result['screenshots'].append(name)
                if width == 320: page.screenshot(path=str(QA/'web-layout-v48-list-320-viewport.png'), full_page=False); result['screenshots'].append('web-layout-v48-list-320-viewport.png')
            page.locator('[data-layout-choice="cards"]').click()
            cards_dims=page.evaluate('''() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,cardCount:document.querySelectorAll('.project-card').length})''')
            require(cards_dims['document']==width, f'Cards mode overflows at {width}: {cards_dims}')
            if width in (390,320):
                name=f'web-layout-v48-cards-{width}x{height}.png'
                page.screenshot(path=str(QA/name), full_page=True)
                result['screenshots'].append(name)
                if width == 320: page.screenshot(path=str(QA/'web-layout-v48-cards-320-viewport.png'), full_page=False); result['screenshots'].append('web-layout-v48-cards-320-viewport.png')
            page.locator('[data-layout-choice="list"]').click()
        require(not result['errors'], f'Browser errors: {result["errors"]}')
        result['indexeddb_unchanged']=True
        result['keyboard_activation_passed']=True
        result['preference_survives_reload']=True
        result['errors']=[]
        (QA/'web-layout-v48-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print(json.dumps(result,ensure_ascii=False,indent=2))




