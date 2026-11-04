from pathlib import Path
from PIL import Image, ImageDraw

qa = Path(__file__).resolve().parent
labels = ['dashboard', 'projects', 'showcase', 'settings', 'detail', 'form']
for device, card_size in [('desktop', (480, 330)), ('mobile', (210, 440))]:
    card_w, card_h = card_size
    sheet = Image.new('RGB', (card_w * 3, card_h * 2), '#dfe4e8')
    for index, label in enumerate(labels):
        source = Image.open(qa / f'web-a11y-v46-{label}-{device}.png').convert('RGB')
        source.thumbnail((card_w - 16, card_h - 38), Image.Resampling.LANCZOS)
        card = Image.new('RGB', card_size, '#f7f7f5')
        card.paste(source, ((card_w - source.width) // 2, 30))
        ImageDraw.Draw(card).text((10, 8), f'{label} / {device}', fill='#192531')
        sheet.paste(card, ((index % 3) * card_w, (index // 3) * card_h))
    output = qa / f'web-a11y-v46-{device}-contact-sheet.png'
    sheet.save(output, optimize=True)
    print(f'{output.name}: {output.stat().st_size} bytes')
