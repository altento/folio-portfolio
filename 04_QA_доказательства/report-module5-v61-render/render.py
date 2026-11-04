from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw
root=Path(r"C:\Users\Windows-10\Desktop\Портфолио_веб-разработчика")
pdf=root/'Пакет_сдачи_портфолио_модули_4_5_на_проверку'/'01_Отчёты'/'Отчёт_ООП_Модуль_5.pdf'
out=root/'служебные_файлы'/'qa_31-10-2026'/'report-module5-v61-render'
doc=pdfium.PdfDocument(pdf)
thumbs=[]
for i,page in enumerate(doc):
    img=page.render(scale=1.45).to_pil().convert('RGB')
    img.save(out/f'page-{i+1:02d}.png')
    thumb=img.copy(); thumb.thumbnail((320,460)); canvas=Image.new('RGB',(340,490),'#ddd'); canvas.paste(thumb,((340-thumb.width)//2,10)); ImageDraw.Draw(canvas).text((12,470),f'Page {i+1}',fill='#111'); thumbs.append(canvas)
cols=4; rows=(len(thumbs)+cols-1)//cols
sheet=Image.new('RGB',(cols*340,rows*490),'#bbb')
for i,t in enumerate(thumbs): sheet.paste(t,((i%cols)*340,(i//cols)*490))
sheet.save(out/'contact-sheet.jpg',quality=90)
print(f'pages={len(doc)}; output={out}')
