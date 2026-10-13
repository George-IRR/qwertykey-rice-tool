"""
QwertyKey Rice Keyboard Protocol Definition
Reverse-engineered from QwertyKey_Rice_V3.exe
"""

VENDOR_ID = 0x0C45
PRODUCT_ID = 0x8016
INTERFACE_NUM = 0  # MI_00

REPORT_LENGTH = 65  # 1 byte report ID (0x00) + 64 bytes payload
CMD_DELAY = 0.035  # 35 milliseconds as defined in config

# Command Headers
CMD_CONFIG_ENTER   = bytes([0x04, 0x18])
CMD_CONFIG_INIT    = bytes([0x04, 0x13])
CMD_CONFIG_APPLY   = bytes([0x04, 0x02])
CMD_CONFIG_EXIT    = bytes([0x04, 0xF0])
CMD_TIME_INIT      = bytes([0x04, 0x28])
CMD_CUSTOM_RGB_INIT= bytes([0x04, 0x20])
CMD_CUSTOM_RGB_READ= bytes([0x04, 0xF5])
CMD_MACRO_ENTER    = bytes([0x04, 0x19])
CMD_MACRO_APPLY    = bytes([0x04, 0x15])
CMD_TFT_ENTER      = bytes([0x04, 0x72])
CMD_BATTERY_QUERY  = bytes([0x20, 0x01])

MAGIC_55AA = bytes([0xAA, 0x55])

# Lighting Modes Map
LIGHT_MODES = {
    0: {"name": "LED Off", "config_func": 0x00},
    1: {"name": "Static", "config_func": 0x31},
    2: {"name": "SingleOn", "config_func": 0x33},
    3: {"name": "SingleOff", "config_func": 0x33},
    4: {"name": "Glittering", "config_func": 0x33},
    5: {"name": "Falling", "config_func": 0x33},
    6: {"name": "Colourful", "config_func": 0x03},
    7: {"name": "Breath", "config_func": 0x33},
    8: {"name": "Spectrum", "config_func": 0x03},
    9: {"name": "Outward", "config_func": 0x33},
    10: {"name": "Scrolling", "config_func": 0x3B},
    11: {"name": "Rolling", "config_func": 0x37},
    12: {"name": "Rotating", "config_func": 0x37},
    13: {"name": "Explode", "config_func": 0x33},
    14: {"name": "Launch", "config_func": 0x33},
    15: {"name": "Ripples", "config_func": 0x33},
    16: {"name": "Flowing", "config_func": 0x37},
    17: {"name": "Pulsating", "config_func": 0x33},
    18: {"name": "Tilt", "config_func": 0x37},
    19: {"name": "Shuttle", "config_func": 0x33},
}

# Mode capability flags
FLAG_BRIGHTNESS = 0x01
FLAG_SPEED      = 0x02
FLAG_DIRECTION  = 0x04
FLAG_DIR_4WAY   = 0x08
FLAG_PALETTE    = 0x10
FLAG_COLORFUL   = 0x20

# Directions
DIR_LEFT_OR_TOP    = 1
DIR_RIGHT_OR_BOTTOM= 2

# Sleep time in minutes
SLEEP_TIMES = {
    0: "No Sleep",
    1: "1 minute",
    5: "5 minutes",
    30: "30 minutes",
}

# TFT Screen Specifications
TFT_WIDTH = 160
TFT_HEIGHT = 96
TFT_MAX_FRAMES = 255
TFT_CHUNK_SIZE = 4096
