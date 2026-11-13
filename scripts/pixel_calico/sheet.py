import sys
from PIL import Image
d = sys.argv[1]; bgc = (255, 255, 255)
names = ['front', 'three_quarter', 'side', 'back']
tiles = [Image.open(f'{d}/sheet/{n}.png').convert('RGBA') for n in names]
w, h = tiles[0].size; S = Image.new('RGBA', (w * 4, h), bgc + (255,))
for i, t in enumerate(tiles): S.alpha_composite(t, (i * w, 0))
S.convert('RGB').save(f'{d}/contact-sheet.png')
