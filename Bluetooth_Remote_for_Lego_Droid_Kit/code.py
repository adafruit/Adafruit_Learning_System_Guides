import time
import board
import busio
from digitalio import DigitalInOut, Direction
from adafruit_bluefruitspi import BluefruitSPI

# Setup SPI bus and 3 control pins for Nordic nRF51822 based Raytec MDBT40
spi_bus = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs  = DigitalInOut(board.D8)
irq = DigitalInOut(board.D7)
rst = DigitalInOut(board.D4)
bluefruit = BluefruitSPI(spi_bus, cs, irq, rst, debug=False)

boardled = DigitalInOut(board.D6)
#boardled = DigitalInOut(board.D13) # small onboard red LED
boardled.direction = Direction.OUTPUT

def vllchksum(n):
    return 7-((n+(n>>2)+(n>>4))&7)

# Lego Micro Scout commands
MS_FWD  = 0
MS_REV  = 1
MS_STOP = 2
MS_BEEP = 4

PAUSE = 0.15

ADVERT_NAME = b'BlueMicroScout'

# Note: incompatibile with ZX Spectrum cursors
BUTTON_1     = 1
BUTTON_2     = 2
BUTTON_3     = 3
BUTTON_4     = 4
BUTTON_UP    = 5
BUTTON_DOWN  = 6
BUTTON_LEFT  = 7
BUTTON_RIGHT = 8

# From https://github.com/JorgePe/mindstorms-vll/blob/master/vll-atat.py
# https://github.com/JorgePe/mindstorms-vll
def vll1():
    boardled.value =  True
    time.sleep(0.02)
    boardled.value = False
    time.sleep(0.04)

def vll0():
    boardled.value = True
    time.sleep(0.04)
    boardled.value = False
    time.sleep(0.02)

def vllinit():
    boardled.value = True
    time.sleep(0.4)

def vllstart():
    boardled.value = False
    time.sleep(0.02)

def vllstop():
    boardled.value = True
    time.sleep(0.02)
    boardled.value = False
    time.sleep(0.06)
    boardled.value = True
    time.sleep(0.12)

def send(command):
    vllstart()
    v = (vllchksum(command) << 7 ) + command
    i = 0x200
    while i>0 :
        if v & i:
            vll1()
        else:
            vll0()
        i = i >> 1
    vllstop()

def pause():
    boardled.value = True
    time.sleep(PAUSE)

boardled.value = False

vllinit()

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

# Borrowed from MUNNY code

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
                # Look for a 'B' for Button packet
                if resp[0] != 'B':
                    continue
                button_num = resp[1]
                button_down = resp[2]
                # For now only look for the down events
                if button_down:
                    if button_num == BUTTON_UP:
                        send(MS_FWD)
                    elif button_num == BUTTON_DOWN:
                        send(MS_REV)
                    elif button_num == BUTTON_1:
                        send(MS_BEEP)
                    else:
                        # some other key pressed
                        pass
            else:  # Not connected
                pass

    except RuntimeError as e:
        print(e)  # Print what happened
        continue  # retry!
