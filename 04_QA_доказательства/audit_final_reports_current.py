from __future__ import annotations
import hashlib, json, re
from difflib import SequenceMatcher
from pathlib import Path
from docx import Document
from pypdf import PdfReader

pkg=Path(__file__).resolve().parents[1]
root=pkg.parent
reports=pkg/'01_Отчёты'
qa=pkg/'04_QA_доказательства'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def read_doc(p:Path)->str:
 d=Document(p)
 out=[x.text for x in d.paragraphs]
 for t in d.tables:
  for row in t.rows: out.extend(c.text for c in row.cells)
 return '\n'.join(out)
def norm(t:str)->str:return re.sub(r'\s+',' ',t).strip()
def inspect(n:int)->dict:
 d=reports/f'Отчёт_ООП_Модуль_{n}.docx'; p=reports/f'Отчёт_ООП_Модуль_{n}.pdf'
 doc=read_doc(d); pages=[x.extract_text() or '' for x in PdfReader(p).pages]
 return {'docx':d.name,'pdf':p.name,'docx_sha256':sha(d),'pdf_sha256':sha(p),'docx_chars':len(doc),'pdf_pages':len(pages),'pdf_pages_with_text':sum(bool(re.sub(r'\s','',x)) for x in pages),'pdf_text_extract_ok':bool(pages) and all(bool(re.sub(r'\s','',x)) for x in pages),'doc_text':doc,'pdf_text':'\n'.join(pages)}
m4=inspect(4); m5=inspect(5)
checks={}
needles=['Контрольный срез на 01.11.2026','настольная версия v87, веб/PWA v74','Python/SQLite 55/55 и web core 21/21','HTTPS или localhost','обычном HTTP-доступе','галерею до восьми изображений','Облака, автосинхронизации и публичной публикации нет.','MDN Web Docs. Secure contexts.']
for i,n in enumerate(needles,1):
 checks[f'module5_content_{i}_docx']=norm(n) in norm(m5['doc_text']); checks[f'module5_content_{i}_pdf']=norm(n) in norm(m5['pdf_text'])
root_sync={}
for n in (4,5):
 for ext in ('docx','pdf'):
  rp=root/f'Отчет_ООП_Модуль_{n}.{ext}'; pp=reports/f'Отчёт_ООП_Модуль_{n}.{ext}'
  root_sync[f'module{n}_{ext}']=rp.is_file() and sha(rp)==sha(pp)
pdfnorm=norm(m5['pdf_text']); docnorm=norm(m5['doc_text'])
text_similarity=SequenceMatcher(None,docnorm,pdfnorm).ratio()
module4_similarity=SequenceMatcher(None,norm(m4['doc_text']),norm(m4['pdf_text'])).ratio()
render_dir=qa/'module5-v74-report-refresh-final'
renders=sorted(render_dir.glob('page-*.png'))
render_dir_m4=qa/'current-report-render-m4'
renders_m4=sorted(render_dir_m4.glob('page-*.png'))
python_log=(qa/'python-regression-package.log').read_text(encoding='utf-8',errors='replace')
web_log=(qa/'web-regression-package.log').read_text(encoding='utf-8',errors='replace')
reg={'python_58_of_58':bool(re.search(r'Ran 58 tests\b',python_log) and re.search(r'\bOK\b',python_log)),'web_21_of_21':all(x in web_log for x in ('ℹ tests 21','ℹ pass 21','ℹ fail 0'))}
result={'date':'2026-11-01','scope':'current submission reports 4 and 5; report snapshot desktop v87 / web-PWA v74; current product desktop v91 / web-PWA v83','module4':{k:v for k,v in m4.items() if k not in ('doc_text','pdf_text')},'module5':{k:v for k,v in m5.items() if k not in ('doc_text','pdf_text')},'module4_docx_pdf_normalized_text_similarity':round(module4_similarity,6),'module4_rendered_pages':len(renders_m4),'module4_all_pages_rendered':len(renders_m4)==m4['pdf_pages']==10,'module5_docx_pdf_normalized_text_similarity':round(text_similarity,6),'module5_rendered_pages':len(renders),'module5_all_pages_rendered':len(renders)==m5['pdf_pages']==11,'module5_visual_contact_sheet':(render_dir/'contact-sheet.png').is_file(),'module5_content_checks':checks,'root_package_hash_sync':root_sync,'latest_package_regression':reg,'all_checks_passed':all(checks.values()) and all(root_sync.values()) and all(reg.values()) and m4['pdf_text_extract_ok'] and m5['pdf_text_extract_ok'] and module4_similarity>=.98 and text_similarity>=.98 and len(renders_m4)==m4['pdf_pages']==10 and len(renders)==m5['pdf_pages']==11 and (render_dir/'contact-sheet.png').is_file()}
(qa/'report-current-package-audit-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not result['all_checks_passed']: raise SystemExit('Current report audit failed.')

