"""Extreu les fotos dels .docx del diari (exportats de Google Docs) i en fa dues versions WebP:
  img/<dia>-<n>.webp       1400 px  (es veu en ampliar la foto)
  img/mini/<dia>-<n>.webp   700 px  (es veu a la pàgina)
Ús: python3 eines/extreure_fotos.py carpeta_amb_docx/    (fitxers anomenats MM-DD.docx)
Aplica la rotació EXIF i també el gir que Google Docs guarda a part (a:xfrm rot)."""
import zipfile, sys, os, io, json
from xml.etree import ElementTree as ET
from PIL import Image, ImageOps
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1]
OUT = os.path.join(ROOT, 'img'); MINI = os.path.join(OUT, 'mini')
os.makedirs(MINI, exist_ok=True)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
mides = {}
for fn in sorted(f for f in os.listdir(SRC) if f.endswith('.docx')):
    day = fn[:-5]; z = zipfile.ZipFile(os.path.join(SRC, fn))
    rmap = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
    doc = ET.fromstring(z.read('word/document.xml')); n = 0
    for dr in doc.iter('{%s}drawing' % ns['w']):
        b = next(dr.iter('{%s}blip' % ns['a']), None)
        if b is None: continue
        xf = next(dr.iter('{%s}xfrm' % ns['a']), None)
        rot = int(xf.get('rot', '0')) / 60000 if xf is not None else 0
        n += 1; name = f'{day}-{n:02d}'
        im = Image.open(io.BytesIO(z.read('word/' + rmap[b.get('{%s}embed' % ns['r'])])))
        im = ImageOps.exif_transpose(im).convert('RGB')
        if rot: im = im.rotate(-rot, expand=True)   # DrawingML gira en sentit horari
        gran = im.copy(); gran.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        gran.save(os.path.join(OUT, name + '.webp'), 'WEBP', quality=82, method=6)
        mini = im.copy(); mini.thumbnail((700, 700), Image.Resampling.LANCZOS)
        mini.save(os.path.join(MINI, name + '.webp'), 'WEBP', quality=80, method=6)
        mides[name] = list(mini.size)
json.dump(mides, open(os.path.join(ROOT, 'eines', 'mides_fotos.json'), 'w'), indent=0)
print(len(mides), 'fotos')
