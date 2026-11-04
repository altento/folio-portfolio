from pathlib import Path
from PIL import Image, ImageDraw
qa = Path(__file__).resolve().parent
labels = ['dashboard', 'projects', 'showcase', 'settings', 'detail', 'form']
for device, size, cols, rows in [('desktop',(480,320),3,2),('mobile',(210,390),3,2)]:
    card_w, card_h = size
    sheet = Image.new('RGB',(card_w*cols,card_h*rows),'#dfe4e8')
    for i,label in enumerate(labels):
        path = qa/f'web-a11y-v43-{label}-{device}.png'
        image = Image.open(path).convert('RGB')
        image.thumbnail((card_w-16,card_h-34))
        card = Image.new('RGB',(card_w,card_h),'#f5f5f5')
        card.paste(image,((card_w-image.width)//2,28))
        ImageDraw.Draw(card).text((10,8),f'{label} · {device}',fill='#192531')
        sheet.paste(card,((i%cols)*card_w,(i//cols)*card_h))
    output=qa/f'web-a11y-v43-{device}-contact-sheet.png'
    sheet.save(output)
    print(output.name,output.stat().st_size)
