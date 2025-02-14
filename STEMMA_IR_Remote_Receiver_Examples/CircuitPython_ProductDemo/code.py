# SPDX-FileCopyrightText: Copyright (c) 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Product demo for the IR Remote Receiver with an ESP32-S2 TFT

import board
import terminalio
import displayio
import digitalio
import pulseio
import adafruit_irremote
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
from adafruit_display_text import label
from adafruit_st7789 import ST7789

displayio.release_displays()

# TFT display setup
spi = board.SPI()
tft_cs = board.TFT_CS  # Adjust to your CS pin
tft_dc = board.TFT_DC  # Adjust to your DC pin
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(
    display_bus, rotation=270, width=240, height=135, rowstart=40, colstart=53
)

# Enable the display backlight
backlight = board.TFT_BACKLIGHT  # Adjust to your backlight pin
backlight = digitalio.DigitalInOut(backlight)
backlight.switch_to_output()
backlight.value = True

# Display initial text
text_area = label.Label(terminalio.FONT, text="Waiting\nfor IR...", color=0xFFFFFF)
text_area.anchor_point = (0.5, 0.5)
text_area.anchored_position = (240 / 2, 135 / 2)  # Assuming display size is 240x135
text_area.scale = 3  # Scale the text size up by 3 times

display.root_group = text_area

# IR receiver setup
# Adjust to your IR receiver pin
ir_receiver = pulseio.PulseIn(board.D5, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

def decode_ir_signals(p):
    codes = decoder.decode_bits(p)
    return codes

while True:
    pulses = decoder.read_pulses(ir_receiver)
    try:
        # Attempt to decode the received pulses
        received_code = decode_ir_signals(pulses)
        # Update display with the received code
        if received_code:
            hex_code = ''.join(["%02X" % x for x in received_code])
            text_area.text = f"Received:\n{hex_code}"
        print(f"Received: {hex_code}")
    except adafruit_irremote.IRNECRepeatException:  # Signal was repeated, ignore
        pass
    except adafruit_irremote.IRDecodeException:  # Failed to decode signal
        text_area.text = "Error decoding"
