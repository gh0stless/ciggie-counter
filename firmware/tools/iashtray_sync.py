"""Butt Bin (Superascher) per Bluetooth vom PC abgleichen.

Ablauf wie in der spaeteren App (siehe hardware-handover.md, GATT-Profil):
  1. Geraet "Butt Bin" suchen und verbinden
  2. Uhr stellen (Time = aktuelle Unix-Zeit)
  3. Events abonnieren, Startnummer schreiben, Ereignisse bis zur Endemarke empfangen

Voraussetzung:  pip install bleak
Aufruf:         python firmware/tools/iashtray_sync.py [startnummer]
"""
import asyncio
import struct
import sys
import time
from datetime import datetime

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Butt Bin"
UUID_SERVICE = "15770001-0f39-460f-8588-44afa8137b74"
UUID_COUNT ="15770002-0f39-460f-8588-44afa8137b74"
UUID_TIME = "15770003-0f39-460f-8588-44afa8137b74"
UUID_EVENTS = "15770004-0f39-460f-8588-44afa8137b74"
SEQ_TIME_UNKNOWN = 0x80000000


async def main(start_seq: int) -> None:
    print(f"Suche {DEVICE_NAME} ...")
    # nach Service-UUID bzw. Name in den Werbedaten filtern: Windows cacht sonst alte Geraetenamen
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: UUID_SERVICE in adv.service_uuids or adv.local_name == DEVICE_NAME,
        timeout=15)
    if device is None:
        sys.exit(f"{DEVICE_NAME} nicht gefunden (Board an? Handy noch verbunden?)")

    # Windows cacht GATT-Dienste pro Adresse; nach Firmware-Updates sonst veraltet
    async with BleakClient(device, winrt={"use_cached_services": False}) as client:
        print(f"Verbunden mit {device.address}")

        count = struct.unpack("<I", await client.read_gatt_char(UUID_COUNT))[0]
        dev_time = struct.unpack("<I", await client.read_gatt_char(UUID_TIME))[0]
        print(f"Zaehler: {count}")
        if dev_time:
            print(f"Geraeteuhr: {datetime.fromtimestamp(dev_time)}  (Abweichung {dev_time - int(time.time()):+d} s)")
        else:
            print("Geraeteuhr: nicht gestellt")

        now = int(time.time())
        await client.write_gatt_char(UUID_TIME, struct.pack("<I", now), response=True)
        print(f"Uhr gestellt: {datetime.fromtimestamp(now)}")

        done = asyncio.Event()
        events = []

        def on_events(_, data: bytearray) -> None:
            if len(data) == 4:  # Endemarke = Gesamtzahl
                print(f"Endemarke: {struct.unpack('<I', data)[0]} Ereignisse insgesamt")
                done.set()
                return
            for off in range(0, len(data) - 7, 8):
                seq, t = struct.unpack_from("<II", data, off)
                events.append((seq, t))

        await client.start_notify(UUID_EVENTS, on_events)
        await client.write_gatt_char(UUID_EVENTS, struct.pack("<I", start_seq), response=True)
        try:
            await asyncio.wait_for(done.wait(), timeout=30)
        except asyncio.TimeoutError:
            print("Keine Endemarke innerhalb von 30 s erhalten")
        await client.stop_notify(UUID_EVENTS)

    print(f"\n{len(events)} Ereignisse ab Nummer {start_seq}:")
    expected = None
    for seq, t in events:
        num = seq & ~SEQ_TIME_UNKNOWN
        if expected is not None and num != expected:
            print(f"  -- Luecke: {expected} bis {num - 1} fehlen")
        expected = num + 1
        if seq & SEQ_TIME_UNKNOWN:
            print(f"  #{num:5d}  Zeit unbekannt ({t} s nach damaligem Geraetestart)")
        else:
            print(f"  #{num:5d}  {datetime.fromtimestamp(t)}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 0))
