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

vdata = board.D9  # Followed by hsync on D10 & vsync on D11
pixel_sync_out = board.D5
pixel_frequency = 10_694_250  # oddly specific
clocks_per_pixel = 10
fine_pixel = 0
active_lines = 240
blanking_lines = 18
active_pixels = 640
blanking_pixels = 58
total_lines = active_lines + blanking_lines

displayio.release_displays()

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

try:
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

def instruction_gen():
    yield total_lines - 2
    for _ in range(blanking_lines):
        yield from (1, 0)  # 0 active pixels is special-cased
    for _ in range(active_lines):
        yield from (blanking_pixels - 1, active_pixels - 1)


instruction = array.array("L", instruction_gen())
print(instruction)

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

pio = rp2pio.StateMachine(
    program.assembled,
    frequency=pixel_frequency * clocks_per_pixel,
    first_in_pin=vdata,
    in_pin_count=3,
    # in_pin_pull_up=True,
    first_sideset_pin=pixel_sync_out,
    auto_pull=True,
    pull_threshold=32,
    auto_push=True,
    push_threshold=32,
    offset=0,
    **program.pio_kwargs,
)

words_per_row = 640 // 32
first_row = (dvi.height - 240) // 2  # adjust text to center if in 640x480 mode
buf = memoryview(dvi).cast("L")[
    first_row * words_per_row : (first_row + active_lines) * words_per_row
]
assert len(buf) == 4800  # Check that the right amount will be transferred

b = array.array("L", [0])

while True:
    pio.run(jmp_0.assembled)
    pio.clear_rxfifo()
    pio.write_readinto(instruction, buf)
