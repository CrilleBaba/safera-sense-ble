"""safera-sense-ble: BLE client library for Safera Sense cooking sensors.

Protocol reverse engineering by Håvard Gulldahl
(https://github.com/havardgulldahl/rorossense-ble); this library is an
independent implementation with additional findings (BLE bonding
requirement, grease filter saturation field).
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
