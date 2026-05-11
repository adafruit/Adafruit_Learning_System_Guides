# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''MagicBand+ BLE protocol constants and helpers.

Shared between the CLUE transmitter and the QT Py S3 receiver. Based on the
reverse-engineering work at:
  https://emcot.world/Disney_MagicBand%2B_Bluetooth_Codes

All command payloads stored here are the manufacturer-data portion only (the
bytes after the 0x0183 Disney CID). The transmitter prepends the CID bytes
when building a BLE advertisement packet.
'''
# Target: shared between the Adafruit CLUE (BLE remote) and the Adafruit
# QT Py ESP32-S3 (BLE Beacon Ears) - copy this file to both boards.

# Disney's Bluetooth SIG company identifier.
DISNEY_CID = 0x0183

# 5-bit color palette. Values are RGB approximations calibrated for how the
# colors look on a NeoPixel Jewel at low brightness (~0.05). Green and blue
# channels look brighter per unit input than red on WS2812B LEDs, so cyan
# values have their red channel boosted to compensate, and blue hues get
# pushed toward their characteristic hue rather than a balanced RGB.
PALETTE_RGB = (
    (80, 255, 255),   # 0x00 cyan (red channel boosted so it's not pure teal)
    (180, 0, 255),    # 0x01 purple
    (0, 0, 255),      # 0x02 blue
    (0, 20, 120),     # 0x03 midnight blue (touch of green stops it looking black)
    (40, 120, 255),   # 0x04 blue 2
    (200, 80, 255),   # 0x05 bright purple
    (200, 180, 255),  # 0x06 lavender
    (120, 0, 255),    # 0x07 deep purple
    (255, 60, 180),   # 0x08 pink
    (255, 70, 170),   # 0x09 pink 2
    (255, 80, 160),   # 0x0A pink 3
    (255, 90, 150),   # 0x0B pink 4
    (255, 110, 150),  # 0x0C pink 5
    (255, 130, 160),  # 0x0D pink 6
    (255, 160, 170),  # 0x0E pink 7
    (255, 180, 0),    # 0x0F yellow orange
    (255, 220, 0),    # 0x10 off yellow
    (255, 140, 20),   # 0x11 yellow orange 2
    (180, 255, 0),    # 0x12 lime
    (255, 90, 0),     # 0x13 orange
    (255, 40, 0),     # 0x14 red orange
    (255, 0, 0),      # 0x15 red
    (60, 255, 255),   # 0x16 cyan 2 (red boost for distinctness from green)
    (40, 240, 255),   # 0x17 cyan 3
    (20, 200, 255),   # 0x18 cyan 4 (shifts more toward blue)
    (0, 255, 0),      # 0x19 green
    (80, 255, 40),    # 0x1A lime green
    (255, 200, 180),  # 0x1B white (warm white avoids blue cast at low levels)
    (255, 200, 180),  # 0x1C white 2
    (0, 0, 0),        # 0x1D off
    (255, 140, 60),   # 0x1E unique
    (255, 0, 255),    # 0x1F random / magenta
)

PALETTE_NAMES = (
    "Cyan", "Purple", "Blue", "Midnight Blue",
    "Blue 2", "Bright Purple", "Lavender", "Deep Purple",
    "Pink", "Pink 2", "Pink 3", "Pink 4",
    "Pink 5", "Pink 6", "Pink 7", "Yellow Orange",
    "Off Yellow", "Yellow Orange 2", "Lime", "Orange",
    "Red Orange", "Red", "Cyan 2", "Cyan 3",
    "Cyan 4", "Green", "Lime Green", "White",
    "White 2", "Off", "Unique", "Random",
)

# Mask palette: which of the 5 LEDs light up for a given 3-bit mask.
# Tuple order: (center, top_left, top_right, bottom_left, bottom_right)
MASK_LEDS = {
    0b000: (1, 1, 1, 1, 1),
    0b001: (0, 0, 1, 0, 0),
    0b010: (0, 0, 0, 0, 1),
    0b011: (0, 0, 0, 1, 0),
    0b100: (0, 1, 0, 0, 0),
    0b101: (1, 1, 1, 1, 1),
    0b110: (0, 0, 1, 0, 0),
    0b111: (1, 1, 1, 1, 1),
}


def decode_timing(byte):
    '''Turn the timing byte into a dict of animation parameters.'''
    scaler_b = bool(byte & 0x40)
    time_val = byte & 0x0F
    if scaler_b:
        seconds = 3.1 * time_val + 5.5
    else:
        seconds = 1.5 * time_val + 6.5
    return {
        "always_on": bool(byte & 0x80),
        "fade_code": (byte >> 4) & 0x03,
        "seconds": seconds,
    }


def build_single_color(palette_idx, mask=0, vibration=0, timing=0x09):
    '''Build an E9 05 single-color-from-palette command payload.'''
    color_byte = ((mask & 0x07) << 5) | (palette_idx & 0x1F)
    vib_byte = 0xB0 | (vibration & 0x0F)
    return bytes((0xE1, 0x00, 0xE9, 0x05, 0x00, timing, 0x0E,
                  color_byte, vib_byte))


def build_dual_color(inner_idx, outer_idx, vibration=0, timing=0x22):
    '''Build an E9 06 dual-color command payload.

    Note: the emcot wiki spec text says the top 3 bits of each color byte
    should be 0b100, but the wiki's own example payloads use 0b010. Using
    0b100 causes the top-left LED to be masked off (same bits the E9 05
    mask palette uses for "top left only"). The correct working value
    per the captured examples is 0b010 / 0x40.
    '''
    inner_byte = 0x40 | (inner_idx & 0x1F)
    outer_byte = 0x40 | (outer_idx & 0x1F)
    vib_byte = 0xB0 | (vibration & 0x0F)
    return bytes((0xE2, 0x00, 0xE9, 0x06, 0x00, timing, 0x0F,
                  inner_byte, outer_byte, vib_byte))


def build_six_bit_color(red, green, blue, vibration=0, timing=0x0E):
    '''Build an E9 08 raw 6-bit RGB command payload.'''
    red_byte = (red & 0x3F) << 1
    green_byte = (green & 0x3F) << 1
    blue_byte = (blue & 0x3F) << 1
    vib_byte = 0xB0 | (vibration & 0x0F)
    return bytes((0xE1, 0x00, 0xE9, 0x08, 0x00, timing, 0xD2, 0x55,
                  red_byte, green_byte, blue_byte, vib_byte))


def build_five_color(center, top_left, bottom_left, bottom_right, top_right,
                    vibration=0, timing=0x0E):
    '''Build an E9 09 five-color-palette command payload.

    Each of the band's 5 LEDs gets its own palette slot. Order matches the
    emcot wiki byte order: center, bottom-left, bottom-right, top-right,
    top-left (reading outer ring counter-clockwise from top-left).
    '''
    def _color_byte(idx):
        return 0xA0 | (idx & 0x1F)
    vib_byte = 0xB0 | (vibration & 0x0F)
    return bytes((0xE1, 0x00, 0xE9, 0x09, 0x00, timing, 0x0F,
                  _color_byte(top_left),
                  _color_byte(bottom_left),
                  _color_byte(bottom_right),
                  _color_byte(top_right),
                  _color_byte(center),
                  vib_byte))


# Starlight Bubble Wand BLE protocol (reverse-engineered April 2026).
# 13-byte packets. First 6 bytes are a fixed signature identifying the
# wand and the "cast color" command. Bytes 6-11 contain a rolling code
# (probably anti-replay authentication) that changes on every broadcast.
# Byte 12 is the palette index - same table as the MagicBand+ palette.
#
# We only check the first 6 bytes to recognize a wand packet. The rolling
# middle bytes cannot be replayed (they would fail the wand's own checks
# if sent back), so we read them but don't try to decode or broadcast
# them ourselves.
WAND_SIGNATURE = bytes.fromhex("cf0b00c42022")
WAND_PAYLOAD_LENGTH = 13
WAND_COLOR_INDEX = 12


def is_wand_packet(payload):
    '''Return True if this payload is a Starlight Bubble Wand cast.'''
    return (len(payload) == WAND_PAYLOAD_LENGTH
            and bytes(payload[:len(WAND_SIGNATURE)]) == WAND_SIGNATURE)


def parse_wand(payload):
    '''Decode a wand cast packet into a structured command dict.'''
    if not is_wand_packet(payload):
        return None
    palette_idx = payload[WAND_COLOR_INDEX] & 0x1F
    return {
        "kind": "wand_cast",
        "palette_idx": palette_idx,
        "raw": bytes(payload),
    }


# Fab 50 statue beacons. The Disney Fab 50 golden statues placed around
# Magic Kingdom broadcast 0xC4 packets to assist guest location services.
# Two sub-formats: C4 10 (18 bytes) and C4 15 (22 bytes). Both contain
# an ASCII 2-digit statue ID at offset 15-16 (e.g. "53", "40", "24").
# Triggering a golden-swirl animation when these are detected gives the
# wearable a thematic "the statue sees you" reaction.
_STATUE_PREFIX = bytes.fromhex("c4")


def _is_statue_beacon(payload):
    '''Return True if this payload looks like a Fab 50 statue beacon.'''
    if not payload or payload[0] != 0xC4:
        return False
    # Two known formats: C4 10 (18 bytes) and C4 15 (23 bytes)
    return len(payload) in (18, 23)


def _parse_statue_beacon(payload):
    '''Decode a statue beacon to extract its 2-digit ASCII identifier.'''
    statue_id = "?"
    # Statue ID is at offset 15-16 in both 18- and 22-byte variants
    if len(payload) >= 17:
        try:
            statue_id = bytes(payload[15:17]).decode("ascii")
        except (UnicodeError, ValueError):
            statue_id = "?"
    return {
        "kind": "statue_beacon",
        "statue_id": statue_id,
        "raw": bytes(payload),
    }


# Park show command opcodes - direct E9/EA family with no E1 00 wrapper.
# Captured from Disney park show infrastructure (Epcot, April 2026). These
# coexist with guest-fired E1/E2 commands but use a different byte layout.
# Long-format variants (E9 10, E9 13, EA 14) share a `f4 48 82` signature
# in the middle of the payload; their byte structure isn't fully decoded
# yet. The E9 08 short form decodes cleanly as a 5-slot palette command.
_SHOW_OPCODE_LABELS = {
    (0xE9, 0x04): "E9 04",
    (0xE9, 0x08): "E9 08 5-slot",
    (0xE9, 0x10): "E9 10",
    (0xE9, 0x13): "E9 13",
    (0xEA, 0x14): "EA 14",
}


def _parse_show_command(payload):
    '''Parse a direct E9/EA show packet captured from park infrastructure.'''
    if len(payload) < 2:
        return None
    head = payload[0]
    sub = payload[1]
    label = _SHOW_OPCODE_LABELS.get((head, sub))
    if label is None:
        return None
    # E9 08 short form is a 5-slot palette command. Bytes 5-9 are masked
    # with 0x1F to extract palette indices, identical to the existing E9
    # 09 five-color decode. Confirmed by capture 9 (blue green) decoding
    # to Cyan/Blue 2/Green/Green/Blue 2 - matching the observed color.
    slots = None
    if (head == 0xE9 and sub == 0x08
            and len(payload) >= 10 and payload[4] == 0x0F):
        slots = [payload[5 + i] & 0x1F for i in range(5)]
    return {
        "kind": "show_command",
        "label": label,
        "head": head,
        "sub": sub,
        "slots": slots,
        "raw": bytes(payload),
    }


def _parse_by_head(payload):
    '''Decode a payload that's not a wand cast or statue beacon.'''
    head = payload[0]
    if head == 0xCC:
        return {"kind": "ping", "raw": payload}
    if head in (0xE9, 0xEA):
        show_cmd = _parse_show_command(payload)
        if show_cmd is not None:
            return show_cmd
    if head in (0xE1, 0xE2):
        return _parse_e1_e2(payload)
    return {"kind": "unknown", "raw": payload}


