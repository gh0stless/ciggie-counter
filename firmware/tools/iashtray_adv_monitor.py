"""Werbepakete des Superaschers beobachten: Takt (Pakete/s) und Zählerstand aus den Manufacturer Data.

Ruhe ~1 Paket/s, nach einem Stempeldruck 30 s lang ~10 Pakete/s (Firmware app_adv.c).
Windows meldet nicht jedes einzelne Paket, die Raten sind daher Untergrenzen.

Aufruf:  python firmware/tools/iashtray_adv_monitor.py [sekunden]
"""
import asyncio
import struct
import sys
import time

from bleak import BleakScanner

UUID_SERVICE = "15770001-0f39-460f-8588-44afa8137b74"
COMPANY_ID = 0xFFFF


async def main(duration: int) -> None:
    seen = []  # (Zeit, Zählerstand)

    def on_adv(device, adv) -> None:
        if UUID_SERVICE not in adv.service_uuids:
            return
        data = adv.manufacturer_data.get(COMPANY_ID)
        count = struct.unpack("<I", data[:4])[0] if data and len(data) >= 4 else None
        if not seen or seen[-1][1] != count:
            print(f"{time.strftime('%H:%M:%S')}  Zählerstand im Werbepaket: {count}")
        seen.append((time.monotonic(), count))

    print(f"Lausche {duration} s – jetzt ruhig mal auf einen Board-Taster drücken …")
    start = time.monotonic()
    async with BleakScanner(on_adv, scanning_mode="active"):
        last_report = start
        while time.monotonic() - start < duration:
            await asyncio.sleep(5)
            now = time.monotonic()
            n = sum(1 for t, _ in seen if t >= last_report)
            print(f"  {time.strftime('%H:%M:%S')}  {n / (now - last_report):4.1f} Pakete/s")
            last_report = now


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 60))
