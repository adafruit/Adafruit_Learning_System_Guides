"""
Demo of using the RFM69HCW Radio with Raspberry Pi.

Author: Brent Rubell for Adafruit Industries
"""
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the RFM69 radio module.
import adafruit_rfm69
# Import the SSD1306 module.
import adafruit_ssd1306

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
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

# Configure Packet Radio
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, 915.0)

# Optionally set an encryption key (16 byte AES key). MUST match both
# on the transmitter and receiver (or be set to None to disable/the default).
rfm69.encryption_key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08'
# Data to send
packet_data = bytes('Hello Feather!\r\n',"utf-8")
prev_packet = None

while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('RasPi Radio', 35, 0, 1)

    # check for packet rx
    packet = rfm69.receive()
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
        display.text('RSSI: ', 0, 20, 1)
        display.text(str(rfm69.rssi), 35, 20, 1)
        time.sleep(2)

    if not btnA.value:
        # Send Packet
        rfm69.send(packet_data)
        display.fill(0)
        display.text('Sent Packet', 0, 25, 1)
        display.show()
        time.sleep(0.2)
    elif not btnB.value:
        # Display the previous packet text and rssi
        display.fill(0)
        if prev_packet is not None:
            packet_text = str(prev_packet, 'ascii')
            display.text('RX: ', 0, 0, 1)
            display.text(packet_text, 25, 0, 1)
            display.text('RSSI: ', 0, 20, 1)
            display.text(str(rfm69.rssi), 35, 20, 1)
        else:
            display.text('No Pkt RCVd', 0, 16, 1)
        display.show()
        time.sleep(2)

    display.show()
    time.sleep(0.1)
