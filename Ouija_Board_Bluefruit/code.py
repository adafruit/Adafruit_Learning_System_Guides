# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

# BLE Ouija Board

import time
import random
import board
import digitalio
import neopixel
from adafruit_motorkit import MotorKit
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
import audiocore
import audiomixer
import audiobusio

# Prep the status LEDs on the Feather
blue_led = digitalio.DigitalInOut(board.BLUE_LED)
red_led = digitalio.DigitalInOut(board.RED_LED)
blue_led.direction = digitalio.Direction.OUTPUT
red_led.direction = digitalio.Direction.OUTPUT

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

num_motors = 1  # up to 4 motors depending on the prop you are driving

motorwing = MotorKit(i2c=board.I2C())
motorwing.frequency = 122  # tune this 50 - 200 range
max_throttle = 0.65  # tune this 0.2 - 1 range

# # make arrays for all the things we care about
motors = [None] * num_motors

motors[0] = motorwing.motor1

# # set motors to "off"
for i in range(num_motors):
    motors[i].throttle = None

# - Audio setup
audio = audiobusio.I2SOut(bit_clock=board.TX, word_select=board.MISO, data=board.RX)
mixer = audiomixer.Mixer(voice_count=2, sample_rate=11025, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)  # attach mixer to audio playback
wav_files = (('spooky_ouija.wav', 0.07, True), ('lars_ouija.wav', 0.09, False))
# open samples
for i in range(len(wav_files)):
    wave = audiocore.WaveFile(open(wav_files[i][0], "rb"))
    mixer.voice[i].level = 0  # start up with level down
    mixer.voice[i].play(wave, loop=wav_files[i][2])

# - NeoPixels
fire_color = 0xcc6600
fade_by = -1
num_leds = 7
max_bright = 0.5
led_pin = board.D6
leds = neopixel.NeoPixel(led_pin, num_leds, brightness=0.0, auto_write=False)
leds.fill(fire_color)
leds.show()

last_time = 0
next_duration = 0.2

print("BLE Ouija board")
print("Use Adafruit Bluefruit app to connect")


while True:
    blue_led.value = False
    ble.name = 'Ouija'
    ble.start_advertising(advertisement)

    while not ble.connected:
        # Wait for a connection.
        pass
    blue_led.value = True  # turn on blue LED when connected
    while ble.connected:
        if uart_service.in_waiting:
            # Packet is arriving.
            red_led.value = False  # turn off red LED
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True  # blink to show a packet has been received
                if packet.button == ButtonPacket.RIGHT:  # > button pressed
                    print("forward")
                    motors[0].throttle = max_throttle
                    time.sleep(0.1)  # wait a moment

                elif packet.button == ButtonPacket.LEFT:  # < button
                    print("reverse")
                    motors[0].throttle = max_throttle * -1
                    time.sleep(0.1)

                elif packet.button == ButtonPacket.DOWN:  # v button
                    print("stop")
                    motors[0].throttle = None
                    time.sleep(0.1)

                elif packet.button == ButtonPacket.BUTTON_1:  # 1 button
                    print("on BG music")
                    mixer.voice[0].level = wav_files[0][1]
                    time.sleep(0.1)

                elif packet.button == ButtonPacket.BUTTON_3:  # 3 button
                    print("off BG music")
                    mixer.voice[0].level = 0.0
                    time.sleep(0.1)

                elif packet.button == ButtonPacket.BUTTON_2:  # 2 button
                    print("on led & Lars")
                    leds.brightness = max_bright
                    mixer.voice[1].play(wave, loop=False)
                    mixer.voice[1].level = wav_files[1][1]
                    time.sleep(0.1)

                elif packet.button == ButtonPacket.BUTTON_4:  # 4 button
                    print("off led & Lars")
                    leds.brightness = 0
                    mixer.voice[1].level = 0.0
                    time.sleep(0.1)

        # fade down all LEDs
        leds[:] = [[min(max(i+fade_by, 0), 255) for i in l] for l in leds]
        leds.show()

        # add new fire to leds
        if time.monotonic() - last_time > next_duration:
            last_time = time.monotonic()
            next_duration = random.uniform(0.95, 1.95)  # tune these nums
            # for i in range( 1):
            c = fire_color  # get our color
            c = (c >> 16 & 0xff, c >> 8 & 0xff, c & 0xff)  # make it a tuple
            leds[random.randint(0, num_leds-1)] = c
