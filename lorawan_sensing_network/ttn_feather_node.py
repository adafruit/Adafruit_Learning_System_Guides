"""
bme280_lorawan.py

CircuitPython TinyLoRa Node
for a BME280 sensor

Learn Guide: https://learn.adafruit.com/multi-device-lora-temperature-network

by Brent Rubell for Adafruit Industries, 2019
"""
import time
import busio
import digitalio
import board

# Import BME280 Sensor Library
import adafruit_bme280

# Import TinyLoRa Library
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa

# Device ID
FEATHER_ID = 0x01

# Delay between sending radio data, in minutes.
SENSOR_SEND_DELAY = 0.5

# Create library object using our Bus I2C port
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# Board LED
led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

# Feather M0 RFM9x Pinouts
# pylint: disable=c-extension-no-member
irq = digitalio.DigitalInOut(board.RFM9X_D0)
# pylint: disable=c-extension-no-member
cs = digitalio.DigitalInOut(board.RFM9X_CS)

# Create library object using our bus SPI port for radio
spi = busio.SPI(board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# TTN Device Address, 4 Bytes, MSB
devaddr = bytearray([0x00, 0x00, 0x00, 0x00])

# TTN Network Key, 16 Bytes, MSB
nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

# TTN Application Key, 16 Bytess, MSB
app = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

ttn_config = TTN(devaddr, nwkey, app, country='US')

lora = TinyLoRa(spi, cs, irq, ttn_config)

# Data Packet to send to TTN
bme280_data = bytearray(7)

while True:
    # Get sensor readings
    temp_val = int(bme280.temperature * 100)
    print("\nTemperature: %0.1f C" % bme280.temperature)
    humid_val = int(bme280.humidity * 100)
    print("Humidity: %0.1f %%" % bme280.humidity)
    pres_val = int(bme280.pressure * 100)
    print("Pressure: %0.1f hPa" % bme280.pressure)

    # Build packet with float data and headers

    # packet header with feather node ID
    bme280_data[0] = FEATHER_ID
    # Temperature data
    bme280_data[1] = (temp_val >> 8) & 0xff
    bme280_data[2] = temp_val & 0xff

    # Humid data
    bme280_data[3] = (humid_val >> 8) & 0xff
    bme280_data[4] = humid_val & 0xff

    # Pressure data
    bme280_data[5] = (pres_val >> 8) & 0xff
    bme280_data[6] = pres_val & 0xff


    # Send data packet
    print('Sending packet...')
    led.value = True
    lora.send_data(bme280_data, len(bme280_data), lora.frame_counter)
    print('Packet Sent!')
    led.value = False
    lora.frame_counter += 1
    time.sleep(SENSOR_SEND_DELAY * 60)
    