import asyncio
from bleak import BleakClient
from PIL import Image

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
# PROCESAMIENTO DE LA IMAGEN LOCAL
# =====================================================================
# 1. Abre la foto (Cambia "foto_jobs_gates.png" por la ruta de tu archivo)
imagen_original = Image.open("foto_jobs_gates.png")

# 2. Calculamos la proporción para que el ancho se ajuste exactamente a 384 píxeles
ancho_fijo = 384
alto_proporcional = int((imagen_original.height * ancho_fijo) / imagen_original.width)

# 3. Redimensionamos la imagen
imagen_redimensionada = imagen_original.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

# 4. Convertimos a 1 bit (Blanco y Negro puro) aplicando Dithering para que se distingan las sombras
imatge = imagen_redimensionada.convert("1")
# =====================================================================

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

        # Configurar el modo texto/datos
        await enviar(0xBE, b"\x01")

        # Imprimir las filas de la imagen procesada
        print(f"Imprimiendo imagen de {imatge.height} líneas de alto...")
        for y in range(imatge.height):
            await enviar(0xA2, convertir_fila(y))

        # Avanzar el papel para poder cortarlo libremente
        await enviar(0xA1, bytes([40, 0]))

        print("Órdenes de impresión enviadas con éxito")

asyncio.run(main())
