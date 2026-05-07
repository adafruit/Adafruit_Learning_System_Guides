# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Named MagicBand+ command library organized into categories.

Each command is a (name, payload, needs_ping) tuple where needs_ping is
True if a 0.5s CC03 wake ping should be broadcast before the real command
to prime the band's receiver. Commands observed to latch reliably on first
try are marked False. The transmitter prepends the 0x0183 Disney CID to
payload bytes when advertising.
'''
# Target: Adafruit CLUE (nRF52840) - the BLE remote
from magicband_protocol import (
    PALETTE_NAMES,
    build_dual_color,
    build_single_color,
)

# Wake-ping broadcast continuously by park beacons. Keeps the band's radio
# in high-response mode so the real command latches on the first shot.
PING_PAYLOAD = bytes.fromhex("cc03000000")

# OFF/cancel command. No pre-ping so cancellation is immediate.
OFF_COMMAND = ("Off", build_single_color(0x1D), False)

# Palette slots that look identical to another, produce no visible effect
# on the band, or duplicate other menu actions. 0x1D (Off) is redundant
# with the B-hold cancel shortcut; 0x1E (Unique) has no visible effect.
_SKIPPED_PALETTE = (0x09, 0x0C, 0x17, 0x18, 0x1C, 0x1D, 0x1E)

# Singles confirmed to latch first-try on a real band (no ping needed).
_RELIABLE_SINGLES = {0x02, 0x05}

SINGLE_COLOR = tuple(
    (name, build_single_color(idx), idx not in _RELIABLE_SINGLES)
    for idx, name in enumerate(PALETTE_NAMES)
    if idx not in _SKIPPED_PALETTE
)

DUAL_COLOR = (
    ("Red & Blue", build_dual_color(0x15, 0x02), True),
    ("Orange & Cyan", build_dual_color(0x13, 0x16), False),
    ("Pink & Lime", build_dual_color(0x08, 0x12), True),
    ("Purple & Yellow", build_dual_color(0x01, 0x0F), True),
    ("Green & Red", build_dual_color(0x19, 0x15), False),
    ("Cyan & Orange", build_dual_color(0x16, 0x13), True),
    ("White & Blue", build_dual_color(0x1B, 0x02), True),
    ("Lavender & Pink", build_dual_color(0x06, 0x08), True),
)

# Combined Colors category - Dual Color pairs first (more visually striking)
# followed by Single Color palette entries.
COLORS = DUAL_COLOR + SINGLE_COLOR

# All captured park show codes latch first-try - they're the packets the
# band's firmware was specifically designed to recognize.
# The * suffix marks commands that trigger the band's vibration motor.
SHOW_FX = (
    ("Taste the Rainbow",
     bytes.fromhex("e100e90c000f0f5d465bf005323748b0"), False),
    ("Blink White *",
     bytes.fromhex("e100e90c000f0f5d465bf00532374895"), False),
    # Orange Blink's timing byte (0xEF) has the always-on flag set, so this
    # command runs indefinitely until another command or OFF is sent. The
    # other E9 0C shows use timing 0x0F for ~29s runtime then auto-stop.
    # Intentional: Orange Blink doubles as a persistent "alert mode" beacon.
    ("Orange Blink *",
     bytes.fromhex("e100e90c00ef0f4f4f5bf0fb14374895"), False),
    ("5 Palette Cycle",
     bytes.fromhex("e100e90c000f0fb1b9b5b1a2307b7db0"), False),
    # DCL Rainbow - cloned from 5 Palette Cycle with DCL brand colors
    # and long buzz. Navy / Yellow / Red / Navy / Yellow.
    ("DCL Rainbow *",
     bytes.fromhex("e100e90c000f0fa3afb5a3af307b7db7"), False),
    # Custom sub-protocol: Ears Battery shows the QT Py wearable's
    # current battery level on its NeoPixel jewels (not visible on
    # the CLUE itself - this is a remote trigger for the receiver).
    ("Ears Battery",
     bytes.fromhex("aa4201"), False),
    # Custom sub-protocol: cycle the QT Py ears through their
    # brightness presets (dim / medium / bright). Useful between
    # daytime and night usage without touching the headband.
    ("Ears Brightness",
     bytes.fromhex("aa4203"), False),
    # Custom sub-protocol: "Find Me" stroller/scooter beacon. Triggers
    # a ~30 second high-visibility 3-phase animation on the wearable
    # (strobe, rainbow chase, breathing) at maximum brightness so you
    # can spot a parked stroller, wheelchair, or EV scooter from across
    # a busy parking lot. Forces max brightness regardless of preset,
    # then restores the preset after the animation ends.
    ("Find Me",
     bytes.fromhex("aa4204"), False),
    # Custom sub-protocol: preview the Fab 50 statue golden-swirl
    # animation on demand. Same animation that real Magic Kingdom
    # statue beacons trigger on the receiver - useful for video shoots
    # and demos without needing a statue beacon nearby.
    ("Ears Statue",
     bytes.fromhex("aa4205"), False),
    # Sentinel entry: when fired, code.py recognizes the LISTEN_MODE
    # marker and transitions to listen-mode UI instead of broadcasting.
    # Captures all unique Disney 0x0183 packets to a file. Useful for
    # reverse-engineering new park show packets (Spaceship Earth,
    # Starlight Parade, etc.).
    ("Listen Mode",
     b"LISTEN", False),
)

# Cross fades 3 and 5 use scaler=0 timing and latch first-try. The others
# use scaler=1 (3.1x multiplier) for long park-show durations and need
# the wake ping to prime the receiver.
CROSS_FADE = (
    ("Cyan to Pink",
     bytes.fromhex("e100e911006f0f564858f44882d1460208d06500b0"), True),
    ("Blue to Yellow",
     bytes.fromhex("e200e911004f0f444f58f44882d1460607d06543b0"), True),
    ("Pink to Green",
     bytes.fromhex("e100e911000f0f485958f44882d146020dd06505b0"), False),
    ("Orange to Red",
     bytes.fromhex("e200e911004f0f4f5558f44882d146022ad06501b0"), True),
    ("Lime to Purple",
     bytes.fromhex("e100e91100010f5a475bf03134374894d13d0507b0"), False),
    ("Red to Off",
     bytes.fromhex("e100e91100070f555d58f44882d1460508d06500b0"), True),
    ("Orange to Blue",
     bytes.fromhex("e100e91100440f514258f44882d146050fd06500b0"), True),
)

ANIMATIONS = (
    # Renamed from Circle w/ Vibration. Last byte changed B0 -> B8 to enable
    # the 6-short-tap vibration pattern (same as working Animation 0F-1).
    # The * suffix marks commands that trigger the band's vibration motor.
    ("Blue Circle *",
     bytes.fromhex("e200e91200030fa2a2a4a4a230d037f4d2460064fcb8"), True),
    ("Purple Flash *",
     bytes.fromhex("e100e90e00010fbda0a0bda059070048aeb5"), True),
    # Crop Dust Fart as a 2-step sequence: the E9 0E tap animation runs
    # for ~3.5s with its 0x8 rapid taps, then a 2-second long buzz (0x7)
    # in orange punctuates the end. Orange finale matches the "gas cloud"
    # theme without being jarring after the band's own color animation.
    ("Crop Dust Fart *",
     ((bytes.fromhex("e100e90e00110fbca7b9a7b959190248aeb8"), 3.5, (100, 80, 0)),
      (bytes.fromhex("e100e90500090e13b7"), 2.5, (200, 100, 0))),
     False),
    ("Blue & Orange *",
     bytes.fromhex("e100e90f00110f4f425807488dd2462a0717b8"), True),
    ("Blue Sparkle",
     bytes.fromhex("e100e91000134897d00ea0d146060f30d04e07b0"), True),
    # E9 13 is a firmware-baked animation that renders as a purple pulse on
    # real bands, despite its byte payload suggesting a multi-color mix.
    ("Purple Pulse",
     bytes.fromhex("e100e9130002d037f0d23d0505000efa8983510ee7a0b0"), True),
    ("Holiday Flash",
     bytes.fromhex("e200e91400420f555b58f44882d0651bd1462a02307b5db0"), False),
)

CATEGORIES = (
    ("Colors", COLORS),
    ("Show FX", SHOW_FX),
    ("Fades", CROSS_FADE),
    ("Animate", ANIMATIONS),
)
