import asyncio
from bleak import BleakClient

MAC = "C4:4F:9F:E9:FE:EF"

async def main():
    async with BleakClient(MAC, timeout=20) as client:
        print("Connectat:", client.is_connected)

        for service in client.services:
            print("Servei:", service.uuid)

            for char in service.characteristics:
                print("  Característica:", char.uuid)
                print("  Propietats:", char.properties)

asyncio.run(main())
