import asyncio
from bleak import BleakClient
from PIL import Image, ImageEnhance, ImageOps

MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"

# CRC8 del protocolo Tiny Print
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

# =====================================================================
# PROCESAMIENTO OPTIMIZADO PARA LA IMAGEN DEL EXPERIMENTO
# =====================================================================
# 1. Abre la foto corrigiendo la orientación si es un JPG de móvil
imagen_original = ImageOps.exif_transpose(Image.open("experimento.jpg"))

# 2. Reescalado automático manteniendo la proporción vertical
ancho_fijo = 384
alto_proporcional = int((imagen_original.height * ancho_fijo) / imagen_original.width)
imagen_redimensionada = imagen_original.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

# 3. FILTRO EXTRA: Subimos el contraste para resaltar
potenciador = ImageEnhance.Contrast(imagen_redimensionada)
imagen_contrastada = potenciador.enhance(1.5)  # 1.5 aumenta el contraste un 50%

# 4. Convertimos a 1 bit con entramado (Dithering)
imatge = imagen_contrastada.convert("1")
# =====================================================================

def convertir_fila(y):
    dades = bytearray(48)
    for x in range(384):
        if imatge.getpixel((x, y)) == 0:
            dades[x // 8] |= 1 << (x % 8)
    return bytes(dades)

async def main():
    async with BleakClient(MAC, timeout=20) as client:
        print("Conectado:", client.is_connected)

        async def enviar(cmd, dades):
            await client.write_gatt_char(AE01, paquet(cmd, dades), response=False)
            await asyncio.sleep(0.04)

        await enviar(0xBE, b"\x01")

        print(f"Imprimiendo foto del experimento ({imatge.height} líneas)...")
        for y in range(imatge.height):
            await enviar(0xA2, convertir_fila(y))

        # Avanza suficiente papel para que no se quede la foto dentro de la tapa
        await enviar(0xA1, bytes())
        print("¡Impresión finalizada!")

asyncio.run(main())
