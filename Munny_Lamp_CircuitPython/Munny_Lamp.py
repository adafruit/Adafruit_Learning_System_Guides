# RGB Color Picker demo - wire up RGB LEDs and set their color
# using Adafruit Bluefruit Connect App on your phone
# runs on Feather M0 Bluefruit LE running the Feather M0 Adalogger build
# of CircuitPython with Prop-Maker Wing and 3W RGB LED

import time
import random
import board
import busio
import pulseio
from digitalio import DigitalInOut, Direction
from adafruit_bluefruitspi import BluefruitSPI
import adafruit_lis3dh

ADVERT_NAME = b'BlinkaNeoLamp'

# RGB LED on D11, 12, 13, we're using a Prop Maker wing
red_led = pulseio.PWMOut(board.D11, frequency=50000, duty_cycle=0)
green_led = pulseio.PWMOut(board.D12, frequency=50000, duty_cycle=0)
blue_led = pulseio.PWMOut(board.D13, frequency=50000, duty_cycle=0)
# Prop maker wing has a power pin for the LED!
power_pin = DigitalInOut(board.D10)
power_pin.direction = Direction.OUTPUT
power_pin.value = True

spi_bus = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.D8)
irq = DigitalInOut(board.D7)
rst = DigitalInOut(board.D4)
bluefruit = BluefruitSPI(spi_bus, cs, irq, rst, debug=False)

i2c = busio.I2C(board.SCL, board.SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

def init_bluefruit():
    # Initialize the device and perform a factory reset
    print("Initializing the Bluefruit LE SPI Friend module")
    bluefruit.init()
    bluefruit.command_check_OK(b'AT+FACTORYRESET', delay=1)
    # Print the response to 'ATI' (info request) as a string
    print(str(bluefruit.command_check_OK(b'ATI'), 'utf-8'))
    # Change advertised name
    bluefruit.command_check_OK(b'AT+GAPDEVNAME='+ADVERT_NAME)

def wait_for_connection():
    print("Waiting for a connection to Bluefruit LE Connect ...")
    # Wait for a connection ...
    dotcount = 0
    while not bluefruit.connected:
        print(".", end="")
        dotcount = (dotcount + 1) % 80
        if dotcount == 79:
            print("")
        time.sleep(0.5)

# This code will check the connection but only query the module if it has been
# at least 'n_sec' seconds. Otherwise it 'caches' the response, to keep from
# hogging the Bluefruit connection with constant queries
connection_timestamp = None
is_connected = None
def check_connection(n_sec):
    # pylint: disable=global-statement
    global connection_timestamp, is_connected
    if (not connection_timestamp) or (time.monotonic() - connection_timestamp > n_sec):
        connection_timestamp = time.monotonic()
        is_connected = bluefruit.connected
    return is_connected

# Unlike most circuitpython code, this runs in two loops
# one outer loop manages reconnecting bluetooth if we lose connection
# then one inner loop for doing what we want when connected!
while True:
    # Initialize the module
    init_bluefruit()
    try:        # Wireless connections can have corrupt data or other runtime failures
                # This try block will reset the module if that happens
        while True:
            # Once connected, check for incoming BLE UART data
            if check_connection(3):  # Check our connection status every 3 seconds
                # OK we're still connected, see if we have any data waiting
                resp = bluefruit.read_packet()
                if not resp:
                    continue  # nothin'
                print("Read packet", resp)
                # Look for a 'C'olor packet
                if resp[0] != 'C':
                    continue
                # Set the LEDs to the three bytes in the packet
                red_led.duty_cycle = int(resp[1]/255 * 65535)
                green_led.duty_cycle = int(resp[2]/255 * 65535)
                blue_led.duty_cycle = int(resp[3]/255 * 65535)
            else:  # Not connected
                # print(lis3dh.acceleration)
                if lis3dh.acceleration.y < -5:
                    print("Tilted")
                    red_led.duty_cycle = random.randint(0, 65535)
                    green_led.duty_cycle = random.randint(0, 65535)
                    blue_led.duty_cycle = random.randint(0, 65535)
                    time.sleep(0.25)

    except RuntimeError as e:
        print(e)  # Print what happened
        continue  # retry!
