import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_bme280
from adafruit_bme280 import Adafruit_BME280_I2C
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa

# BME280
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = Adafruit_BME280_I2C(i2c)

# TinyLoRa/RFM9x Setup
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.RFM9X_CS)
irq = DigitalInOut(board.RFM9X_D0)

# TTN Device Address, 4 Bytes, MSB
devaddr = bytearray([0x00, 0x00, 0x00, 0x00])

# TTN Network Key, 16 Bytes, MSB
nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

# TTN Application Key, 16 Bytess, MSB
app = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

ttn_config = TTN(devaddr, nwkey, app, country='US')

lora = TinyLoRa(spi, cs, irq, ttn_config, channel = 6)

# bme data packet
bme_d = bytearray(7)

while True:
    temp_val = int(bme280.temperature * 100)
    humid_val = int(bme280.humidity * 100)
    
    bme_d[0] = 0x01
    # Temperature data
    bme_d[1] = (temp_val >> 8) & 0xff
    bme_d[2] = temp_val & 0xff
    # Humid data
    bme_d[3] = (humid_val >> 8) & 0xff
    bme_d[4] = humid_val & 0xff
    
    print('Sending packet...')
    lora.send_data(bme_d, len(bme_d), lora.frame_counter)
    print('Packet sent!')
    lora.frame_counter += 1
    time.sleep(2)