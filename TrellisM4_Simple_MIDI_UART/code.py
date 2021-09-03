# Simple example of sending MIDI via UART to classic DIN-5 (not USB) synth

import adafruit_trellism4

import board
import busio
midiuart = busio.UART(board.SDA, board.SCL, baudrate=31250)
print("MIDI UART EXAMPLE")

trellis = adafruit_trellism4.TrellisM4Express()

def wheel(pos):
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))


for x in range(trellis.pixels.width):
    for y in range(trellis.pixels.height):
        pixel_index = (((y * 8) + x) * 256 // 2)
        trellis.pixels[x, y] = wheel(pixel_index & 255)

current_press = set()

while True:
    pressed = set(trellis.pressed_keys)

    for press in pressed - current_press:
        x, y = press
        print("Pressed:", press)
        noteval = 36 + x + (y * 8)
        midiuart.write(bytes([0x90, noteval, 100]))

    for release in current_press - pressed:
        x, y = release
        print("Released:", release)
        noteval = 36 + x + (y * 8)
        midiuart.write(bytes([0x90, noteval, 0]))  # note off

    current_press = pressed
