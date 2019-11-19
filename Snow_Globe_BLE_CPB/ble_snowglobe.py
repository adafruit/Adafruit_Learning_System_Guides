import time
import random
import board
import busio
import neopixel
import adafruit_lis3dh

from adafruit_ble.uart_server import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

#===| User Config |==================================================
SNOWGLOBE_NAME = "SNOWGLOBE" # name that will show up on smart device
DEFAULT_ANIMATION = 0        # 0-3, index in ANIMATIONS list
DEFAULT_DURATION = 5         # total seconds to play animation
DEFAULT_SPEED = 0.1          # delay in seconds between updates
DEFAULT_COLOR = 0xFF0000     # hex color value
DEFAULT_SHAKE = 27           # lower number is more sensitive
# you can define more animation functions below
# here, specify the four to be used
ANIMATIONS = ('spin', 'pulse', 'strobe', 'sparkle')
#===| User Config |==================================================

# Configuration settings
snow_config = {
    'animation' : DEFAULT_ANIMATION,
    'duration' : DEFAULT_DURATION,
    'speed' : DEFAULT_SPEED,
    'color' : DEFAULT_COLOR,
    'shake' : DEFAULT_SHAKE,
}

# Setup NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Setup accelo
accelo_i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelo = adafruit_lis3dh.LIS3DH_I2C(accelo_i2c, address=0x19)

# Setup BLE
uart_server = UARTServer(name=SNOWGLOBE_NAME)

#--| ANIMATIONS |----------------------------------------------------
def spin(config):
    start_time = time.monotonic()
    last_update = start_time
    p = -1
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            pixels.fill(0)
            pixels[p % 10] = config['color']
            p -= 1
            last_update = time.monotonic()

def pulse(config):
    start_time = time.monotonic()
    last_update = start_time
    brightness = 0
    delta = 0.05
    pixels.brightness = 0
    pixels.fill(config['color'])
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            brightness += delta
            if brightness > 1:
                brightness = 1
                delta *= -1
            if brightness < 0:
                brightness = 0
                delta *= -1
            pixels.brightness = brightness
            last_update = time.monotonic()

def strobe(config):
    start_time = time.monotonic()
    last_update = start_time
    turn_on = True
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            if turn_on:
                pixels.fill(config['color'])
            else:
                pixels.fill(0)
            turn_on = not turn_on
            last_update = time.monotonic()

def sparkle(config):
    start_time = time.monotonic()
    last_update = start_time
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            pixels.fill(0)
            pixels[random.randint(0, 9)] = config['color']
            last_update = time.monotonic()
#--| ANIMATIONS |----------------------------------------------------

def play_animation(config):
    #pylint: disable=eval-used
    eval(ANIMATIONS[config['animation']])(config)
    pixels.fill(0)

def indicate(event=None):
    if not isinstance(event, str):
        return
    event = event.strip().upper()
    if event == 'START':
        for _ in range(2):
            for i in range(10):
                pixels[i] = DEFAULT_COLOR
                time.sleep(0.05)
                pixels.fill(0)
    if event == 'CONNECTED':
        for _ in range(5):
            pixels.fill(0x0000FF)
            time.sleep(0.1)
            pixels.fill(0)
            time.sleep(0.1)
    if event == 'DISCONNECTED':
        for _ in range(5):
            pixels.fill(0x00FF00)
            time.sleep(0.1)
            pixels.fill(0)
            time.sleep(0.1)

indicate('START')
while True:
    uart_server.start_advertising()

    # wait for connection
    while not uart_server.connected:
        # check for shake while waiting
        if accelo.shake(snow_config['shake'], 5, 0):
            play_animation(snow_config)

    # connected
    indicate('CONNECTED')

    while uart_server.connected:

        if accelo.shake(snow_config['shake'], 5, 0):
            play_animation(snow_config)

        if uart_server.in_waiting:
            try:
                packet = Packet.from_stream(uart_server)
            except ValueError:
                continue

            if isinstance(packet, ColorPacket):
                #
                # COLOR
                #
                snow_config['color'] = packet.color
                pixels.fill(snow_config['color'])
                time.sleep(0.5)
                pixels.fill(0)

            if isinstance(packet, ButtonPacket) and packet.pressed:
                #
                # SPEED
                #
                if packet.button == ButtonPacket.UP:
                    speed = snow_config['speed'] - 0.05
                    speed = 0.05 if speed < 0.05 else speed
                    snow_config['speed'] = speed
                    play_animation(snow_config)
                if packet.button == ButtonPacket.DOWN:
                    speed = snow_config['speed'] + 0.05
                    snow_config['speed'] = speed
                    play_animation(snow_config)

                #
                # DURATION
                #
                if packet.button == ButtonPacket.LEFT:
                    duration = snow_config['duration'] - 1
                    duration = 1 if duration < 1 else duration
                    snow_config['duration'] = duration
                    play_animation(snow_config)
                if packet.button == ButtonPacket.RIGHT:
                    duration = snow_config['duration'] + 1
                    snow_config['duration'] = duration
                    play_animation(snow_config)

                #
                # ANIMATION
                #
                if packet.button == ButtonPacket.BUTTON_1:
                    snow_config['animation'] = 0
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_2:
                    snow_config['animation'] = 1
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_3:
                    snow_config['animation'] = 2
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_4:
                    snow_config['animation'] = 3
                    play_animation(snow_config)

    # disconnected
    indicate('DISCONNECTED')
