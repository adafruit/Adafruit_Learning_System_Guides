# SPDX-FileCopyrightText: 2026 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import usb_midi
import adafruit_midi
from digitalio import DigitalInOut, Direction
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
import neopixel

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# NeoPixel LED Setup
NUMPIXELS = 72
BRIGHTNESS = 1
PIN = board.EXTERNAL_NEOPIXELS
ORDER = neopixel.BGR
pixels = neopixel.NeoPixel(PIN, NUMPIXELS, brightness=BRIGHTNESS,
                           auto_write=False, pixel_order=ORDER)

# Matrix layout
MATRIX_ROWS = 6
MATRIX_COLS = 12  # One full chromatic octave per row

# MIDI setup - listen on channels 1 and 2 (0-indexed: 0 and 1)
print(usb_midi.ports)
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=(0, 1), midi_out=usb_midi.ports[1], out_channel=0
)

# MIDI note number that maps to Pixel 0 (top-left of matrix).
# 24 = C1, 36 = C2, 48 = C3
NOTE_OFFSET = 24

# Chromatic note names used for print statements
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Base color palette - 24 colors spanning two octaves of the chromatic scale.
# The first 12 colors cover one octave, the next 12 cover the second octave
# with a distinct shifted palette. Colors then tile across all 6 rows.
BASE_COLORS = [
    # Octave A - Warm to Cool spectrum
    (255, 0,   0),    # C  - Red
    (255, 45,  0),    # C# - Red-Orange
    (255, 90,  0),    # D  - Orange
    (255, 145, 0),    # D# - Amber
    (255, 200, 0),    # E  - Yellow-Orange
    (255, 255, 0),    # F  - Yellow
    (128, 255, 0),    # F# - Yellow-Green
    (0,   255, 0),    # G  - Green
    (0,   255, 128),  # G# - Spring Green
    (0,   255, 255),  # A  - Cyan
    (0,   128, 255),  # A# - Sky Blue
    (0,   0,   255),  # B  - Blue

    # Octave B - Rich and saturated shifted palette
    (64,  0,   255),  # C  - Indigo
    (128, 0,   255),  # C# - Violet
    (200, 0,   255),  # D  - Purple
    (255, 0,   200),  # D# - Magenta
    (255, 0,   128),  # E  - Hot Pink
    (255, 0,   64),   # F  - Deep Rose
    (255, 64,  64),   # F# - Salmon
    (255, 128, 128),  # G  - Light Coral
    (255, 200, 128),  # G# - Peach
    (255, 255, 128),  # A  - Pale Yellow
    (128, 255, 128),  # A# - Mint
    (128, 255, 255),  # B  - Ice Blue
]

# Expand BASE_COLORS to a full 72-entry list by repeating the 24-color pattern.
PIXEL_COLORS = [BASE_COLORS[i % len(BASE_COLORS)] for i in range(NUMPIXELS)]

FADE_DURATION = 0.1   # Total fade duration in seconds
FADE_STEPS = 5       # Number of steps in the fade

# Non-blocking fade state per pixel:
# pixel_index -> {"color": (r,g,b), "step": int, "last_time": float}
fading_pixels = {}

def note_to_matrix(note):
    """
    Map a MIDI note to a (row, col) position in the matrix.
    Each row is one octave (12 notes). C always starts at column 0.
    NOTE_OFFSET determines which note maps to (row=0, col=0).
    """
    offset_note = note - NOTE_OFFSET
    r = (offset_note // MATRIX_COLS) % MATRIX_ROWS
    c = offset_note % MATRIX_COLS
    return r, c

def matrix_to_pixel(r, c):
    """
    Convert a (row, col) matrix position to a physical pixel index,
    accounting for zigzag wiring.
    Even rows (0, 2, 4) run left to right.
    Odd rows  (1, 3, 5) run right to left.
    """
    if r % 2 == 0:
        return r * MATRIX_COLS + c                       # Left to right
    else:
        return r * MATRIX_COLS + (MATRIX_COLS - 1 - c)  # Right to left

def note_to_pixel(note):
    """Map a MIDI note directly to a physical pixel index via the matrix."""
    r, c = note_to_matrix(note)
    return matrix_to_pixel(r, c)

def note_to_name(note):
    """Return a human-readable note name and octave, e.g. 'C2' for note 36."""
    name = NOTE_NAMES[note % 12]
    octave = (note // 12) - 1
    return f"{name}{octave}"

def color_for_note(note):
    """
    Look up the color for a note based on its position across two octaves.
    The 24-color palette tiles every two octaves across the matrix rows.
    """
    offset_note = note - NOTE_OFFSET
    return BASE_COLORS[offset_note % len(BASE_COLORS)]

def color_wipe(c, delay=0.01):
    """Wipe a color across the strip one LED at a time."""
    for i in range(NUMPIXELS):
        pixels[i] = c
        pixels.show()
        time.sleep(delay)

def boot_sequence():
    """Animated boot sequence using color wipes."""
    color_wipe((255, 0, 0),     0.01)  # Red wipe
    color_wipe((0, 255, 0),     0.01)  # Green wipe
    color_wipe((0, 0, 255),     0.01)  # Blue wipe
    color_wipe((0, 0, 0),       0.01)  # Wipe off

def update_fades():
    """Call this every loop iteration to advance any active fades."""
    now = time.monotonic()
    completed = []
    for pix_index, state in fading_pixels.items():
        step_delay = FADE_DURATION / FADE_STEPS
        if now - state["last_time"] >= step_delay:
            state["step"] += 1
            state["last_time"] = now
            if state["step"] >= FADE_STEPS:
                pixels[pix_index] = (0, 0, 0)
                pixels.show()
                completed.append(pix_index)
            else:
                r, g, b = state["color"]
                factor = (FADE_STEPS - state["step"]) / FADE_STEPS
                pixels[pix_index] = (int(r * factor), int(g * factor), int(b * factor))
                pixels.show()
    for pix_index in completed:
        del fading_pixels[pix_index]

# Run boot sequence on startup
boot_sequence()

while True:
    msg = midi.receive()

    if isinstance(msg, NoteOn) and msg.velocity > 0:
        pixel_index = note_to_pixel(msg.note)
        color = color_for_note(msg.note)
        note_name = note_to_name(msg.note)
        row, col = note_to_matrix(msg.note)
        # Immediately cancel any active fade on this pixel
        if pixel_index in fading_pixels:
            del fading_pixels[pixel_index]
        pixels[pixel_index] = color
        pixels.show()
        print(f"Note ON:  {note_name} ({msg.note}) Pixel {pixel_index}, Color {color}")

    elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
        pixel_index = note_to_pixel(msg.note)
        color = color_for_note(msg.note)
        note_name = note_to_name(msg.note)
        row, col = note_to_matrix(msg.note)
        fading_pixels[pixel_index] = {
            "color": color,
            "step": 0,
            "last_time": time.monotonic()
        }
        print(f"Note OFF: {note_name} ({msg.note}) Pixel {pixel_index} fading")

    # Advance all active fades each loop iteration
    update_fades()
