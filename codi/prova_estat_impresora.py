import asyncio
from bleak import BleakClient

MAC = "C4:4F:9F:E9:FE:EF"

AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"

def resposta(sender, data):
    print("Resposta BLE:", data.hex(" "))

async def main():
    async with BleakClient(MAC, timeout=20) as client:

        print("Connectat:", client.is_connected)

        await client.start_notify(AE02, resposta)
        print("Notificacions activades")

        # Consulta de l'estat de la impressora
        ordre = bytes.fromhex("51 78 A3 00 01 00 00 00 FF")

        print("Enviant:", ordre.hex(" "))

        await client.write_gatt_char(
            AE01,
            ordre,
            response=False
        )

        print("Esperant resposta...")
        await asyncio.sleep(5)

        await client.stop_notify(AE02)

    print("Connexió finalitzada")

asyncio.run(main())