def parse(payload):
    '''Decode a manufacturer-data payload into a structured command dict.

    Used by the QT Py receiver to interpret commands from MagicBands, the
    CLUE remote, the Starlight Bubble Wand, and Disney park infrastructure
    (Fab 50 statues, parade beacons).
    '''
    if not payload:
        return None
    # Wand packets have a distinctive 6-byte header signature
    wand = parse_wand(payload)
    if wand is not None:
        return wand
    # Fab 50 statue beacons (Magic Kingdom hub area)
    if _is_statue_beacon(payload):
        return _parse_statue_beacon(payload)
    return _parse_by_head(payload)


def _parse_single_color(payload):
    color_byte = payload[7]
    return {
        "kind": "single_color",
        "mask": (color_byte >> 5) & 0x07,
        "palette_idx": color_byte & 0x1F,
        "timing": decode_timing(payload[5]),
        "vibration": payload[8] & 0x0F,
    }


def _parse_dual_color(payload):
    return {
        "kind": "dual_color",
        "inner_idx": payload[7] & 0x1F,
        "outer_idx": payload[8] & 0x1F,
        "timing": decode_timing(payload[5]),
        "vibration": payload[9] & 0x0F,
    }


def _parse_six_bit(payload):
    return {
        "kind": "six_bit_color",
        "red": (payload[8] >> 1) & 0x3F,
        "green": (payload[9] >> 1) & 0x3F,
        "blue": (payload[10] >> 1) & 0x3F,
        "timing": decode_timing(payload[5]),
        "vibration": payload[11] & 0x0F,
    }


