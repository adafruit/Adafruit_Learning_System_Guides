# pylint: disable=unused-import
import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
from adafruit_fona.fona_3g import FONA3G
import adafruit_bme280

print("FONA SMS Sensor")

# Create a serial connection for the FONA connection
uart = busio.UART(board.TX, board.RX)
rst = digitalio.DigitalInOut(board.D4)

# Use this for FONA800 and FONA808
fona = FONA(uart, rst)

# Use this for FONA3G
# fona = FONA3G(uart, rst)

# Initialize BME280 Sensor
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# Initialize Network
while fona.network_status != 1:
    print("Connecting to network...")
    time.sleep(1)
print("Connected to network!")
print("RSSI: %ddB" % fona.rssi)

# Enable FONA SMS notification
fona.enable_sms_notification = True

print("Listening for messages...")
while True:
    sender, message = fona.receive_sms()
    if message:
        print("New Message!")
        print("FROM: ", sender)
        print("MSG: ", message)

        # Read BME280 sensor values
        temp = bme280.temperature
        humid = bme280.humidity
        pres = bme280.pressure

        # Sanitize message
        message = message.lower()
        message = message.strip()

        if message in ["temp", "temperature", "t"]:
            response = "Temperature: %0.1f C" % temp
        elif message in ["humid", "humidity", "h"]:
            response = "Humidity: %0.1f %%" % humid
        elif message in ["pres", "pressure", "p"]:
            response = "Pressure: %0.1f hPa" % pres
        elif message in ["status", "s"]:
            response = "Temperature: {0:.2f}C\nHumidity: {1:.1f}%Pressure: {2:.1f}hPa".format(
                temp, humid, pres
            )
        elif message in ["help"]:
            response = "I'm a SMS Sensor - txt me with a command:\
                        TEMP - Read temperature\
                        HUMID - Read humidity\
                        PRES - Read pressure\
                        STATUS - Read all sensors.\
                        HELP - List commands"
        else:
            response = "Incorrect message format received. \
                        Text HELP to this number for a list of commands."

        # Send a response back to the sender
        print("Sending response...")
        if not fona.send_sms(int(sender), response):
            print("SMS Send Failed")
        print("SMS Sent!")
