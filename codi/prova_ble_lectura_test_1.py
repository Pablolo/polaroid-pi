import asyncio
from bleak import BleakClient

MAC = "C4:4F:9F:E9:FE:EF"
UUID = "0000ae10-0000-1000-8000-00805f9b34fb"

async def main():
    async with BleakClient(MAC) as client:
        print("Connectat:", client.is_connected)

        dades = await client.read_gatt_char(UUID)

        print("Dades:", dades.hex(" "))
        print("Bytes:", list(dades))

asyncio.run(main())
