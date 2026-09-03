"""Command encoding tests.

The expected byte sequences were sniffed from the vendor app by the
rorossense-ble project (https://github.com/havardgulldahl/rorossense-ble).
"""

from unittest.mock import AsyncMock

import pytest

from safera_sense_ble import DeviceCommand, FanSpeed, LightLevel, SaferaSenseClient
from safera_sense_ble.const import CHAR_DEVICE_COMMAND


@pytest.fixture
def client() -> SaferaSenseClient:
    ble_device = AsyncMock()
    ble_device.address = "AA:BB:CC:DD:EE:FF"
    safera = SaferaSenseClient(ble_device)
    bleak_client = AsyncMock()
    bleak_client.is_connected = True
    safera._client = bleak_client
    return safera


def written_payloads(client: SaferaSenseClient) -> list[bytes]:
    return [
        bytes(call.args[1])
        for call in client._client.write_gatt_char.await_args_list
        if call.args[0] == CHAR_DEVICE_COMMAND
    ]


async def test_command_encoding(client: SaferaSenseClient) -> None:
    await client.send_command(DeviceCommand.SET_HOOD_MOTOR_SPEED_STEP, 0x5A)
    assert written_payloads(client) == [bytes([0x01, 0x20, 0, 0, 0x5A, 0, 0, 0])]


async def test_fan_levels(client: SaferaSenseClient) -> None:
    await client.set_fan_speed(FanSpeed.OFF)
    await client.set_fan_speed(FanSpeed.LEVEL_1)
    await client.set_fan_speed(FanSpeed.LEVEL_3)
    assert written_payloads(client) == [
        bytes([0x01, 0x20, 0, 0, 0x00, 0, 0, 0]),
        bytes([0x01, 0x20, 0, 0, 0x1E, 0, 0, 0]),
        bytes([0x01, 0x20, 0, 0, 0x5A, 0, 0, 0]),
    ]


async def test_fan_boost_sequence(client: SaferaSenseClient) -> None:
    await client.set_fan_speed(FanSpeed.BOOST)
    assert written_payloads(client) == [
        bytes([0x01, 0x20, 0, 0, 0x78, 0, 0, 0]),
        bytes([0x02, 0x10, 0, 0, 0x78, 0, 0, 0]),
    ]


async def test_fan_auto(client: SaferaSenseClient) -> None:
    await client.set_fan_auto()
    assert written_payloads(client) == [bytes([0x04, 0x20, 0, 0, 0x02, 0, 0, 0])]


async def test_light_levels(client: SaferaSenseClient) -> None:
    await client.set_light_level(LightLevel.LEVEL_2)
    assert written_payloads(client) == [bytes([0x05, 0x20, 0, 0, 0x3C, 0, 0, 0])]


async def test_grease_filter_reset(client: SaferaSenseClient) -> None:
    await client.reset_grease_filter()
    assert written_payloads(client) == [bytes([0x09, 0x20, 0, 0, 0, 0, 0, 0])]


async def test_identify(client: SaferaSenseClient) -> None:
    await client.identify()
    assert written_payloads(client) == [bytes([0x18, 0x10, 0, 0, 0, 0, 0, 0])]
