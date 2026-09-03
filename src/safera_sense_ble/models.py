"""Parsers for the Safera Sense BLE payloads.

Byte layouts are documented in
https://github.com/havardgulldahl/rorossense-ble/blob/main/docs/safera-ble-protocol.md
All multi-byte values are little-endian.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import PCU_ERROR_FLAGS, SENSOR_ERROR_FLAGS

SENSOR_REPORT_MIN_LEN = 54


def _u16(payload: bytes, offset: int) -> int:
    return int.from_bytes(payload[offset : offset + 2], "little")


def _s16(payload: bytes, offset: int) -> int:
    return int.from_bytes(payload[offset : offset + 2], "little", signed=True)


def _u32(payload: bytes, offset: int) -> int:
    return int.from_bytes(payload[offset : offset + 4], "little")


def _ascii(payload: bytes, offset: int, length: int) -> str:
    raw = payload[offset : offset + length]
    return raw.split(b"\x00")[0].split(b"\x0a")[0].decode("ascii", "replace")


@dataclass(frozen=True)
class SensorReport:
    """A parsed SENSOR_REPORT ("beef") record."""

    ambient_temperature: float  # °C
    surface_temperature: float  # °C
    humidity: int  # %RH (quantized to whole percent)
    ambient_light: int  # lx (presumed; quantized to whole lux)
    mounting_height: int  # cm
    air_quality_index: int
    # Documented upstream as "particle index, unit/scale unknown"; observed
    # to track the vendor app's PM2.5 reading (µg/m³) on IFU10CR-PRO.
    particle_index: float
    voc_uba: float  # UBA index 1-5, 0 = no data
    co2_ppm: int
    tvoc_ppb: int
    heat_index: int  # estimated pan temperature, °C
    connected_accessories: int
    battery_level: int  # %
    alarm_status: int  # 1 = normal, 0 = stove power cut, 118-104 = alarm countdown
    device_state: int
    sensor_errors: int
    device_clock: int
    pcu_errors: int
    activity_type: int  # 0 = idle, 2 = cooking
    alarm_level: int  # %, alarm sounds at 100
    activity_level: int  # %
    power_consumption: int  # W, stove power draw
    # Hood state; only present when the sensor is integrated with a hood
    # and the device sends an extended (>54 byte) report. Offsets
    # confirmed empirically on IFU10CR-PRO fw 13/75:
    #   byte 56 = commanded fan speed step (0/30/60/90/120)
    #   byte 60 = auto flags bitfield, matching magicus's
    #             HOOD_AUTO_MASTER_ENABLES: bit 0x01 = fan auto,
    #             bit 0x02 = light auto
    fan_speed_raw: int | None = None  # 0/30/60/90/120
    hood_flags: int | None = None
    light_raw: int | None = None  # light step indicator, 0/30/60/90 (level * 30)
    # Grease filter saturation %; resets to 0 via SET_HOOD_FILTER_CHANGED.
    # (Byte 59 tracked the vendor app's filter percentage and zeroed on
    # reset.)
    grease_filter: int | None = None

    @property
    def fan_speed_level(self) -> int | None:
        """Fan level 0-4, if known (0 = off, 4 = boost)."""
        if self.fan_speed_raw is None or self.fan_speed_raw not in (
            0,
            30,
            60,
            90,
            120,
        ):
            return None
        return self.fan_speed_raw // 30

    @property
    def fan_auto(self) -> bool | None:
        """True when the fan is in automatic (air-quality) mode."""
        if self.hood_flags is None:
            return None
        return bool(self.hood_flags & 0x01)

    @property
    def light_auto(self) -> bool | None:
        """True when the light is in automatic (presence-based) mode."""
        if self.hood_flags is None:
            return None
        return bool(self.hood_flags & 0x02)

    @property
    def light_level(self) -> int | None:
        """Current light level 0-3, if known."""
        if self.light_raw is None or self.light_raw not in (0, 30, 60, 90):
            return None
        return round(self.light_raw / 30)

    @property
    def sensor_error_messages(self) -> list[str]:
        return [
            msg for mask, msg in SENSOR_ERROR_FLAGS.items() if self.sensor_errors & mask
        ]

    @property
    def pcu_error_messages(self) -> list[str]:
        return [msg for mask, msg in PCU_ERROR_FLAGS.items() if self.pcu_errors & mask]

    @classmethod
    def from_bytes(cls, payload: bytes | bytearray) -> SensorReport:
        if len(payload) < SENSOR_REPORT_MIN_LEN:
            raise ValueError(
                f"Sensor payload too short: {len(payload)} < {SENSOR_REPORT_MIN_LEN}"
            )
        payload = bytes(payload)
        # Values are quantized to each sensor's meaningful precision; the
        # raw record's resolution (0.01 degC, 0.01 %RH, 1/32 lx) is
        # measurement jitter, and forwarding it verbatim makes every
        # report look like a state change to consumers.
        return cls(
            ambient_temperature=round(_u16(payload, 0) * 0.01 - 50, 1),
            surface_temperature=round(_u16(payload, 2) * 0.01 - 50, 1),
            humidity=round(_u16(payload, 4) / 100),
            ambient_light=round(_u16(payload, 6) / 32),
            mounting_height=payload[8],
            air_quality_index=_u16(payload, 10),
            particle_index=round(_u16(payload, 12) / 5, 1),
            voc_uba=round(payload[14] / 20, 1),
            co2_ppm=_u16(payload, 15),
            tvoc_ppb=_u16(payload, 17),
            heat_index=payload[24] * 2,
            connected_accessories=payload[25],
            battery_level=payload[26],
            alarm_status=payload[28],
            device_state=payload[33],
            sensor_errors=_u16(payload, 34),
            device_clock=_u32(payload, 36),
            pcu_errors=_u16(payload, 40),
            activity_type=payload[43],
            alarm_level=payload[44],
            activity_level=payload[45],
            power_consumption=_u16(payload, 46),
            fan_speed_raw=payload[56] if len(payload) > 56 else None,
            hood_flags=payload[60] if len(payload) > 60 else None,
            light_raw=payload[53] if len(payload) > 53 else None,
            grease_filter=payload[59] if len(payload) > 59 else None,
        )


@dataclass(frozen=True)
class DeviceInfo:
    """Static device information from the Device Information service."""

    manufacturer: str
    model: str
    serial_number: str
    hardware_rev: str
    firmware_rev: str
    software_rev: str


@dataclass(frozen=True)
class WifiStatus:
    """A parsed CLOUD_WIFI_STATUS ("abd1") record."""

    ssid: str
    rssi: int  # dBm
    wifi_connection_status: int
    cloud_connection_status: int
    device_name: str
    local_ip: str

    @classmethod
    def from_bytes(cls, payload: bytes | bytearray) -> WifiStatus:
        if len(payload) < 75:
            raise ValueError(f"Wi-Fi status payload too short: {len(payload)}")
        payload = bytes(payload)
        rssi = int.from_bytes(payload[32:33], "little", signed=True)
        return cls(
            ssid=_ascii(payload, 0, 32),
            rssi=rssi,
            wifi_connection_status=payload[35],
            cloud_connection_status=payload[36],
            device_name=_ascii(payload, 43, 16),
            local_ip=".".join(str(b) for b in payload[71:75]),
        )
