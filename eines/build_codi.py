"""Genera codi.html i la llista d'enllaços de codi d'index.html a partir de codi/*.py.
Per afegir un script nou: posa'l a codi/ i afegeix-lo a GRUPS amb la seva descripció."""
import os, re, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRUPS = [
  ("Bluetooth i impressora", [
    ("prova_ble.py", "23/10", "Es connecta a la impressora i llista tots els seus serveis i característiques BLE."),
    ("prova_ble_lectura_test_1.py", "23/10", "Llegeix les dades internes de la característica ae10."),
    ("hola_print_test.py", "23/10", "La primera impressió que va funcionar: dibuixa «HOLA RASPBERRY» i l'envia fila a fila."),
    ("prova_estat_impresora.py", "26/10", "Demana l'estat a la impressora (ordre A3) i mostra la resposta."),
    ("ibm_quote.py", "26/10", "Prova d'impressió de text llarg en diverses línies."),
    ("gates_jobs_image_print.py", "26/10", "Primera prova d'imprimir una imatge des d'un fitxer."),
    ("print_jpg.py", "26/10", "Imprimeix un JPG de l'ordinador amb més contrast."),
  ]),
  ("Càmera", [
    ("tomar_foto.py", "26/10", "Fa una foto amb la Pi Camera fent servir rpicam-still."),
    ("camara_instantanea.py", "26/10", "Fa la foto i la imprimeix al moment."),
    ("camara_instantanea_pro.py", "26/10", "Comprova abans que la impressora estigui encesa i amb paper."),
    ("camara_instantanea_vertical.py", "26/10", "Imprimeix la foto en vertical, més gran i nítida."),
    ("camara_instantanea_final.py", "27/10", "Guarda cada foto a ~/MisFotosPolaroid amb la data i l'hora al nom."),
  ]),
  ("Telegram i botons", [
    ("camara_instantanea_telegram.py", "27/10", "Envia la foto en color per Telegram mentre s'imprimeix."),
    ("test_boto.py", "27/10", "Prova el botó de foto connectat a GPIO17."),
    ("camara_instantanea_telegram_boton.py", "27/10", "Fa una foto cada vegada que es prem el botó, en bucle infinit."),
    ("camera_boto_apagat.py", "27/10", "Afegeix el botó d'apagada a GPIO3 (3 segons premut)."),
    ("camera_pi_v1.py", "29/10", "Còpia de la versió amb els dos botons."),
  ]),
  ("Programa principal", [
    ("polaroid_pi_v1.py", "29/10", "Primera versió que arrenca sola amb systemd."),
    ("polaroid_pi_v2.py", "29/10", "Menys contrast, més brillantor i tramat Floyd–Steinberg."),
    ("test_enfoque.py", "29/10", "Només envia la foto per Telegram, per ajustar l'enfocament."),
    ("polaroid_pi_v3.py", "30/10", "Envia la foto per Telegram encara que la impressora no funcioni."),
  ]),
]
FALTEN = ["test_impresora_v1.py", "test_impresora_v2.py", "extraer_exacto.py", "rodillo.py"]

def slug(n): return 'f-' + re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
def dia(d): a, b = d.split('/'); return f"index.html#dia-{a}-{b}"

files = set(f for f in os.listdir(os.path.join(ROOT, 'codi')) if f.endswith('.py'))
llistats = {n for _, g in GRUPS for n, _, _ in g}
for f in sorted(files - llistats): GRUPS[-1][1].append((f, "", "Script del projecte."))

toc, body = [], []
for titol, items in GRUPS:
    items = [i for i in items if i[0] in files]
    toc.append(f'<div class="toc-group"><h3>{titol}</h3><ul>' + ''.join(
        f'<li><a href="#{slug(n)}"><code>{n}</code></a></li>' for n, _, _ in items) + '</ul></div>')
    body.append(f'<h2 class="group">{titol}</h2>')
    for n, d, desc in items:
        src = open(os.path.join(ROOT, 'codi', n), encoding='utf-8').read()
        lines = src.count('\n') + 1
        meta = f'<a href="{dia(d)}">Diari {d}</a> · ' if d else ''
        body.append(f'''<article class="file" id="{slug(n)}">
  <header><h3><code>{n}</code></h3>
  <p class="desc">{html.escape(desc)}</p>
  <p class="meta">{meta}{lines} línies · <a href="codi/{n}" download>Descarregar</a></p></header>
  <pre><code class="language-python">{html.escape(src)}</code></pre>
</article>''')

page = open(os.path.join(ROOT, 'eines', 'codi_plantilla.html'), encoding='utf-8').read()
page = page.replace('<!--TOC-->', '\n'.join(toc)).replace('<!--FITXERS-->', '\n'.join(body))
page = page.replace('<!--N-->', str(len(files)))
page = page.replace('<!--FALTEN-->', ', '.join(f'<code>{f}</code>' for f in FALTEN))
open(os.path.join(ROOT, 'codi.html'), 'w', encoding='utf-8').write(page)

# Llista d'enllaços a la portada
home = ['<section id="codi">', '    <div class="sec-head">', '      <p class="label">Codi</p>',
        f'      <h2>Tots els scripts</h2>',
        f'      <p>Els {len(files)} programes en Python del projecte, en l\'ordre en què els vam fer. Cada un s\'obre a la <a href="codi.html">pàgina de codi</a>.</p>',
        '    </div>', '    <div class="code-index">']
for titol, items in GRUPS:
    items = [i for i in items if i[0] in files]
    home.append(f'      <div><h3>{titol}</h3><ul>' + ''.join(
        f'<li><a class="code-link" href="codi.html#{slug(n)}"><code>{n}</code></a></li>' for n, _, _ in items) + '</ul></div>')
home += ['    </div>', '  </section>']
p = os.path.join(ROOT, 'index.html'); s = open(p, encoding='utf-8').read()
block = '<!-- CODI:INICI -->\n  ' + '\n'.join(home) + '\n  <!-- CODI:FI -->'
if '<!-- CODI:INICI -->' in s:
    a = s.index('<!-- CODI:INICI -->'); b = s.index('<!-- CODI:FI -->') + len('<!-- CODI:FI -->')
    s = s[:a] + block + s[b:]
else:
    s = s.replace('  <section id="licions">', '  ' + block + '\n\n  <section id="licions">', 1)
open(p, 'w', encoding='utf-8').write(s)
print('codi.html:', len(files), 'fitxers')