def _parse_five_color(payload):
    '''E9 09 layout: TL BL BR TR C VIB starting at index 7.'''
    return {
        "kind": "five_color",
        "top_left": payload[7] & 0x1F,
        "bottom_left": payload[8] & 0x1F,
        "bottom_right": payload[9] & 0x1F,
        "top_right": payload[10] & 0x1F,
        "center": payload[11] & 0x1F,
        "timing": decode_timing(payload[5]),
        "vibration": payload[12] & 0x0F,
    }


# Function-code dispatch for E1/E2-wrapped payloads. Each entry maps
# the 2-byte function code (payload[2]<<8 | payload[3]) to (min_length,
# parser_or_kind). When the parser slot is a callable, it's invoked with
# the payload; when it's a string, a generic {"kind": ..., "raw": ...}
# dict is returned. Defined at module bottom so all _parse_* helpers
# already exist when this dict is built at import time.
_FUNC_CODE_DISPATCH = {
    0xE905: (9, _parse_single_color),
    0xE906: (10, _parse_dual_color),
    0xE908: (12, _parse_six_bit),
    0xE909: (13, _parse_five_color),
    0xE90C: (5, "show_fx"),
    0xE911: (5, "cross_fade"),
    # Newer parade/show command not in our protocol docs. We can't
    # decode the colors but still want the ears to react visibly.
    0xCD07: (5, "parade_command"),
}


def _parse_e1_e2(payload):
    '''Decode an E1/E2-wrapped payload by its function code.'''
    if len(payload) < 5:
        return {"kind": "unknown", "raw": payload}
    func = (payload[2] << 8) | payload[3]
    entry = _FUNC_CODE_DISPATCH.get(func)
    if entry is None:
        return {"kind": "animation", "func": func, "raw": payload}
    min_len, handler = entry
    if len(payload) < min_len:
        return {"kind": "animation", "func": func, "raw": payload}
    if callable(handler):
        return handler(payload)
    return {"kind": handler, "raw": payload}
