from bleak import BleakScanner
import asyncio
from processor import process_ble_data

async def scan_ble():
    devices = await BleakScanner.discover()
    process_ble_data(devices)

if __name__ == "__main__":
    asyncio.run(scan_ble())
