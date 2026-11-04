import asyncio
import subprocess
import time
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

def convertir_fila(imatge, y):
    dades = bytearray(48)
    for x in range(384):
        if imatge.getpixel((x, y)) == 0:
            dades[x // 8] |= 1 << (x % 8)
    return bytes(dades)

async def main():
    nombre_archivo = "mi_experimento.jpg"
    print("--------------------------------------------------")
    print("1. CAPTURANDO IMAGEN DESDE LA PI CAMERA v1.3...")
    print("--------------------------------------------------")
    time.sleep(1) # Breve pausa de cortesía
    
    try:
        # Usamos el comando exacto que funcionó perfectamente
        subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
        print("¡Captura completada con éxito!")
    except Exception as e:
        print(f"Error al tomar la foto: {e}")
        return

    print("\n--------------------------------------------------")
    print("2. PROCESANDO IMAGEN PARA IMPRESIÓN TÉRMICA...")
    print("--------------------------------------------------")
    # Abrimos la imagen de 2592x1944 recién creada
    imagen_original = ImageOps.exif_transpose(Image.open(nombre_archivo))

    # Reescalamos manteniendo la proporción (Ancho fijo de 384 píxeles)
    ancho_fijo = 384
    alto_proporcional = int((imagen_original.height * ancho_fijo) / imagen_original.width)
    imagen_redimensionada = imagen_original.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

    # Filtro de contraste para mejorar la visibilidad en papel térmico
    potenciador = ImageEnhance.Contrast(imagen_redimensionada)
    imagen_contrastada = potenciador.enhance(1.6) # Aumentamos contraste un 60%

    # Convertimos a blanco y negro puro (1-bit Dithering)
    imatge_final = imagen_contrastada.convert("1")
    print(f"Imagen preparada: {ancho_fijo}x{alto_proporcional} píxeles.")

    print("\n--------------------------------------------------")
    print("3. CONECTANDO A IMPRESORA Y TRANSMITIENDO...")
    print("--------------------------------------------------")
    try:
        # Reducimos el tiempo de espera a 10 segundos para no perder tiempo si está apagada
        async with BleakClient(MAC, timeout=10) as client:
            print("¡Conectado por Bluetooth con éxito!")

            async def enviar(cmd, dades):
                await client.write_gatt_char(AE01, paquet(cmd, dades), response=False)
                await asyncio.sleep(0.04)

            # Iniciar el modo de datos de la impresora
            await enviar(0xBE, b"\x01")

            print(f"Imprimiendo tira térmica ({imatge_final.height} líneas)...")
            for y in range(imatge_final.height):
                await enviar(0xA2, convertir_fila(imatge_final, y))

            # =====================================================================
            # MEJORA: AVANCE EXTRA DE PAPEL PARA CORTE LIMPIO
            # =====================================================================
            print("Avanzando papel para el corte...")
            # Enviamos unas 60 líneas completamente en blanco (un bloque de 48 bytes vacíos)
            # Esto empujará el papel hacia afuera aproximadamente 4-5 centímetros
            fila_blanca = bytearray(48)
            for _ in range(60):
                await enviar(0xA2, bytes(fila_blanca))

            # Avanzar el mecanismo de forma nativa y cerrar
            await enviar(0xA1, bytes())
            print("¡Proceso finalizado! Ya puedes cortar tu papel limpiamente.")

    except asyncio.TimeoutError:
        print("\n[AVISO] No se pudo encontrar la impresora por Bluetooth.")
        print("-> Por favor, asegúrate de que la impresora está ENCENDIDA.")
        print("-> Verifica que la batería no esté agotada y que esté cerca de la Raspberry Pi.")
        
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo inesperado en la conexión: {e}")

# Lanzamos el proceso asíncrono
asyncio.run(main())
