"""safera-sense-ble: BLE client library for Safera Sense cooking sensors.

Protocol reverse engineering by magicus
(https://github.com/magicus/safera-ble) and Håvard Gulldahl
(https://github.com/havardgulldahl/rorossense-ble); this library is an
independent implementation with additional findings (BLE bonding
requirement, grease filter field, PM2.5 interpretation).
"""

from .client import SaferaSenseClient
from .const import (
    ALARM_DEVICE_STATES,
    SAFERA_SERVICE_UUID,
    ActivityType,
    DeviceCommand,
    DeviceState,
    FanSpeed,
    LightLevel,
)
from .models import DeviceInfo, SensorReport, WifiStatus

__version__ = "0.2.0"

__all__ = [
    "ALARM_DEVICE_STATES",
    "SAFERA_SERVICE_UUID",
    "ActivityType",
    "DeviceCommand",
    "DeviceInfo",
    "DeviceState",
    "FanSpeed",
    "LightLevel",
    "SaferaSenseClient",
    "SensorReport",
    "WifiStatus",
    "__version__",
]
