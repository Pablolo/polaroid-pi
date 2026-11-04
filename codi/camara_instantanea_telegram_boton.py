import asyncio
import os
import subprocess
import time
from datetime import datetime
from gpiozero import Button
from bleak import BleakClient
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import requests

# CONFIGURACIÓN BLUETOOTH
MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"

# CONFIGURACIÓN TELEGRAM
TELEGRAM_TOKEN = "POSA_AQUI_EL_TOKEN_DEL_BOT"
TELEGRAM_CHAT_ID = "POSA_AQUI_EL_TEU_CHAT_ID"

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
    print(f"-> Info de la impressora: {data.hex(' ')}")

# Función para enviar la foto en segundo plano sin congelar la impresión
def enviar_a_telegram(ruta_foto):
    print("\n[Telegram] Intentando enviar la foto a tu móvil...")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

    try:
        with open(ruta_foto, "rb") as foto:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": (
                    f"📸 ¡Nueva foto de tu Raspberry Polaroid!\n"
                    f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
            }

            response = requests.post(
                url,
                data=payload,
                files={"photo": foto},
                timeout=(5, 20)
            )

            resultado = response.json()

            if response.ok and resultado.get("ok"):
                print("[Telegram] ¡Foto enviada correctamente!")
            else:
                print(f"[Telegram] Error HTTP: {response.status_code}")
                print(f"[Telegram] Detalles: {resultado}")

    except requests.exceptions.Timeout:
        print("[Telegram] Tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        print(f"[Telegram] Error de conexión: {e}")
    except Exception as e:
        print(f"[Telegram] Error inesperado: {e}")


async def main():
    global ultima_resposta

    # CONFIGURAR BOTÓN DISPARADOR (Se inicializa una sola vez fuera del bucle)
    boto_disparador = Button(17, pull_up=True)
    
    # ORGANIZACIÓN AUTOMÁTICA DE ARCHIVOS (Se crea la carpeta una sola vez)
    carpeta_fotos = os.path.expanduser("~/MisFotosPolaroid")
    os.makedirs(carpeta_fotos, exist_ok=True)

    # 🔄 BUCLE INFINITO PARA CONVERTIRLO EN CÁMARA CONTINUA
    while True:
        ultima_resposta = None  # Reseteamos el estado para el nuevo disparo
        
        print("\n==================================================")
        print("📸 CÁMARA INSTANTÁNEA EN ESPERA...")
        print("Presiona el botón físico para tomar una foto.")
        print("==================================================")

        # El programa se detiene aquí de forma segura hasta que detecte la pulsación
        boto_disparador.wait_for_press() 
        print("\n¡Disparo detectado! Arrancando sistema...")

        # Generamos el nombre del archivo con la hora exacta de la pulsación actual
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = os.path.join(carpeta_fotos, f"foto_{ahora}.jpg")

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
                    print("\n[AVISO] La impresora no respondió al test de estado. Reintentando en el próximo clic.")
                    continue  # Regresa al inicio del bucle a esperar otra pulsación
                print("¡Impresora lista! Procediendo...")
        except asyncio.TimeoutError:
            print("\n[AVISO] No se pudo encontrar la impresora. ¿Está encendida? Reintentando en el próximo clic.")
            continue
        except Exception as e:
            print(f"\n[ERROR] Fallo de conexión previo: {e}")
            continue

        print("\n--------------------------------------------------")
        print(f"2. CAPTURANDO IMAGEN DESDE LA PI CAMERA v1.3...")
        print(f"Guardando como: {os.path.basename(nombre_archivo)}")
        print("--------------------------------------------------")
        time.sleep(0.5) 
        try:
            subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
            print("¡Captura completada con éxito!")
        except Exception as e:
            print(f"Error al tomar la foto: {e}")
            continue

        print("\n--------------------------------------------------")
        print("3. PROCESANDO IMAGEN (FORMATO VERTICAL Y ALTA CLARIDAD)...")
        print("--------------------------------------------------")
        imagen_original = ImageOps.exif_transpose(Image.open(nombre_archivo))

        # Rotación vertical (90 grados)
        imagen_vertical = imagen_original.rotate(90, expand=True)

        # Reescalado proporcional al ancho de la impresora (384 píxeles)
        ancho_fijo = 384
        alto_proporcional = int((imagen_vertical.height * ancho_fijo) / imagen_vertical.width)
        imagen_redimensionada = imagen_vertical.resize((ancho_fijo, alto_proporcional), Image.Resampling.LANCZOS)

        # Filtros de claridad y nitidez extrema
        imagen_nitida = imagen_redimensionada.filter(ImageFilter.SHARPEN)
        
        potenciador_contraste = ImageEnhance.Contrast(imagen_nitida)
        imagen_contrastada = potenciador_contraste.enhance(1.8)
        
        potenciador_brillo = ImageEnhance.Brightness(imagen_contrastada)
        imagen_ajustada = potenciador_brillo.enhance(0.95)

        # Conversión final a blanco y negro puro (1-bit Dithering)
        imatge_final = imagen_ajustada.convert("1")
        print(f"Imagen preparada en VERTICAL: {ancho_fijo}x{alto_proporcional} píxeles.")

        print("\n--------------------------------------------------")
        print("4. TRANSMITIENDO FOTO A LA IMPRESORA Y ENVIANDO A TELEGRAM...")
        print("--------------------------------------------------")
        try:
            # Disparamos el envío a Telegram en paralelo para aprovechar el tiempo mientras conecta el BLE
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, enviar_a_telegram, nombre_archivo)

            async with BleakClient(MAC, timeout=10) as client:
                async def enviar(cmd, dades):
                    await client.write_gatt_char(AE01, paquet(cmd, dades), response=False)
                    await asyncio.sleep(0.04)

                await enviar(0xBE, b"\x01")

                print(f"Imprimiendo foto vertical ({imatge_final.height} líneas)...")
                for y in range(imatge_final.height):
                    await enviar(0xA2, convertir_fila(imatge_final, y))

                # 110 líneas en blanco para el avance físico
                print("Avanzando papel extra para un corte limpio...")
                fila_blanca = bytearray(48)
                for _ in range(110):
                    await enviar(0xA2, bytes(fila_blanca))

                await enviar(0xA1, bytes())
                print(f"\n¡Proceso finalizado con éxito!")

        except Exception as e:
            print(f"\n[ERROR] Ocurrió un fallo durante la transmisión: {e}")

        # Pequeña pausa de seguridad antes de permitir el siguiente disparo físico
        print("\nPreparando cámara para el siguiente disparo...")
        await asyncio.sleep(3.0)

# Lanzamos el proceso asíncrono básico
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n[Sistema] Cámara detenida de forma manual desde la terminal (Ctrl+C).")
