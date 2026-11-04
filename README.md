# Polaroid Pi

Càmera instantània portàtil feta amb una Raspberry Pi: fa la foto amb un botó, la imprimeix al moment en paper tèrmic (per Bluetooth Low Energy) i l'envia en color al mòbil per Telegram.

**Projecte IOT CIFO La Violeta 2026** · Autor: **Pablo Olóndriz**

Web: https://pablolo.github.io/polaroid-pi/

## Què hi ha en aquest repositori

| Carpeta / fitxer | Contingut |
|---|---|
| `index.html` | La web del projecte: com funciona, components i el diari de construcció dia a dia |
| `codi.html` | Tots els scripts en Python, amb colors |
| `codi/` | Els 21 scripts `.py` del projecte |
| `img/` | Fotos del diari (`img/` 1400 px, `img/mini/` 700 px, en WebP) |
| `eines/` | Scripts per regenerar la web |

## Fer servir el codi

El token del bot de Telegram i l'ID del xat **no** són al repositori. Per fer funcionar els scripts, substitueix `POSA_AQUI_EL_TOKEN_DEL_BOT` i `POSA_AQUI_EL_TEU_CHAT_ID` pels teus.

## Afegir un dia nou al diari

1. Escriu el dia a `eines/diari.txt` (el format està explicat a `eines/build.py`).
2. Extreu les fotos dels documents `.docx` amb `python3 eines/extreure_fotos.py carpeta_docx/`.
3. Regenera la web:

```bash
python3 eines/build_codi.py
python3 eines/build.py
```
