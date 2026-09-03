"""BLE client for Safera Sense devices.

Uses bleak + bleak-retry-connector; contains no Home Assistant imports so
it can also be exercised standalone.

Command sequences are taken from the safera-ble and rorossense-ble
reverse engineering projects:
https://github.com/magicus/safera-ble
https://github.com/havardgulldahl/rorossense-ble
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    CHAR_CLOUD_WIFI_STATUS,
    CHAR_DAY_STATISTICS,
    CHAR_DCV_SENSOR_REPORT,
    CHAR_DEVICE_COMMAND,
    CHAR_EVENT_LOG,
    CHAR_FIRMWARE_REV,
    CHAR_GDT_DATA,
    CHAR_HARDWARE_REV,
    CHAR_LOG,
    CHAR_MANUFACTURER,
    CHAR_MODEL_NUMBER,
    CHAR_READ_CONFIG_BANK,
    CHAR_READ_SETTINGS,
    CHAR_SENSOR_REPORT,
    CHAR_SERIAL_NUMBER,
    CHAR_SOFTWARE_REV,
    CHAR_VOC,
    LEVEL_TO_RAW,
    DeviceCommand,
    FanSpeed,
    LightLevel,
)
from .models import DeviceInfo, SensorReport, WifiStatus

_LOGGER = logging.getLogger(__name__)


class SaferaSenseClient:
    """Client for one Safera Sense device."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClient | None = None
        self._report_callback: Callable[[SensorReport], None] | None = None
        self._lock = asyncio.Lock()
        self._last_tail: bytes | None = None
        self._first_report_logged = False

    @property
    def address(self) -> str:
        return self._ble_device.address

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLEDevice (e.g. after rediscovery via a proxy)."""
        self._ble_device = ble_device

    async def connect(
        self, disconnected_callback: Callable[[BleakClient], None] | None = None
    ) -> None:
        """Connect to the device (no-op when already connected)."""
        async with self._lock:
            if self.is_connected:
                return
            _LOGGER.debug("Connecting to %s", self.address)
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self._ble_device.address,
                disconnected_callback=disconnected_callback,
            )
            self._first_report_logged = False
            _LOGGER.debug("Connected to %s", self.address)

    async def disconnect(self) -> None:
        async with self._lock:
            client = self._client
            self._client = None
            if client is not None and client.is_connected:
                await client.disconnect()

    def _ensure_client(self) -> BleakClient:
        if not self.is_connected:
            raise ConnectionError(f"Not connected to {self.address}")
        assert self._client is not None
        return self._client

    # -- Pairing ---------------------------------------------------------

    @staticmethod
    def _is_auth_error(err: Exception) -> bool:
        """Return True for ATT security errors (insufficient auth/encryption)."""
        message = str(err).lower()
        return (
            "insufficient authentication" in message
            or "insufficient encryption" in message
            or "error=5 " in message
            or "error=15 " in message
        )

    async def pair(self) -> None:
        """Bond with the device (required for the proprietary characteristics)."""
        client = self._ensure_client()
        _LOGGER.debug("Pairing with %s", self.address)
        try:
            await client.pair()
        except NotImplementedError:
            # The macOS backend pairs automatically on demand.
            _LOGGER.debug("Backend pairs implicitly; continuing")
        except Exception as err:
            _LOGGER.debug("Pair attempt on %s returned: %s", self.address, err)

    async def _authed(self, func, /, *args, **kwargs):
        """Run a GATT operation, pairing and retrying once on auth errors."""
        try:
            return await func(*args, **kwargs)
        except Exception as err:
            if not self._is_auth_error(err):
                raise
            _LOGGER.info(
                "%s requires an encrypted link; pairing and retrying", self.address
            )
            await self.pair()
            return await func(*args, **kwargs)

    # -- Reading ---------------------------------------------------------

    async def _read_str(self, uuid: str) -> str:
        raw = await self._authed(self._ensure_client().read_gatt_char, uuid)
        return raw.decode("utf-8", "replace").strip("\x00").strip()

    async def fetch_device_info(self) -> DeviceInfo:
        """Read the standard Device Information service."""
        return DeviceInfo(
            manufacturer=await self._read_str(CHAR_MANUFACTURER),
            model=await self._read_str(CHAR_MODEL_NUMBER),
            serial_number=await self._read_str(CHAR_SERIAL_NUMBER),
            hardware_rev=await self._read_str(CHAR_HARDWARE_REV),
            firmware_rev=await self._read_str(CHAR_FIRMWARE_REV),
            software_rev=await self._read_str(CHAR_SOFTWARE_REV),
        )

    async def fetch_wifi_status(self) -> WifiStatus:
        raw = await self._authed(
            self._ensure_client().read_gatt_char, CHAR_CLOUD_WIFI_STATUS
        )
        return WifiStatus.from_bytes(raw)

    async def fetch_sensor_report(self) -> SensorReport:
        raw = await self._authed(
            self._ensure_client().read_gatt_char, CHAR_SENSOR_REPORT
        )
        return SensorReport.from_bytes(raw)

    # -- Notifications ---------------------------------------------------

    async def subscribe_sensor_reports(
        self, callback: Callable[[SensorReport], None]
    ) -> None:
        """Subscribe to SENSOR_REPORT notifications (roughly one per second)."""
        self._report_callback = callback
        await self._authed(
            self._ensure_client().start_notify,
            CHAR_SENSOR_REPORT,
            self._notification_handler,
        )

    def _notification_handler(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        if not self._first_report_logged:
            self._first_report_logged = True
            _LOGGER.debug(
                "First sensor report this connection (len=%d): %s",
                len(data),
                bytes(data).hex(":"),
            )
        self._log_report_tail(bytes(data))
        try:
            report = SensorReport.from_bytes(data)
        except ValueError as err:
            _LOGGER.debug("Ignoring unparseable sensor report: %s", err)
            return
        if self._report_callback is not None:
            self._report_callback(report)

    def _log_report_tail(self, data: bytes) -> None:
        """Debug-log the extended report bytes whenever they change.

        Bytes 48-50 and 53+ carry the hood state; several fields here
        are decoded (light step/brightness/colour-temp, fan speed,
        grease filter, auto flags) but some remain unknown (e.g. byte
        58), so this aids further reverse engineering. Bytes 51-52
        (radio link metrics) jitter and are excluded to avoid log spam.
        """
        tail = data[48:51] + data[53:]
        if tail == self._last_tail:
            return
        self._last_tail = tail
        _LOGGER.debug(
            "Report tail changed (len=%d): [48:51]=%s [53:]=%s",
            len(data),
            data[48:51].hex(":"),
            data[53:].hex(":"),
        )

    # -- Commands --------------------------------------------------------

    async def send_command(self, command: DeviceCommand | int, param: int) -> None:
        """Write an 8-byte command record to DEVICE_COMMAND ("babe")."""
        payload = int(command).to_bytes(4, "little") + (param & 0xFFFFFFFF).to_bytes(
            4, "little"
        )
        _LOGGER.debug("Command %s param=%s to %s", command, param, self.address)
        # The vendor app uses write-without-response for commands.
        await self._authed(
            self._ensure_client().write_gatt_char,
            CHAR_DEVICE_COMMAND,
            payload,
            response=False,
        )

    async def set_fan_speed(self, level: FanSpeed) -> None:
        """Set fan speed: OFF or levels 1-4.

        The hood exposes four speed steps (HOOD_MOTOR_SPEED_COUNT = 4);
        each level is a single SET_HOOD_MOTOR_SPEED_STEP write with a
        raw step of level * 30 (0/30/60/90/120). "Boost" is simply the
        top step, level 4.
        """
        await self.send_command(
            DeviceCommand.SET_HOOD_MOTOR_SPEED_STEP, LEVEL_TO_RAW[int(level)]
        )

    async def set_fan_auto(self) -> None:
        """Put the fan in automatic (air-quality controlled) mode."""
        await self.send_command(DeviceCommand.SET_HOOD_MOTOR_AUTO_MODE, 0x02)

    async def toggle_light_auto(self) -> None:
        """Toggle the light's automatic (presence-based) mode.

        Captured from the vendor app via DEVICE_COMMAND read-back: the
        same command and parameter are sent to enter AND leave auto
        mode, so callers should check SensorReport.light_auto first and
        only toggle when the current state differs from the target.
        """
        await self.send_command(DeviceCommand.SET_HOOD_LIGHT_AUTO_MODE, 0x02)

    async def set_light_level(self, level: LightLevel) -> None:
        """Set the hood light to OFF or levels 1-3."""
        await self.send_command(
            DeviceCommand.SET_HOOD_LIGHT_PRESET, LEVEL_TO_RAW[int(level)]
        )

    async def identify(self) -> None:
        """Ask the device to identify itself."""
        await self.send_command(DeviceCommand.IDENTIFY_DEVICE, 0)

    async def reset_grease_filter(self) -> None:
        """Tell the device the grease filter was cleaned/replaced."""
        await self.send_command(DeviceCommand.SET_HOOD_FILTER_CHANGED, 0)

    # -- Protocol investigation ------------------------------------------

    async def dump_characteristics(self) -> dict[str, str]:
        """Hex-dump every known readable characteristic.

        Used to hunt for not-yet-decoded fields (e.g. grease filter
        saturation). Returns {name: "aa:bb:..."} with errors inline.
        """
        targets = {
            # Read FIRST: DEVICE_COMMAND returns the LAST command the
            # device received (e.g. from the vendor app) — invaluable for
            # capturing unknown command parameters. It must be read
            # before this dump's own CONFIG_READ_BANK write below, which
            # would overwrite it.
            "DEVICE_COMMAND (babe)": CHAR_DEVICE_COMMAND,
            "SENSOR_REPORT (beef)": CHAR_SENSOR_REPORT,
            "READ_SETTINGS (dcba)": CHAR_READ_SETTINGS,
            "DAY_STATISTICS (abdf)": CHAR_DAY_STATISTICS,
            "EVENT_LOG (abcf)": CHAR_EVENT_LOG,
            "LOG (abcd)": CHAR_LOG,
            "VOC (abce)": CHAR_VOC,
            "GDT_DATA (abd2)": CHAR_GDT_DATA,
            "DCV_SENSOR_REPORT (abd4)": CHAR_DCV_SENSOR_REPORT,
            "CLOUD_WIFI_STATUS (abd1)": CHAR_CLOUD_WIFI_STATUS,
        }
        results: dict[str, str] = {}
        client = self._ensure_client()
        for name, uuid in targets.items():
            try:
                raw = await self._authed(client.read_gatt_char, uuid)
                results[name] = bytes(raw).hex(":")
            except Exception as err:
                results[name] = f"<unreadable: {err}>"
        # CONFIG_READ_BANK: the docs say bank 2 must be requested via a
        # command before reading the dcbb characteristic.
        try:
            await self.send_command(DeviceCommand.CONFIG_READ_BANK, 2)
            await asyncio.sleep(0.3)
            raw = await self._authed(client.read_gatt_char, CHAR_READ_CONFIG_BANK)
            results["CONFIG_BANK_2 (dcbb)"] = bytes(raw).hex(":")
        except Exception as err:
            results["CONFIG_BANK_2 (dcbb)"] = f"<unreadable: {err}>"
        return results
