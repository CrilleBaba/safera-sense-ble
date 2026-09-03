"""Parser tests based on real captures from an IFU10CR-PRO (fw 13/75)."""

import pytest

from safera_sense_ble import DeviceState
from safera_sense_ble.models import SensorReport, WifiStatus

# Captured 2026-09-02 while the vendor app showed 6% grease filter.
REPORT_FILTER_6PCT = bytes.fromhex(
    "231c721c0416da07430c090009000aba014b0000000000001100"
    "64ff00ef001e0002000081687000000003000001000000000100"
    "0000000000000d060000000000000000ff"
)

# Captured minutes later, right after the filter was reset in the app.
REPORT_FILTER_RESET = bytes.fromhex(
    "291c5f1c0d169b15430b0a0009000dba01760000010000001000"
    "64ff00ef001e000200006b6a7000000003000001000000000100"
    "0000000000000d000000000000000000ff"
)

WIFI_STATUS = bytes.fromhex(
    "556e6966692b0a00000000000000000000000000000000000000"
    "000000000000bb010003010403a86d976a53656e73655f304130"
    "4237430000000000000000000000000000000000000000000000"
    "00312e3100000000000000000000000000"
)


def test_report_lengths() -> None:
    assert len(REPORT_FILTER_6PCT) == 69
    assert len(REPORT_FILTER_RESET) == 69


def test_sensor_report_documented_fields() -> None:
    report = SensorReport.from_bytes(REPORT_FILTER_6PCT)
    # Values are quantized to meaningful precision (0.1 degC, 1 %RH, 1 lx).
    assert report.ambient_temperature == pytest.approx(22.0)
    assert report.surface_temperature == pytest.approx(22.8)
    assert report.humidity == 56
    assert report.ambient_light == 63
    assert report.mounting_height == 67
    assert report.air_quality_index == 9
    assert report.co2_ppm == 442
    assert report.tvoc_ppb == 75
    assert report.heat_index == 34
    assert report.battery_level == 100
    assert report.device_state == DeviceState.IDLE
    assert report.sensor_errors == 0
    assert report.power_consumption == 0
    assert report.fan_speed_level == 0
    assert report.light_level == 0


def test_grease_filter_field() -> None:
    """Byte 59 is grease filter saturation %; zeroes on app reset."""
    assert SensorReport.from_bytes(REPORT_FILTER_6PCT).grease_filter == 6
    assert SensorReport.from_bytes(REPORT_FILTER_RESET).grease_filter == 0


def test_bare_54_byte_report_has_no_hood_fields() -> None:
    report = SensorReport.from_bytes(REPORT_FILTER_6PCT[:54])
    assert report.grease_filter is None
    assert report.fan_speed_raw is None
    assert report.fan_auto is None
    # Byte 53 is present in a 54-byte record.
    assert report.light_raw == 0


def test_short_report_rejected() -> None:
    with pytest.raises(ValueError):
        SensorReport.from_bytes(REPORT_FILTER_6PCT[:53])


def test_particle_index_one_decimal() -> None:
    """PM2.5 keeps the raw record's 0.2 ug/m3 resolution."""
    payload = bytearray(REPORT_FILTER_6PCT)
    payload[12:14] = (56).to_bytes(2, "little")
    assert SensorReport.from_bytes(payload).particle_index == pytest.approx(11.2)


def test_light_auto_mode() -> None:
    payload = bytearray(REPORT_FILTER_6PCT)
    payload[53] = 100
    report = SensorReport.from_bytes(payload)
    assert report.light_auto is True
    assert report.light_level is None


def test_fan_boost_level() -> None:
    payload = bytearray(REPORT_FILTER_6PCT)
    payload[60] = 120
    assert SensorReport.from_bytes(payload).fan_speed_level == 4


def test_wifi_status() -> None:
    status = WifiStatus.from_bytes(WIFI_STATUS)
    assert status.ssid == "Unifi+"
    assert status.rssi == -69
    assert status.device_name == "Sense_0A0B7C"


def test_sensor_error_messages() -> None:
    payload = bytearray(REPORT_FILTER_6PCT)
    payload[34:36] = (0x1001).to_bytes(2, "little")
    report = SensorReport.from_bytes(payload)
    assert report.sensor_error_messages == ["Temp Sensor", "Sensor Lens Dirty"]
