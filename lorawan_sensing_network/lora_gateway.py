"""
Adafruit IO LoRa Gateway

Learn Guide: https://learn.adafruit.com/multi-device-lora-temperature-network

by Brent Rubell for Adafruit Industries
"""
# Import Python System Libraries
import time

# Import Adafruit IO REST client.
from Adafruit_IO import Client

# Import Blinka Libraries
import busio
import board
from digitalio import DigitalInOut, Direction, Pull

# Import SSD1306 module.
import adafruit_ssd1306

# Import RFM9x module
import adafruit_rfm9x

# Define radio frequency, must match device.
RADIO_FREQ_MHZ = 905.5

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
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
prev_packet = None

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'USER'

# Set to your Adafruit IO key.
ADAFRUIT_IO_KEY = 'KEY'

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Set up Adafruit IO feeds
temperature_feed_1 = aio.feeds('feather-1-temp')
humidity_feed_1 = aio.feeds('feather-1-humid')
pressure_feed_1 = aio.feeds('feather-1-pressure')

temperature_feed_2 = aio.feeds('feather-2-temp')
humidity_feed_2 = aio.feeds('feather-2-humid')
pressure_feed_2 = aio.feeds('feather-2-pressure')

def pkt_int_to_float(pkt_val_1, pkt_val_2, pkt_val_3=None):
    """Convert packet data to float.
    """
    if pkt_val_3 is None:
        float_val = pkt_val_1 << 8 | pkt_val_2
    else:
        float_val = pkt_val_1 << 16 | pkt_val_2 << 8 | pkt_val_3
    return float_val/100

while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('Adafruit.IO LoRa GTWY', 0, 0, 1)

    # check for packet rx
    packet = rfm9x.receive()
    if packet is None or prev_packet:
        display.show()
        display.text('- Waiting for PKT -', 10, 20, 1)
    else:
        prev_packet = packet
        print('> New Packet!')
        # Decode packet
        temp_val = pkt_int_to_float(packet[1], packet[2])
        humid_val = pkt_int_to_float(packet[3], packet[4])
        pres_val = pkt_int_to_float(packet[5], packet[6], packet[7])

        # Display packet information
        print('Device ID: LoRa Feather #', packet[0])
        print("Temp: %0.2f C" % temp_val)
        print("Humid: %0.2f %% " % humid_val)
        print("Pressure: %0.2f hPa" % pres_val)

        # Send to Feather 1 feeds
        if packet[0] == 0x01:
            display.fill(0)
            display.text('Feather #1 Data RX''d!', 15, 0, 1)
            display.text('Sending to IO...', 0, 20, 1)
            display.show()
            aio.send(temperature_feed_1.key, temp_val)
            aio.send(humidity_feed_1.key, humid_val)
            aio.send(pressure_feed_1.key, pres_val)
            display.text('Sent!', 100, 20, 1)
            display.show()
        # Send to Feather 2 feeds
        if packet[0] == 0x02:
            display.fill(0)
            display.text('Feather #2 Data RX''d!', 15, 0, 1)
            display.text('Sending to IO...', 0, 20, 1)
            display.show()
            aio.send(temperature_feed_2.key, temp_val)
            aio.send(humidity_feed_2.key, humid_val)
            aio.send(pressure_feed_2.key, pres_val)
            display.text('Sent!', 100, 20, 1)
            display.show()
        time.sleep(1)

    display.show()
