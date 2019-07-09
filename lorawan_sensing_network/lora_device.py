"""
lora_device.py

CircuitPython LoRa Device w/BME280
"""
import time
import busio
import digitalio
import board

# Import LoRa Library
import adafruit_rfm9x

# Import BME280 Sensor Library
import adafruit_bme280

# Device ID
FEATHER_ID = 0x01

# Delay between sending radio data, in minutes.
SENSOR_SEND_DELAY = 1

# Create library object using our Bus I2C port
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# Define radio frequency, MUST match gateway frequency.
RADIO_FREQ_MHZ = 905.5

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:
# pylint: disable=c-extension-no-member
CS = digitalio.DigitalInOut(board.RFM9X_CS)
# pylint: disable=c-extension-no-member
RESET = digitalio.DigitalInOut(board.RFM9X_RST)

# Define the onboard LED
LED = digitalio.DigitalInOut(board.D13)
LED.direction = digitalio.Direction.OUTPUT

# Initialize SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

# Set transmit power to max
rfm9x.tx_power = 23

# sensor data
bme280_data = bytearray(8)

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
    bme280_data[5] = (pres_val >> 16) & 0xff
    bme280_data[6] = (pres_val >> 8) & 0xff
    bme280_data[7] = pres_val & 0xff

    # Convert bytearray to bytes
    bme280_data_bytes = bytes(bme280_data)
    # Send the packet data
    print('Sending data...')
    LED.value = True
    rfm9x.send(bme280_data)
    print('Sent data!')
    LED.value = False

    # Wait to send the packet again
    time.sleep(SENSOR_SEND_DELAY * 60)
  