# safera-sense-ble

Async Python library for talking to **Safera Sense** cooking sensors over
Bluetooth Low Energy — as found in **Røros Hetta** cooker hoods
(Safera Sense Integral) and Safera stove guards.

[![CI](https://github.com/christophebaraer/safera-sense-ble/actions/workflows/ci.yml/badge.svg)](https://github.com/christophebaraer/safera-sense-ble/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/safera-sense-ble.svg)](https://pypi.org/project/safera-sense-ble/)

## Credits

The idea and much of the protocol reverse engineering come from
**Håvard Gulldahl**'s [rorossense-ble](https://github.com/havardgulldahl/rorossense-ble)
project — in particular its excellent byte-level
[protocol documentation](https://github.com/havardgulldahl/rorossense-ble/blob/main/docs/safera-ble-protocol.md).
This library is an independent, from-scratch implementation of that
protocol, extended with findings made during its development:

- the proprietary characteristics require **BLE bonding** (the device
  answers ATT "Insufficient authentication" until paired; this library
  pairs on demand and retries),
- **grease filter saturation** lives at byte 59 of the extended sensor
  report, and resets via the `SET_HOOD_FILTER_CHANGED` command
  (confirmed experimentally against the vendor app on an
  `IFU10CR-PRO`, firmware 13/75).

Unofficial project — not affiliated with Safera Oy or Røros Metall AS.

## Features

- **Live sensor stream**: subscribe to notifications (~1 Hz) parsed into a
  typed `SensorReport` — ambient/surface/pan temperature, humidity,
  ambient light, eCO2, tVOC, air quality index, particle index, stove
  power draw, cooking activity, alarm level, grease filter saturation,
  device state, error bitfields.
- **Control**: hood fan speeds 1–3, boost, auto mode; light levels 1–3;
  identify; grease-filter reset.
- **Device info**: model, serial, hardware/firmware revisions, Wi-Fi
  status (SSID, RSSI, device name).
- Built on [bleak](https://github.com/hbldh/bleak) and
  [bleak-retry-connector](https://github.com/Bluetooth-Devices/bleak-retry-connector);
  plays well with Home Assistant's Bluetooth stack but has **no Home
  Assistant dependency**.

## Installation

```bash
pip install safera-sense-ble
```

## Usage

### Find the device

Safera devices advertise the proprietary service UUID and, depending on
branding, a name like `Røroshetta`, `iSense…` or `Sense_…`:

```python
import asyncio
from bleak import BleakScanner
from safera_sense_ble import SAFERA_SERVICE_UUID

async def find():
    devices = await BleakScanner.discover(return_adv=True)
    for device, adv in devices.values():
        if SAFERA_SERVICE_UUID in adv.service_uuids:
            print(device.address, adv.local_name)

asyncio.run(find())
```

### Stream sensor data

```python
import asyncio
from bleak import BleakScanner
from safera_sense_ble import SaferaSenseClient, SensorReport

async def monitor(address: str):
    ble_device = await BleakScanner.find_device_by_address(address)
    client = SaferaSenseClient(ble_device)
    await client.connect()

    info = await client.fetch_device_info()
    print(f"Connected to {info.model} (fw {info.firmware_rev})")

    def on_report(report: SensorReport) -> None:
        print(
            f"{report.ambient_temperature:.1f} °C  "
            f"{report.humidity:.0f} %RH  "
            f"eCO2 {report.co2_ppm} ppm  "
            f"filter {report.grease_filter} %"
        )

    # The device requires bonding for this; the client pairs on demand.
    await client.subscribe_sensor_reports(on_report)
    await asyncio.sleep(30)
    await client.disconnect()

asyncio.run(monitor("D4:6A:C8:XX:XX:XX"))
```

### Control the hood

```python
from safera_sense_ble import FanSpeed, LightLevel

await client.set_fan_speed(FanSpeed.LEVEL_2)   # speeds 1-3
await client.set_fan_speed(FanSpeed.BOOST)     # time-limited boost
await client.set_fan_auto()                    # air-quality controlled
await client.set_fan_speed(FanSpeed.OFF)

await client.set_light_level(LightLevel.LEVEL_3)
await client.set_light_level(LightLevel.OFF)

await client.identify()                        # make the device identify itself
await client.reset_grease_filter()             # after cleaning the filter
```

### One-shot reads

```python
report = await client.fetch_sensor_report()    # single parsed snapshot
wifi = await client.fetch_wifi_status()        # SSID, RSSI, device name, IP
```

See [examples/monitor.py](examples/monitor.py) for a runnable script.

## API notes

- All methods are coroutines; the client is designed for a single
  long-lived connection (the device accepts one central at a time — close
  the vendor app while connected).
- `SensorReport.from_bytes` accepts both the documented 54-byte record
  and the extended (~69-byte) record sent by hood-integrated devices;
  hood-only fields (`fan_speed_raw`, `light_raw`, `grease_filter`, …)
  are `None` when absent.
- `SaferaSenseClient.dump_characteristics()` hex-dumps every readable
  characteristic — useful for decoding the remaining unknown fields;
  contributions welcome upstream and here.

## License

MIT — see [LICENSE](LICENSE).
