# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
from os import getenv
from displayio import Group
from terminalio import FONT
import supervisor
import audiocore
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_color_terminal import ColorTerminal
from adafruit_fruitjam.peripherals import Peripherals

from curses_irc_client import run_irc_client

# Configuration - modify these values as needed
IRC_CONFIG = {
    "server": "irc.libera.chat",  # Example: irc.libera.chat, irc.freenode.net
    # "port": 6667,  # 6667 - clear text
    "port": 6697,  # 6697 - TLS encrypted
    "username": "",
    "channel": "#adafruit-fruit-jam",
}

if IRC_CONFIG["username"] == "":
    raise ValueError("username must be set in IRC_CONFIG")

main_group = Group()
display = supervisor.runtime.display

font_bb = FONT.get_bounding_box()
screen_size = (display.width // font_bb[0], display.height // font_bb[1])

terminal = ColorTerminal(FONT, screen_size[0], screen_size[1])
main_group.append(terminal.tilegrid)
display.root_group = main_group

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(ssid, password)
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue

print("IRC Configuration:")
print(f"Server: {IRC_CONFIG['server']}:{IRC_CONFIG['port']}")
print(f"Nickname: {IRC_CONFIG['username']}")
print(f"Channel: {IRC_CONFIG['channel']}")
print("-" * 40)

fruit_jam_peripherals = Peripherals()
beep_wave = audiocore.WaveFile("beep.wav")
run_irc_client(
    esp,
    IRC_CONFIG,
    terminal,
    terminal.tilegrid,
    audio_interface=fruit_jam_peripherals.audio,
    beep_wave=beep_wave,
)
