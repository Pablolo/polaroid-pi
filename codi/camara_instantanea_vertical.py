import asyncio
import subprocess
import time
from bleak import BleakClient
from PIL import Image, ImageEnhance, ImageOps, ImageFilter

MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"

ultima_resposta = None

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

def rebre_estat(sender, data):
    global ultima_resposta
    ultima_resposta = data
    print(f"-> Info recibida de la impresora: {data.hex(' ')}")

async def main():
    nombre_archivo = "mi_experimento.jpg"
    global ultima_resposta

    print("--------------------------------------------------")
    print("1. VERIFICANDO ESTADO DE LA IMPRESORA...")
    print("--------------------------------------------------")
    try:
        async with BleakClient(MAC, timeout=8) as client:
            print("¡Conectado por Bluetooth!")
            await client.start_notify(AE02, rebre_estat)
            
            ordre_estat = bytes.fromhex("51 78 A3 00 01 00 00 00 FF")
            await client.write_gatt_char(AE01, ordre_estat, response=False)
            
            await asyncio.sleep(1.0)
            await client.stop_notify(AE02)
            
            if ultima_resposta is None:
                print("\n[AVISO] La impresora no respondió al test de estado.")
                return
            print("¡Impresora lista! Procediendo...")
    except asyncio.TimeoutError:
        print("\n[AVISO] No se pudo encontrar la impresora. ¿Está encendida?")
        return
    except Exception as e:
        print(f"\n[ERROR] Fallo de conexión previo: {e}")
        return

    print("\n--------------------------------------------------")
    print("2. CAPTURANDO IMAGEN DESDE LA PI CAMERA v1.3...")
    print("--------------------------------------------------")
    time.sleep(0.5) 
    try:
        subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
        print("¡Captura completada!")
    except Exception as e:
        print(f"Error al tomar la foto: {e}")
        return

    print("\n--------------------------------------------------")
    print("3. PROCESANDO IMAGEN (FORMATO VERTICAL Y ALTA CLARIDAD)...")
    print("--------------------------------------------------")
    imagen_original = ImageOps.exif_transpose(Image.open(nombre_archivo))

    # =====================================================================
    # MEJORA 1: ROTACIÓN VERTICAL
    # Rotamos la foto 90 grados en sentido horario para que sea vertical
    # =====================================================================
    imagen_vertical = imagen_original.rotate(90, expand=True)

    # Reescalado proporcional al ancho de la impresora (384 píxeles)
    ancho_fijo = 384
    alto_proporcional = int((imagen_vertical.height * ancho_fijo) / imagen_vertical.width)
    imagen_redimensionada = imagen_vertical.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

    # =====================================================================
    # MEJORA 3: MEJORAR LA CLARIDAD / RESOLUCIÓN VISUAL
    # =====================================================================
    # 1. Aplicamos un filtro de nitidez extrema para resaltar bordes y detalles
    imagen_nitida = imagen_redimensionada.filter(ImageFilter.SHARPEN)
    
    # 2. Incrementamos el contraste fuertemente (factor de 1.8 o 2.0)
    potenciador_contraste = ImageEnhance.Contrast(imagen_nitida)
    imagen_contrastada = potenciador_contraste.enhance(1.8)
    
    # 3. Oscurecemos ligeramente la imagen si es necesario para que el cabezal térmico queme con fuerza
    potenciador_brillo = ImageEnhance.Brightness(imagen_contrastada)
    imagen_ajustada = potenciador_brillo.enhance(0.95)

    # Convertimos a blanco y negro puro (1-bit Floy-Steinberg Dithering)
    imatge_final = imagen_ajustada.convert("1")
    print(f"Imagen preparada en VERTICAL: {ancho_fijo}x{alto_proporcional} píxeles.")

    print("\n--------------------------------------------------")
    print("4. TRANSMITIENDO FOTO A LA IMPRESORA...")
    print("--------------------------------------------------")
    try:
        async with BleakClient(MAC, timeout=10) as client:
            async def enviar(cmd, dades):
                await client.write_gatt_char(AE01, paquet(cmd, dades), response=False)
                await asyncio.sleep(0.04)

            await enviar(0xBE, b"\x01")

            print(f"Imprimiendo foto vertical ({imatge_final.height} líneas)...")
            for y in range(imatge_final.height):
                await enviar(0xA2, convertir_fila(imatge_final, y))

            # =====================================================================
            # MEJORA 2: MÁS LÍNEAS EN BLANCO AL FINAL
            # Incrementado a 110 líneas para un avance cómodo y corte limpio
            # =====================================================================
            print("Avanzando papel extra para un corte limpio...")
            fila_blanca = bytearray(48)
            for _ in range(110):
                await enviar(0xA2, bytes(fila_blanca))

            await enviar(0xA1, bytes())
            print("¡Proceso finalizado! Ya puedes cortar tu foto vertical perfectamente.")

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo durante la transmisión: {e}")

asyncio.run(main())
