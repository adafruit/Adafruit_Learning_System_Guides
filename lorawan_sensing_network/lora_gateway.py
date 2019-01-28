"""
Adafruit IO LoRa Gateway

Learn Guide: https://learn.adafruit.com/multi-device-lora-temperature-network
Author: Brent Rubell for Adafruit Industries
"""
# Import Python System Libraries
import time
# Import Blinka Libraries 
import busio
import board
from digitalio import DigitalInOut, Direction, Pull

# Import Adafruit IO REST client.
from Adafruit_IO import Client, Feed, Data, RequestError

# Import SSD1306 module.
import adafruit_ssd1306

# Import RFM9x module
import adafruit_rfm9x

TEMP_DATA = 0x01
TEMP_DATA = 0x01
TEMP_DATA = 0x01
TEMP_DATA = 0x01

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)
# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# Configure LoRa Radio
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 905.5)
prev_packet = None

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'USER'

# Set to your Adafruit IO key.
ADAFRUIT_IO_KEY = 'KEY'

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Set up Adafruit IO feeds
device_id_feed = aio.feeds('deviceid')
temperature_feed = aio.feeds('temperature')
humidity_feed = aio.feeds('humidity')
altitude_feed = aio.feeds('altitude')
pressure_feed = aio.feeds('pressure')

while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('Adafruit IO LoRa', 10, 0, 1)

    # check for packet rx
    packet = rfm9x.receive()
    if packet is None:
        display.show()
        display.text('- Waiting for PKT -', 15, 20, 1)
    else:
        # Get Feather ID from packet header
        print('> New Packet!')
        print('Device ID: LoRa Feather #', packet[0])
        aio.send(device_id_feed.key, packet[0])
        # Get temperature from packet
        temp_val = (packet[1] << 8) | packet[2];
        temp_val = temp_val / 100;
        # Send temperature to Adafruit IO
        print("Sending to IO: %0.2f C" % temp_val)
        aio.send(temperature_feed.key, temp_val)

        # Get humidity from packet
        humid_val = (packet[3] << 8) | packet[4];
        humid_val = humid_val / 100;
        # Send humidity to Adafruit IO
        print("Sending to IO: %0.2f %% " % humid_val)
        aio.send(humidity_feed.key, humid_val)

        # Get altitude from packet
        alt_val = (packet[5] << 8) | packet[6];
        alt_val = alt_val / 100;
        # Send altitude to Adafruit IO
        print("Sending to IO: %0.2f meters" % alt_val)
        aio.send(altitude_feed.key, alt_val)

        # Get pressure from packet
        pres_val = (packet[7] << 8) | packet[8];
        pres_val = pres_val / 100;
        # Send altitude to Adafruit IO
        print("Sending to IO: %0.2f hPa" % pres_val)
        aio.send(pressure_feed.key, pres_val)

        time.sleep(15)

    display.show()