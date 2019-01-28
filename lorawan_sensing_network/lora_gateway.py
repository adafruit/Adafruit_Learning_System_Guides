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
ADAFRUIT_IO_USERNAME = 'IO_USER'

# Set to your Adafruit IO key.
ADAFRUIT_IO_KEY = 'IO_PASS'

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Set up Adafruit IO feeds
temperature_feed = aio.feeds('feather-1-temp')
humidity_feed = aio.feeds('feather-1-humid')
altitude_feed = aio.feeds('feather-1-alt')
pressure_feed = aio.feeds('feather-1-pressure')

def pkt_int_to_float(pkt_val_1, pkt_val_2):
    float_val = pkt_val_1 << 8 | pkt_val_2
    return float_val/100

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
        print('> New Packet!')
        # Get temperature from packet
        temp_val = pkt_int_to_float(packet[1], packet[2])
        # Get humidity from packet
        humid_val = pkt_int_to_float(packet[3], packet[4])
        # Get altitude from packet
        alt_val = pkt_int_to_float(packet[5], packet[6])
        # Get pressure from packet
        pres_val = pkt_int_to_float(packet[7], packet[8])

        # Get Feather ID from packet header
        print('Device ID: LoRa Feather #', packet[0])
        if packet[0] == 0x01: # Send to Feather 1-specific feeds
          # Send Temperature 
          print("Sending to IO: %0.2f C" % temp_val)
          aio.send(temperature_feed.key, temp_val)
          # Send Humidity 
          print("Sending to IO: %0.2f %% " % humid_val)
          aio.send(humidity_feed.key, humid_val)
          # Send Altitude
          print("Sending to IO: %0.2f meters" % alt_val)
          aio.send(altitude_feed.key, alt_val)
          # Send Pressure
          print("Sending to IO: %0.2f hPa" % pres_val)
          aio.send(pressure_feed.key, pres_val)
        time.sleep(15)

    display.show()