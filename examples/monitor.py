"""Stream live sensor data from a Safera Sense device.

Usage: python examples/monitor.py D4:6A:C8:XX:XX:XX
"""

import asyncio
import sys

from bleak import BleakScanner

from safera_sense_ble import SaferaSenseClient, SensorReport


def on_report(report: SensorReport) -> None:
    print(
        f"ambient {report.ambient_temperature:5.1f} °C | "
        f"pan {report.heat_index:3d} °C | "
        f"humidity {report.humidity:5.1f} % | "
        f"eCO2 {report.co2_ppm:4d} ppm | "
        f"tVOC {report.tvoc_ppb:4d} ppb | "
        f"AQI {report.air_quality_index:3d} | "
        f"filter {report.grease_filter} % | "
        f"fan L{report.fan_speed_level} | "
        f"light L{report.light_level}"
    )


async def main(address: str) -> None:
    ble_device = await BleakScanner.find_device_by_address(address)
    if ble_device is None:
        raise SystemExit(f"Device {address} not found (is the vendor app connected?)")

    client = SaferaSenseClient(ble_device)
    await client.connect()
    try:
        info = await client.fetch_device_info()
        print(f"Connected: {info.manufacturer} {info.model}, fw {info.firmware_rev}")
        await client.subscribe_sensor_reports(on_report)
        print("Streaming (Ctrl+C to stop)...")
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1]))
