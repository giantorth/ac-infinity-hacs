"""Constants for the ac_infinity integration."""
from bleak.exc import BleakError

DOMAIN = "ac_infinity"

DEVICE_TIMEOUT = 30
UPDATE_SECONDS = 15

BLEAK_EXCEPTIONS = (AttributeError, BleakError, TimeoutError)

DEVICE_MODEL = {
    1: "Controller 67",
    6: "AIRTAP T6",
    7: "Controller 69",
    11: "Controller 69 Pro",
}

WORK_TYPE_TO_RAW = {
    "AUTO": 3,
    "ON": 2,
    "OFF": 1,
    "CYCLE": 6,
    "TIMER": 4,
}

WORK_TYPE_FROM_RAW = {v: k.capitalize() for k, v in WORK_TYPE_TO_RAW.items()}
