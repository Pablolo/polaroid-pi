import os
import subprocess
import time
from datetime import datetime
import requests

# CONFIGURACIÓN TELEGRAM
TELEGRAM_TOKEN = "POSA_AQUI_EL_TOKEN_DEL_BOT"
TELEGRAM_CHAT_ID = "POSA_AQUI_EL_TEU_CHAT_ID"

def enviar_a_telegram(ruta_foto):
    print("\n[Telegram] Enviando captura de prueba para enfoque...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(ruta_foto, "rb") as foto:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": f"🔍 PRUEBA DE ENFOQUE\n📅 {datetime.now().strftime('%H:%M:%S')}\n\n¡Revisa la nitidez de esta imagen!"
            }
            response = requests.post(url, data=payload, files={"photo": foto}, timeout=(5, 20))
            if response.ok and response.json().get("ok"):
                print("[Telegram] ¡Foto enviada! Revisa tu móvil.")
            else:
                print(f"[Telegram] Error: {response.status_code}")
    except Exception as e:
        print(f"[Telegram] Error de conexión: {e}")

def main():
    carpeta_fotos = "/home/pi/MisFotosPolaroid"
    os.makedirs(carpeta_fotos, exist_ok=True)
    
    nombre_archivo = os.path.join(carpeta_fotos, "prueba_enfoque.jpg")
    
    # Si existía una prueba anterior, la borramos para no confundirnos
    if os.path.exists(nombre_archivo):
        os.remove(nombre_archivo)

    print("\n==================================================")
    print("📸 CAPTURANDO IMAGEN DE PRUEBA (Sin impresión)...")
    print("==================================================")
    
    try:
        # Tomamos la foto a máxima resolución para evaluar bien el detalle del enfoque
        subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
        print("¡Captura completada con éxito!")
        
        # Enviamos el archivo original directamente a Telegram
        enviar_a_telegram(nombre_archivo)
        
    except Exception as e:
        print(f"[Error] No se pudo tomar la foto: {e}")

if __name__ == "__main__":
    main()
