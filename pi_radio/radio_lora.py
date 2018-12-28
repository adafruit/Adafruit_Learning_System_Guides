"""
Example for using the RFM9x Radio with Raspberry Pi.

Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
Author: Brent Rubell for Adafruit Industries
"""
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import thte SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x
import adafruit_rfm9x

# Button A
btnA = DigitalInOut(board.D26)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D19)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

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
CS = DigitalInOut(board.D18)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
rfm9x.tx_power = 23
data_to_send = bytes("Hello LoRa!\r\n","utf-8")
prev_packet = None
while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('RasPi LoRa', 35, 0, 1)

    # check for packet rx
    packet = rfm9x.receive()
    print(packet)
    if packet is None:
        display.show()
        display.text('- Waiting for PKT -', 0, 20, 1)
    else:
        # Display the packet text and rssi
        display.fill(0)
        prev_packet = packet
        packet_text = str(prev_packet, 'ascii')
        display.text('RX: ', 0, 0, 1)
        display.text(packet_text, 25, 0, 1)
        time.sleep(1)

    if not btnA.value:
        # Send Packet
        rfm9x.send(data_to_send)
        display.fill(0)
        display.text('Sent Packet', 0, 25, 1)
        display.show()
        time.sleep(0.1)
    elif not btnB.value:
        # Display the previous packet text and rssi
        display.fill(0)
        if prev_packet is not None:
            packet_text = str(prev_packet, 'ascii')
            display.text('RX: ', 0, 0, 1)
            display.text(packet_text, 25, 0, 1)
        else:
            display.text('No Pkt RCVd', 0, 16, 1)
        display.show()
        time.sleep(2)


    display.show()
    time.sleep(.1)
