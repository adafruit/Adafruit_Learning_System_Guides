""" FancyLED Palette and Color Picker Control with BlueFruit App
    Code by Phil Burgess, Dan Halbert & Erin St Blaine for Adafruit Industries
"""
import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_ble.uart import UARTServer
# for >= CPy 5.0.0
# from adafruit_ble.uart_server import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket

NUM_LEDS = 60                   # change to reflect your LED strip
NEOPIXEL_PIN = board.D13        # change to reflect your wiring

# Palettes can have any number of elements in various formats
# check https://learn.adafruit.com/fancyled-library-for-circuitpython/colors
# for more info

# Declare a 6-element RGB rainbow palette
PALETTE_RAINBOW = [fancy.CRGB(1.0, 0.0, 0.0),  # Red
                   fancy.CRGB(0.5, 0.5, 0.0),  # Yellow
                   fancy.CRGB(0.0, 1.0, 0.0),  # Green
                   fancy.CRGB(0.0, 0.5, 0.5),  # Cyan
                   fancy.CRGB(0.0, 0.0, 1.0),  # Blue
                   fancy.CRGB(0.5, 0.0, 0.5)]  # Magenta

# Declare a Purple Gradient palette
PALETTE_GRADIENT = [fancy.CRGB(160, 0, 141),  # Purples
                    fancy.CRGB(77, 0, 160),
                    fancy.CRGB(124, 0, 255),
                    fancy.CRGB(0, 68, 214)]

# Declare a FIRE palette
PALETTE_FIRE = [fancy.CRGB(0, 0, 0),        # Black
                fancy.CHSV(1.0),            # Red
                fancy.CRGB(1.0, 1.0, 0.0),  # Yellow
                0xFFFFFF]                   # White

# Declare a Water Colors palette
PALETTE_WATER = [fancy.CRGB(0, 214, 214),  # blues and cyans
                 fancy.CRGB(0, 92, 160),
                 fancy.CRGB(0, 123, 255),
                 fancy.CRGB(0, 68, 214)]

# Declare a NeoPixel object on NEOPIXEL_PIN with NUM_LEDS pixels,
# no auto-write.
# Set brightness to max because we'll be using FancyLED's brightness control.
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_LEDS, brightness=1.0,
                           auto_write=False)

offset = 0  # Positional offset into color palette to get it to 'spin'
offset_increment = 1
OFFSET_MAX = 1000000

uart_server = UARTServer()

def set_palette(palette):
    for i in range(NUM_LEDS):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, (offset + i) / NUM_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()
    pixels.show()

# set initial palette to run on startup
palette_choice = PALETTE_RAINBOW

# True if cycling a palette
cycling = True

while True:
    uart_server.start_advertising()
    while not uart_server.connected:
        if cycling:
            set_palette(palette_choice)
            offset = (offset + offset_increment) % OFFSET_MAX

    # Now we're connected

    while uart_server.connected:
        if uart_server.in_waiting:
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, ColorPacket):
                cycling = False
                # Set all the pixels to one color and stay there.
                pixels.fill(packet.color)
                pixels.show()
            elif isinstance(packet, ButtonPacket):
                cycling = True
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        palette_choice = PALETTE_RAINBOW
                    elif packet.button == ButtonPacket.BUTTON_2:
                        palette_choice = PALETTE_GRADIENT
                    elif packet.button == ButtonPacket.BUTTON_3:
                        palette_choice = PALETTE_FIRE
                    elif packet.button == ButtonPacket.BUTTON_4:
                        palette_choice = PALETTE_WATER
                # change the speed of the animation by incrementing offset
                    elif packet.button == ButtonPacket.UP:
                        offset_increment += 1
                    elif packet.button == ButtonPacket.DOWN:
                        offset_increment -= 1

        if cycling:
            offset = (offset + offset_increment) % OFFSET_MAX
            set_palette(palette_choice)
