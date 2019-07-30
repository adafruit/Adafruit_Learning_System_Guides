import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_bme280
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa

# Unique feather identifier
FEATHER_ID = 1

i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# TinyLoRa/RFM9x Setup
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
# pylint: disable=c-extension-no-member
cs = DigitalInOut(board.RFM9X_CS)
irq = DigitalInOut(board.RFM9X_D0)
rst = DigitalInOut(board.RFM9X_RST)

# TTN Device Address, 4 Bytes, MSB
devaddr = bytearray([0x00, 0x00, 0x00, 0x00])

# TTN Network Key, 16 Bytes, MSB
nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

# TTN Application Key, 16 Bytess, MSB
app = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

ttn_config = TTN(devaddr, nwkey, app, country='US')

lora = TinyLoRa(spi, cs, irq, rst, ttn_config, channel = 6)

# bme data packet
bme_d = bytearray(7)

while True:
    # Grab sensor data
    temp_val = int(bme280.temperature * 100)
    humid_val = int(bme280.humidity * 100)

    bme_d[0] = FEATHER_ID
    # Temperature data
    bme_d[1] = (temp_val >> 8) & 0xff
    bme_d[2] = temp_val & 0xff
    # Humidity data
    bme_d[3] = (humid_val >> 8) & 0xff
    bme_d[4] = humid_val & 0xff

    print('Sending packet...')
    lora.send_data(bme_d, len(bme_d), lora.frame_counter)
    print('Packet sent!')
    lora.frame_counter += 1
    time.sleep(1 * 60)
