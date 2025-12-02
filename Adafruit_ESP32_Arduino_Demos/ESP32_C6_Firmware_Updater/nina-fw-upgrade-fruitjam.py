# SPDX-FileCopyrightText: 2025 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import board
import busio
import neopixel
import digitalio
import adafruit_miniesptool

print("nina-fw Updater for Fruit Jam")
print("Press FruitJam Button 3 to start flashing...")

# Configure Fruit Jam's ESP32-C6 pinout
tx = board.ESP_TX
rx = board.ESP_RX
reset = digitalio.DigitalInOut(board.ESP_RESET)
reset.direction = digitalio.Direction.OUTPUT
gpio0 = digitalio.DigitalInOut(board.I2S_IRQ)
gpio0.direction = digitalio.Direction.OUTPUT

# Setup Fruit Jam button #3
button = digitalio.DigitalInOut(board.BUTTON3)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Setup NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 5)
pixels.brightness = 0.5

# Wait for button press to begin flashing
pixels.fill((0, 0, 255))
while button.value:
    time.sleep(0.1)

print("Button pressed! Starting flashing process...")
pixels.fill((255, 0, 0))

# Initialize UART and esptool
uart = busio.UART(tx, rx, baudrate=115200, timeout=1)
esptool = adafruit_miniesptool.miniesptool(uart, gpio0, reset, flashsize=4 * 1024 * 1024)

# Attempt to sync with the ESP32-C6
esptool.sync()
chip_name = esptool.chip_name
if (chip_name is None):
    pixels.fill((255, 0, 0))
    time.sleep(3)
    raise RuntimeError("Unable to detect chip type!")
print("Chip Name:", chip_name)
print("Chip MAC Addr: ", [hex(i) for i in esptool.mac_addr])
# Increase baudrate to speed up flashing
esptool.baudrate = 912600

# Attempt to flash nina.bin to the ESP32-C6
print("Flashing...")
pixels.fill((255, 255, 0))
try:
    esptool.flash_file("nina.bin", 0x0)
except (OSError, RuntimeError) as e:
    pixels.fill((255, 0, 0))
    time.sleep(2)
    raise RuntimeError("Flashing failed: " + str(e))

print("Done flashing, resetting..")
esptool.reset()

# Blink green to show we're done flashing
while True:
    pixels.fill((0, 255, 0))
    time.sleep(0.5)
    pixels.fill((0, 0, 0))
    time.sleep(0.5)