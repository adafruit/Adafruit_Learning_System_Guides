"""
Example for using the RFM9x Radio with Raspberry Pi and LoRaWAN

Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
Author: Brent Rubell for Adafruit Industries
"""
import threading
import time
import subprocess
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import thte SSD1306 module.
import adafruit_ssd1306
# Import Adafruit TinyLoRa
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa

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

# TinyLoRa Configuration
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.CE1)
irq = DigitalInOut(board.D22)
rst = DigitalInOut(board.D25)

# TTN Device Address, 4 Bytes, MSB
devaddr = bytearray([0x00, 0x00, 0x00, 0x00])
# TTN Network Key, 16 Bytes, MSB
nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
# TTN Application Key, 16 Bytess, MSB
app = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
# Initialize ThingsNetwork configuration
ttn_config = TTN(devaddr, nwkey, app, country='US')
# Initialize lora object
lora = TinyLoRa(spi, cs, irq, rst, ttn_config)
# 2b array to store sensor data
data_pkt = bytearray(2)
# time to delay periodic packet sends (in seconds)
data_pkt_delay = 5.0


def send_pi_data_periodic():
    threading.Timer(data_pkt_delay, send_pi_data_periodic).start()
    print("Sending periodic data...")
    send_pi_data(CPU)
    print('CPU:', CPU)

def send_pi_data(data):
    # Encode float as int
    data = int(data * 100)
    # Encode payload as bytes
    data_pkt[0] = (data >> 8) & 0xff
    data_pkt[1] = data & 0xff
    # Send data packet
    lora.send_data(data_pkt, len(data_pkt), lora.frame_counter)
    lora.frame_counter += 1
    display.fill(0)
    display.text('Sent Data to TTN!', 15, 15, 1)
    print('Data sent!')
    display.show()
    time.sleep(0.5)

while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('RasPi LoRaWAN', 35, 0, 1)

    # read the raspberry pi cpu load
    cmd = "top -bn1 | grep load | awk '{printf \"%.1f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell = True )
    CPU = float(CPU)

    if not btnA.value:
        # Send Packet
        send_pi_data(CPU)
    if not btnB.value:
        # Display CPU Load
        display.fill(0)
        display.text('CPU Load %', 45, 0, 1)
        display.text(str(CPU), 60, 15, 1)
        display.show()
        time.sleep(0.1)
    if not btnC.value:
        display.fill(0)
        display.text('* Periodic Mode *', 15, 0, 1)
        display.show()
        time.sleep(0.5)
        send_pi_data_periodic()


    display.show()
    time.sleep(.1)
