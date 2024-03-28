# SPDX-FileCopyrightText: 2024 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array

import ulab
import rp2pio
import board
import adafruit_pioasm
import picodvi
import displayio

# The connections from the Xerox 820
vdata = board.D9  # Followed by hsync on D10 & vsync on D11
# The nominal frequency of the Xerox 820 video circuitry. Can modify by steps
# of approximately ±42000 to improve display stability
pixel_frequency = 10_694_250
# The PIO peripheral is run at a multiple of the pixel frequency. This must be less
# than the CPU speed, normally 120MHz.
clocks_per_pixel = 10
# The "fine pixel offset", shifts the sample time by this many sub-pixels
fine_pixel = 0
# A pin that shows when the Pico samples the pixel value. With an oscilloscope, this can
# be used to help fine tune the pixel_frequency & fine_pixel numbers. Ideally, the rising
# edge of pixel_sync_out is exactly in the middle of time a pixel is high/low.
pixel_sync_out = board.D5

# Details of the Xerox display timing. You may need to modify `blanking_lines` and
# `blanking_pixels` to adjust the vertical and horizontal position of the screen content.
# Normally you wouldn't change `active_lines` or `active_pixels`.
active_lines = 240
blanking_lines = 18
active_pixels = 640
blanking_pixels = 58
total_lines = active_lines + blanking_lines

# Pins for the DVI connector
dvi_pins = dict(
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
)

# Set up the display. Try 640x240 first (this mode is likely to be added in CircuitPython
# 9.1.x) then 640x480, which works in CircuitPython 9.0.x.
try:
    displayio.release_displays()
    dvi = picodvi.Framebuffer(640, 240, **dvi_pins, color_depth=1)
except ValueError:
    print(
        "Note: This version of CircuitPython does not support 640x240\n."
        "Display will be compressed vertically."
    )
    displayio.release_displays()
    dvi = picodvi.Framebuffer(640, 480, **dvi_pins, color_depth=1)

# Clear the display
ulab.numpy.frombuffer(dvi, dtype=ulab.numpy.uint8)[:] = 0

# Create the "control stream". The details are discussed in the Learn article
def control_gen():
    yield total_lines - 2
    for _ in range(blanking_lines):
        yield from (1, 0)  # 0 active pixels is special-cased
    for _ in range(active_lines):
        yield from (blanking_pixels - 1, active_pixels - 1)

control = array.array("L", control_gen())

# These little programs are run on the RP2040's PIO co-processor, and handle the pixel
# data and sync pulses.
jmp_0 = adafruit_pioasm.Program("jmp 0")

program = adafruit_pioasm.Program(
    f"""
.side_set 1

    .wrap_target
    out y, 32           ; get total line count
    wait 0, pin 2
    wait 1, pin 2 ; wait for vsync

wait_line_inactive:
    out x, 32     ; get total line count
    wait 0, pin 1
    wait 1, pin 1; wait for hsync

wait_line_active:
    nop [{clocks_per_pixel-2}]
    jmp x--, wait_line_active ; count off non-active pixels

    out x, 32 [{fine_pixel}]    ; get line active pixels & perform fine pixel adjust
    jmp !x, wait_line_inactive  ; no pixels this line, wait next hsync

capture_active_pixels:
    in pins, 1 side 1
    jmp x--, capture_active_pixels [{clocks_per_pixel-2}] ; more pixels
    jmp y--, wait_line_inactive ; more lines?
    .wrap
"""
)

# Set up PIO to transfer pixels from Xerox
pio = rp2pio.StateMachine(
    program.assembled,
    frequency=pixel_frequency * clocks_per_pixel,
    first_in_pin=vdata,
    in_pin_count=3,
    in_pin_pull_up=True,
    first_sideset_pin=pixel_sync_out,
    auto_pull=True,
    pull_threshold=32,
    auto_push=True,
    push_threshold=32,
    offset=0,
    **program.pio_kwargs,
)

# Set up the DVI framebuffer memory as a capture target
words_per_row = 640 // 32
first_row = (dvi.height - 240) // 2  # adjust text to center if in 640x480 mode
buf = memoryview(dvi).cast("L")[
    first_row * words_per_row : (first_row + active_lines) * words_per_row
]
assert len(buf) == 4800  # Check that the right amount will be transferred

b = array.array("L", [0])

# Repeatedly transfer pixels from Xerox into DVI framebuffer.
while True:
    pio.run(jmp_0.assembled)
    pio.clear_rxfifo()
    pio.write_readinto(instruction, buf)
