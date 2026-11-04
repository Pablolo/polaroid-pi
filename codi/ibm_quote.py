import asyncio
from bleak import BleakClient
from PIL import Image, ImageDraw, ImageFont

MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"

# CRC8 del protocol Tiny Print
def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

def paquet(cmd, dades=b""):
    n = len(dades)
    return (
        bytes([0x51, 0x78, cmd, 0x00])
        + n.to_bytes(2, "little")
        + dades
        + bytes([crc8(dades), 0xFF])
    )

# 1. CAMBIO: Aumentamos el alto de la imagen de 90 a 250 píxeles para que quepa todo el texto
imatge = Image.new("1", (384, 250), 1)
draw = ImageDraw.Draw(imatge)

# 2. CAMBIO: Reducimos un poco el tamaño de la letra (de 27 a 20) para que entren más palabras por línea
font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    20
)

# 3. CAMBIO: Definimos el texto largo usando "\n" para indicarle dónde saltar de línea
texto_largo = (
    "I think there is a\n"
    "world market for\n"
    "maybe five computers.\n\n"
    "- Tom Watson,\n"
    "President of IBM, 1943"
)

# 4. CAMBIO: Usamos "multiline_text" en lugar de "text" para que respete los saltos de línea
draw.multiline_text((20, 20), texto_largo, font=font, fill=0, spacing=4)

# Convertir cada fila en 48 bytes
def convertir_fila(y):
    dades = bytearray(48)

    for x in range(384):
        if imatge.getpixel((x, y)) == 0:
            dades[x // 8] |= 1 << (x % 8)

    return bytes(dades)

async def main():
    async with BleakClient(MAC, timeout=20) as client:
        print("Connectat:", client.is_connected)

        async def enviar(cmd, dades):
            await client.write_gatt_char(
                AE01,
                paquet(cmd, dades),
                response=False
            )
            await asyncio.sleep(0.04)

        # Configurar el mode text
        await enviar(0xBE, b"\x01")

        # Imprimir les files de la imatge
        for y in range(imatge.height):
            await enviar(0xA2, convertir_fila(y))

        # Avançar una mica el paper
        await enviar(0xA1, bytes([40, 0]))

        print("Ordres d'impressió enviades")

asyncio.run(main())
