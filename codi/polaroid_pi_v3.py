import asyncio
import os
import subprocess
import time
from datetime import datetime
from gpiozero import Button
from bleak import BleakClient
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import requests
import sys

# ==================================================
# CONFIGURACIÓN BLUETOOTH
# ==================================================

MAC = "C4:4F:9F:E9:FE:EF"
AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"

# ==================================================
# CONFIGURACIÓN TELEGRAM
# ==================================================

# Introduce aquí tu NUEVO token de Telegram
TELEGRAM_TOKEN = "POSA_AQUI_EL_TOKEN_DEL_BOT"
TELEGRAM_CHAT_ID = "POSA_AQUI_EL_TEU_CHAT_ID"

ultima_resposta = None

# ==================================================
# FUNCIONES DE COMUNICACIÓN CON IMPRESORA
# ==================================================

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

# ==================================================
# ENVÍO DE FOTOGRAFÍAS A TELEGRAM
# ==================================================

def enviar_a_telegram(ruta_foto):
    print("\n[Telegram] Enviando la foto a tu móvil...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

    try:
        with open(ruta_foto, "rb") as foto:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": (
                    "📸 ¡Nueva foto de tu Raspberry Polaroid!\n"
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
                print(f"[Telegram] Error API: {response.status_code}")
                print(resultado)
    except Exception as e:
        print(f"[Telegram] Error de conexión: {e}")

# ==================================================
# APAGADO SEGURO
# ==================================================

def apagar_sistema():
    print("\n\033[91m==================================================")
    print("⚠️ ¡BOTÓN DE APAGADO DETECTADO! (3 SEGUNDOS)")
    print("Cerrando el sistema de forma segura ahora mismo...")
    print("==================================================\033[0m")
    time.sleep(2.0)
    os.system("sudo shutdown -h now")
    sys.exit()

# ==================================================
# PROCESAMIENTO DE IMAGEN
# ==================================================

def procesar_imagen(nombre_archivo):

    imagen_original = ImageOps.exif_transpose(
        Image.open(nombre_archivo)
    )

    imagen_vertical = imagen_original.rotate(90, expand=True)

    ancho_fijo = 384

    alto_proporcional = int(
        (imagen_vertical.height * ancho_fijo)
        / imagen_vertical.width
    )

    imagen_redimensionada = imagen_vertical.resize(
        (ancho_fijo, alto_proporcional),
        Image.Resampling.LANCZOS
    )

    imagen_contrastada = ImageEnhance.Contrast(
        imagen_redimensionada
    ).enhance(1.1)

    imagen_ajustada = ImageEnhance.Brightness(
        imagen_contrastada
    ).enhance(1.3)

    imagen_nitida = imagen_ajustada.filter(
        ImageFilter.SHARPEN
    )

    imatge_final = imagen_nitida.convert(
        "1",
        dither=Image.Dither.FLOYDSTEINBERG
    )

    return imatge_final

# ==================================================
# COMPROBAR ESTADO DE LA IMPRESORA
# ==================================================

async def comprobar_impresora():

    global ultima_resposta
    ultima_resposta = None

    async with BleakClient(MAC, timeout=10) as client:
        print("   Conectado. Consultando estado...")
        await client.start_notify(AE02, rebre_estat)
        ordre_estat = bytes.fromhex(
            "51 78 A3 00 01 00 00 00 FF"
        )
        
        await client.write_gatt_char(
            AE01,
            ordre_estat,
            response=False
        )

        await asyncio.sleep(1.0)
        await client.stop_notify(AE02)
        respuesta_valida = ultima_resposta is not None
    # La conexión se cierra al salir del bloque async with.
    return respuesta_valida

# ==================================================
# ENVIAR FOTOGRAFÍA A LA IMPRESORA
# ==================================================

async def imprimir_fotografia(imatge_final):
    async with BleakClient(MAC, timeout=10) as client:
        print("   Nueva conexión Bluetooth establecida.")
        async def enviar_comando(cmd, dades=b""):
            await client.write_gatt_char(
                AE01,
                paquet(cmd, dades),
                response=False
            )
            await asyncio.sleep(0.04)

        # INICIAR IMPRESIÓN

        await enviar_comando(0xBE, b"\x01")
        print(
            f"   Imprimiendo fotografía "
            f"({imatge_final.height} líneas)..."
        )

        # ENVIAR TODAS LAS FILAS

        for y in range(imatge_final.height):
            await enviar_comando(
                0xA2,
                convertir_fila(imatge_final, y)
            )

            if y % 100 == 0:
                print(f"   Progreso: {y}/{imatge_final.height} líneas")

        # AVANCE EXTRA DE PAPEL

        print("   Avanzando papel extra...")
        fila_blanca = bytes(48)
        for _ in range(110):
            await enviar_comando(0xA2, fila_blanca)

        # FINALIZAR IMPRESIÓN

        await enviar_comando(0xA1, bytes())
        print("   ¡Impresión finalizada con éxito!")

# ==================================================
# PROGRAMA PRINCIPAL
# ==================================================

async def main():

    global ultima_resposta

    # CONFIGURAR BOTONES GPIO

    boto_disparador = Button(17, pull_up=True)
    boto_apagado = Button(
        3,
        pull_up=True,
        hold_time=3.0
    )

    boto_apagado.when_held = apagar_sistema

    # CARPETA DE FOTOGRAFÍAS

    carpeta_fotos = os.path.expanduser(
        "~/MisFotosPolaroid"
    )

    os.makedirs(carpeta_fotos, exist_ok=True)

    # BUCLE PRINCIPAL

    while True:
        ultima_resposta = None
        print("\n==================================================")
        print("📸 CÁMARA INSTANTÁNEA EN ESPERA...")
        print("-> Pulsa el DISPARADOR (GPIO 17) para hacer una foto.")
        print("-> Mantén APAGAR (GPIO 3) durante 3 segundos.")
        print("==================================================")
        # ESPERAR DISPARADOR

        while not boto_disparador.is_pressed:
            await asyncio.sleep(0.1)

        print("\n¡Disparo detectado! Arrancando captura...")
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = os.path.join(
            carpeta_fotos,
            f"foto_{ahora}.jpg"
        )

        # --------------------------------------------------
        # PASO 1: CAPTURAR IMAGEN
        # --------------------------------------------------

        print("\n1. CAPTURANDO IMAGEN...")
        time.sleep(0.2)

        try:
            subprocess.run(
                [
                    "rpicam-still",
                    "-o",
                    nombre_archivo,
                    "--immediate"
                ],
                check=True
            )

            print("¡Captura completada!")

        except Exception as e:
            print(f"[ERROR] Al tomar la foto: {e}")
            await asyncio.sleep(1)
            continue

        # --------------------------------------------------
        # PASO 2: TELEGRAM Y PROCESAMIENTO
        # --------------------------------------------------

        print("\n2. ENVIANDO A TELEGRAM Y PROCESANDO...")
        loop = asyncio.get_running_loop()
        print("[Sistema] Esperando el envío de Telegram...")

        await loop.run_in_executor(
            None,
            enviar_a_telegram,
            nombre_archivo
        )

        print("[Sistema] Telegram terminado. Preparando impresora...")

        try:
            imatge_final = procesar_imagen(nombre_archivo)
            print(
                f"Imagen preparada: "
                f"384 x {imatge_final.height} píxeles"
            )
        except Exception as e:
            print(f"[ERROR] Procesando imagen: {e}")
            await asyncio.sleep(1)
            continue

        # --------------------------------------------------
        # PASO 3: COMPROBAR Y CONECTAR A IMPRESORA
        # --------------------------------------------------

        print("\n3. CONECTANDO CON IMPRESORA NK...")
        impresion_realizada = False
        max_intentos = 3

        for intento in range(1, max_intentos + 1):
            print(
                f"\n-> Intento {intento}/{max_intentos}"
            )
            try:

                # PRIMERA CONEXIÓN:
                # CONSULTAR ESTADO Y CERRAR CONEXIÓN

                impresora_lista = await comprobar_impresora()
                if not impresora_lista:

                    print(
                        "[AVISO] La impresora no ha respondido."
                    )

                    raise Exception(
                        "No se recibió respuesta de estado"
                    )

                print("¡Impresora lista!")
                await asyncio.sleep(0.5)

                # SEGUNDA CONEXIÓN:
                # TRANSMITIR FOTOGRAFÍA

                print(
                    "Abriendo nueva conexión para imprimir..."
                )
                await imprimir_fotografia(imatge_final)
                impresion_realizada = True
                break
            except Exception as e:
                print(
                    f"[AVISO] Error en intento "
                    f"{intento}: {e}"
                )

            if intento < max_intentos:
                print("Esperando 2 segundos para reintentar...")
                await asyncio.sleep(2.0)

        # --------------------------------------------------
        # PASO 4: RESULTADO
        # --------------------------------------------------

        if impresion_realizada:
            print("\n¡FOTOGRAFÍA IMPRESA CORRECTAMENTE! 📸")
        else:

            print("\n[Modo Digital] Impresora inaccesible.")
            print("La fotografía permanece guardada.")
            print("También se ha solicitado su envío a Telegram.")

        # --------------------------------------------------
        # PASO 5: PREPARAR SIGUIENTE FOTO
        # --------------------------------------------------

        print("\nPreparando cámara para el siguiente disparo...")
        await asyncio.sleep(2.0)

# ==================================================
# INICIAR SISTEMA
# ==================================================

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n[Sistema] Cámara detenida manualmente.")
