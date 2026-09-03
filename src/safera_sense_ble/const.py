"""Constants for the Safera Sense BLE protocol.

Protocol knowledge reverse engineered by the rorossense-ble project:
https://github.com/havardgulldahl/rorossense-ble
"""

from __future__ import annotations

from enum import IntEnum

# The proprietary Safera service; its presence identifies a Safera device.
SAFERA_SERVICE_UUID = "0000f00d-1212-efde-1523-785fef13d123"

# Characteristics of the Safera service.
CHAR_SENSOR_REPORT = "0000beef-1212-efde-1523-785fef13d123"  # Read, Notify
CHAR_DEVICE_COMMAND = "0000babe-1212-efde-1523-785fef13d123"  # Read, Write
CHAR_CLOUD_WIFI_STATUS = "0000abd1-1212-efde-1523-785fef13d123"  # Read, Notify
CHAR_EVENT_LOG = "0000abcf-1212-efde-1523-785fef13d123"  # Read, Notify
CHAR_DAY_STATISTICS = "0000abdf-1212-efde-1523-785fef13d123"  # Read, Notify

# Undocumented / partially documented characteristics, read for diagnostics.
CHAR_LOG = "0000abcd-1212-efde-1523-785fef13d123"  # Read, Notify
CHAR_VOC = "0000abce-1212-efde-1523-785fef13d123"  # Read, Notify
CHAR_READ_SETTINGS = "0000dcba-1212-efde-1523-785fef13d123"  # Read
CHAR_READ_CONFIG_BANK = "0000dcbb-1212-efde-1523-785fef13d123"  # Read
CHAR_GDT_DATA = "0000abd2-1212-efde-1523-785fef13d123"  # Read, Write, Notify
CHAR_DCV_SENSOR_REPORT = "0000abd4-1212-efde-1523-785fef13d123"  # Read, Notify

# Standard Device Information service characteristics.
CHAR_MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
CHAR_MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
CHAR_SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
CHAR_HARDWARE_REV = "00002a27-0000-1000-8000-00805f9b34fb"
CHAR_FIRMWARE_REV = "00002a26-0000-1000-8000-00805f9b34fb"
CHAR_SOFTWARE_REV = "00002a28-0000-1000-8000-00805f9b34fb"


class DeviceCommand(IntEnum):
    """DEVICE_COMMAND ("babe") command codes.

    The characteristic takes an 8-byte record: a 32-bit little-endian
    command code followed by a 32-bit little-endian parameter.
    """

    BT_KEEP_ALIVE = 0x1002
    SET_CLOCK_UNIX = 0x1005
    IDENTIFY_DEVICE = 0x1018
    CONFIG_READ_BANK = 0x101B
    SET_HOOD_MOTOR_SPEED_STEP = 0x2001
    SET_HOOD_MOTOR1_SPEED_RAW = 0x2002
    SET_HOOD_MOTOR2_SPEED_RAW = 0x2003
    SET_HOOD_MOTOR_AUTO_MODE = 0x2004
    SET_HOOD_LIGHT_PRESET = 0x2005
    SET_HOOD_LIGHT_BRIGHTNESS = 0x2006
    SET_HOOD_LIGHT_TEMPERATURE = 0x2007
    SET_HOOD_LIGHT_AUTO_MODE = 0x2008
    SET_HOOD_FILTER_CHANGED = 0x2009


class DeviceState(IntEnum):
    """Values of the SENSOR_REPORT device_state field."""

    NONE = 0x00
    START = 0x01
    IDLE = 0x02
    SELF_CHECK = 0x03
    PAIRING_RCL2 = 0x05
    PAIRING_BLE = 0x06
    POWEROFF_WARNING = 0x07
    POWEROFF = 0x08
    FIRE_WARNING = 0x09
    FIRE = 0x0A
    LOCKED_WARNING = 0x0B
    LOCKED_POWEROFF = 0x0C
    LOCKOFF_POWER_CHECK = 0x0D
    LOCKOFF_POWER_CHECK_WARN = 0x0E
    CURRENT_CAL = 0x0F
    REMOTE_MAINTENANCE = 0x10


# States in which the device is warning about or reacting to a hazard.
ALARM_DEVICE_STATES = {
    DeviceState.POWEROFF_WARNING,
    DeviceState.POWEROFF,
    DeviceState.FIRE_WARNING,
    DeviceState.FIRE,
    DeviceState.LOCKED_WARNING,
    DeviceState.LOCKED_POWEROFF,
}


class ActivityType(IntEnum):
    """Values of the SENSOR_REPORT activity_type field."""

    IDLE = 0
    COOKING = 2


class FanSpeed(IntEnum):
    """Logical fan speed levels."""

    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    BOOST = 4


class LightLevel(IntEnum):
    """Logical light levels."""

    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


# Fan/light levels are sent as raw "step" parameters in units of 30.
LEVEL_TO_RAW = {0: 0, 1: 30, 2: 60, 3: 90, 4: 120}

SENSOR_ERROR_FLAGS = {
    0x0001: "Temp Sensor",
    0x0002: "TOF Sensor",
    0x0004: "ADC Sensor",
    0x0008: "Gas Sensor A",
    0x0010: "Gas Sensor B",
    0x0020: "Particle Sensor",
    0x0040: "Orientation Sensor",
    0x0080: "Humidity Sensor",
    0x0100: "Orientation",
    0x0200: "Battery Low",
    0x0400: "Paired PCU missing",
    0x0800: "Processor Error",
    0x1000: "Sensor Lens Dirty",
    0x2000: "Battery Critically Low",
    0x4000: "External Memory",
    0x8000: "IO Expander",
}

PCU_ERROR_FLAGS = {
    0x0001: "Volt Meas",
    0x0002: "Cur Meas",
    0x0004: "Water Meas",
    0x0008: "Processor",
    0x0010: "Temp Sensor",
    0x0020: "Power Supply",
    0x0040: "Relay",
    0x0080: "Overheat",
    0x0400: "Overcurrent",
}
