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
    CookingEventType,
    DeviceCommand,
    DeviceState,
    FanSpeed,
    LightLevel,
)
from .models import (
    CookingEvent,
    DeviceInfo,
    SensorReport,
    WifiStatus,
    parse_event_log,
)

__version__ = "0.3.0"

__all__ = [
    "ALARM_DEVICE_STATES",
    "SAFERA_SERVICE_UUID",
    "ActivityType",
    "CookingEvent",
    "CookingEventType",
    "DeviceCommand",
    "DeviceInfo",
    "DeviceState",
    "FanSpeed",
    "LightLevel",
    "SaferaSenseClient",
    "SensorReport",
    "WifiStatus",
    "__version__",
    "parse_event_log",
]
