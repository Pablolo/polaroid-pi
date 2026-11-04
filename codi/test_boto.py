import time
from gpiozero import Button

# Configuramos el botón en el pin GPIO 17
# pull_up=True activa una resistencia interna para que el pin no capte interferencias
boto = Button(17, pull_up=True)

print("--- TEST DEL BOTÓN DISPARADOR ---")
print("Presiona el botón para comprobar que funciona (Ctrl+C para salir)...")

try:
    while True:
        if boto.is_pressed:
            print("¡Botón pulsado correctamente! 🎉")
            time.sleep(0.3) # Evita que se repita el mensaje mil veces por segundo
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTest finalizado.")
