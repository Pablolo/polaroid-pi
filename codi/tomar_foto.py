import subprocess
import time

print("Inicializando la Raspberry Pi Camera v1.3 (Entorno Bookworm)...")
time.sleep(2)

nombre_archivo = "mi_experimento.jpg"
print(f"Tomando foto con rpicam-still y guardándola como '{nombre_archivo}'...")

try:
    # USAMOS EL NUEVO COMANDO OFICIAL: rpicam-still
    # --immediate toma la foto al instante sin esperar previsualizaciones
    subprocess.run(["rpicam-still", "-o", nombre_archivo, "--immediate"], check=True)
    print("¡Listo! Foto guardada con éxito en esta carpeta.")
except subprocess.CalledProcessError as e:
    print(f"Error al intentar tomar la foto: {e}")
except FileNotFoundError:
    print("Error: No se encontró el comando 'rpicam-still'.")
