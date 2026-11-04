import asyncio
import subprocess
import time
from bleak import BleakClient
from PIL import Image, ImageEnhance, ImageOps

MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"

# Variable global temporal para capturar la respuesta del estado
ultima_resposta = None

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

# Callback para procesar la notificación de estado de la impresora
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
        # Intentamos conectar primero para validar que esté lista y con papel
        async with BleakClient(MAC, timeout=8) as client:
            print("¡Conectado por Bluetooth!")
            
            # Activamos notificaciones en la característica AE02
            await client.start_notify(AE02, rebre_estat)
            
            # Enviamos la orden de consulta de estado (A3)
            ordre_estat = bytes.fromhex("51 78 A3 00 01 00 00 00 FF")
            await client.write_gatt_char(AE01, ordre_estat, response=False)
            
            # Esperamos solo 1 segundo para la respuesta (suficiente si está encendida)
            await asyncio.sleep(1.0)
            await client.stop_notify(AE02)
            
            if ultima_resposta is None:
                print("\n[AVISO] La impresora está conectada, pero no respondió al test de estado.")
                print("¿Tiene papel cargado correctamente?")
                return
            
            # Nota técnica: Aquí podrías desglosar los bytes de 'ultima_resposta' si quieres
            # detectar específicamente "sin papel" o "batería baja".
            print("¡Impresora verificada con éxito! Procediendo a la captura...")

    except asyncio.TimeoutError:
        print("\n[AVISO] No se pudo encontrar la impresora por Bluetooth.")
        print("-> Por favor, asegúrate de que la impresora está ENCENDIDA.")
        print("-> Verifica que esté cerca de la Raspberry Pi y tenga batería.")
        return
    except Exception as e:
        print(f"\n[ERROR] Fallo al verificar la impresora antes de la foto: {e}")
        return

    print("\n--------------------------------------------------")
    print("2. CAPTURANDO IMAGEN DESDE LA PI CAMERA v1.3...")
    print("--------------------------------------------------")
    time.sleep(0.5) 
    
    try:
        # Captura inmediata con el sistema moderno de Bookworm
        subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
        print("¡Captura completada con éxito!")
    except Exception as e:
        print(f"Error al tomar la foto: {e}")
        return

    print("\n--------------------------------------------------")
    print("3. PROCESANDO IMAGEN PARA IMPRESIÓN TÉRMICA...")
    print("--------------------------------------------------")
    imagen_original = ImageOps.exif_transpose(Image.open(nombre_archivo))

    # Reescalado proporcional (Ancho fijo de 384 píxeles)
    ancho_fijo = 384
    alto_proporcional = int((imagen_original.height * ancho_fijo) / imagen_original.width)
    imagen_redimensionada = imagen_original.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

    # Filtro de contraste (+60%) y conversión a 1-bit Dithering
    potenciador = ImageEnhance.Contrast(imagen_redimensionada)
    imagen_contrastada = potenciador.enhance(1.6)
    imatge_final = imagen_contrastada.convert("1")
    print(f"Imagen preparada: {ancho_fijo}x{alto_proporcional} píxeles.")

    print("\n--------------------------------------------------")
    print("4. TRANSMITIENDO FOTO A LA IMPRESORA...")
    print("--------------------------------------------------")
    try:
        # Nos volvemos a conectar para transferir el bloque de datos de la imagen
        async with BleakClient(MAC, timeout=10) as client:
            async def enviar(cmd, dades):
                await client.write_gatt_char(AE01, paquet(cmd, dades), response=False)
                await asyncio.sleep(0.04)

            # Iniciar el modo de datos de la impresora
            await enviar(0xBE, b"\x01")

            print(f"Imprimiendo tira térmica ({imatge_final.height} líneas)...")
            for y in range(imatge_final.height):
                await enviar(0xA2, convertir_fila(imatge_final, y))

            print("Avanzando papel para el corte...")
            # Inyectamos 60 líneas en blanco para el margen de corte físico
            fila_blanca = bytearray(48)
            for _ in range(60):
                await enviar(0xA2, bytes(fila_blanca))

            # Avanzar mecanismo nativo y cerrar
            await enviar(0xA1, bytes())
            print("¡Proceso finalizado! Ya puedes cortar tu foto limpiamente.")

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo durante la transmisión de la imagen: {e}")

# Lanzamos el proceso asíncrono
asyncio.run(main())
