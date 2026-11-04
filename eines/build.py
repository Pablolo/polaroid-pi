"""Genera el diari d'index.html a partir d'eines/diari.txt.
Format de diari.txt:
  @day DD/MM | Dia N | Títol | Títol curt   -> nou dia (el títol curt surt a l'índex de dies)
  @photos ... @end                -> grup de fotos
  @fig classes | fitxer | alt | peu de foto
  {{nom.py}}                      -> enllaç a la pàgina de codi (si el fitxer existeix a codi/)
  [[nom.py]]                      -> el mateix, però sense format de codi (per dins de <pre> i <code>)
  ==text==                        -> subratllat amb retolador (fora dels blocs de codi)
La resta de línies és HTML tal qual.
"""
import os, re, html, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
codi = set(os.listdir(os.path.join(ROOT, 'codi'))) if os.path.isdir(os.path.join(ROOT, 'codi')) else set()

_m = os.path.join(ROOT, 'eines', 'mides_fotos.json')
mides = json.load(open(_m)) if os.path.exists(_m) else {}

def slug(name): return 'f-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def code_link(m):
    n = m.group(1)
    if n in codi:
        return f'<a class="code-link" href="codi.html#{slug(n)}"><code>{n}</code></a>'
    return f'<code title="Aquest fitxer no és a la carpeta Codis">{n}</code>'

def plain_link(m):
    n = m.group(1)
    return f'<a class="code-link-plain" href="codi.html#{slug(n)}">{n}</a>' if n in codi else n

out, open_day, nav, in_pre = [], False, [], False
for line in open(os.path.join(ROOT, 'eines', 'diari.txt'), encoding='utf-8'):
    line = line.rstrip('\n')
    if line.startswith('@day '):
        if open_day: out.append('      </div>\n    </article>\n')
        parts = [s.strip() for s in line[5:].split('|')]
        date, num, title = parts[:3]
        curt = parts[3] if len(parts) > 3 else num
        d, mth = date.split('/')
        nav.append(f'        <li><a href="#dia-{d}-{mth}"><b>{date}</b><span>{html.escape(curt)}</span></a></li>')
        out.append(f'    <article class="day" id="dia-{d}-{mth}">\n      <div class="day-date"><b>{date}</b><span>{num}</span></div>\n      <div class="day-body">\n        <h3>{html.escape(title)}</h3>')
        open_day = True
    elif line == '@photos': out.append('        <div class="photos">')
    elif line == '@end': out.append('        </div>')
    elif line.startswith('@fig'):
        cls, f, alt, cap = [s.strip() for s in line[4:].split('|')]
        c = ' '.join(['pol'] + cls.split())
        w, h = mides.get(f, (700, 700))
        out.append(f'          <figure class="{c}"><button type="button"><img src="img/mini/{f}.webp" data-full="img/{f}.webp" width="{w}" height="{h}" alt="{html.escape(alt)}" loading="lazy" decoding="async"></button><figcaption>{html.escape(cap)}</figcaption></figure>')
    elif line.strip() == '' and not in_pre: continue
    else:
        if '<pre' in line: in_pre = True
        if '</pre>' in line: in_pre = False
        line = re.sub(r'\{\{([\w.\-]+\.py)\}\}', code_link, line)
        line = re.sub(r'\[\[([\w.\-]+\.py)\]\]', plain_link, line)
        if not in_pre and '<pre' not in line:
            line = re.sub(r'==(.+?)==', r'<mark>\1</mark>', line)
        out.append(line)
if open_day: out.append('      </div>\n    </article>')
diari = '\n'.join(out)

p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()
a = s.index('<!-- DIARI:INICI -->') if '<!-- DIARI:INICI -->' in s else s.index('    <!-- ====== 21/10 ====== -->')
b = s.index('<!-- DIARI:FI -->') if '<!-- DIARI:FI -->' in s else s.index('  </section>\n\n  <section id="licions">')
s = s[:a] + '<!-- DIARI:INICI -->\n' + diari + '\n    <!-- DIARI:FI -->\n' + s[b:].replace('<!-- DIARI:FI -->', '', 1)
na = s.index('<!-- NAV:INICI -->') + len('<!-- NAV:INICI -->'); nb = s.index('<!-- NAV:FI -->')
s = s[:na] + '\n      <p class="label">Dies</p>\n      <ol>\n' + '\n'.join(nav) + '\n      </ol>\n' + s[nb:]
open(p, 'w', encoding='utf-8').write(s)
print('diari generat:', diari.count('<article'), 'dies,', diari.count('<figure'), 'fotos')
