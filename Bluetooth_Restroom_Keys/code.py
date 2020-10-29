"""Bluetooth Key Tracker."""
from adafruit_ble import BLERadio
from adafruit_led_animation.animation import Pulse, Solid
import adafruit_led_animation.color as color
from analogio import AnalogIn
from array import array
from audiobusio import I2SOut
from audiocore import RawSample, WaveFile
from board import BATTERY, D5, D6, D9, NEOPIXEL, RX, TX
from digitalio import DigitalInOut, Direction, Pull
from math import pi, sin
from neopixel import NeoPixel
from time import sleep

battery = AnalogIn(BATTERY)

ble = BLERadio()
hit_status = [color.RED, color.ORANGE, color.AMBER, color.GREEN]

pixel = NeoPixel(NEOPIXEL, 1)
pulse = Pulse(pixel,
              speed=0.01,
              color=color.PURPLE,  # Use CYAN for Male Key
              period=3,
              min_intensity=0.0,
              max_intensity=0.5)

solid = Solid(pixel, color.GREEN)

reed_switch = DigitalInOut(D5)
reed_switch.direction = Direction.INPUT
reed_switch.pull = Pull.UP

amp_enable = DigitalInOut(D6)
amp_enable.direction = Direction.OUTPUT
amp_enable.value = False


def play_tone():
    """Generate tone and transmit to I2S amp."""
    length = 4000 // 440
    sine_wave = array("H", [0] * length)
    for i in range(length):
        sine_wave[i] = int(sin(pi * 2 * i / 18) * (2 ** 15) + 2 ** 15)

    sample = RawSample(sine_wave, sample_rate=8000)
    i2s = I2SOut(TX, RX, D9)
    i2s.play(sample, loop=True)
    sleep(1)
    i2s.stop()
    sample.deinit()
    i2s.deinit()


def play_message():
    """Play recorded WAV message and transmit to I2S amp."""
    with open("d1.wav", "rb") as file:
        wave = WaveFile(file)
        i2s = I2SOut(TX, RX, D9)
        i2s.play(wave)
        while i2s.playing:
            pass
        wave.deinit()
        i2s.deinit()


boundary_violations = 0

while True:
    if reed_switch.value:  # Not Docked
        hits = 0
        try:
            advertisements = ble.start_scan(timeout=3)
            for advertisement in advertisements:
                addr = advertisement.address
                if (advertisement.scan_response and
                   addr.type == addr.RANDOM_STATIC):
                    if advertisement.complete_name == '<Your 1st beacon name here>':
                        hits |= 0b001
                    elif advertisement.complete_name == '<Your 2nd beacon name here>':
                        hits |= 0b010
                    elif advertisement.complete_name == '<Your 3rd beacon name here>':
                        hits |= 0b100
        except Exception as e:
            print(repr(e))
        hit_count = len([ones for ones in bin(hits) if ones == '1'])
        solid.color = hit_status[hit_count]
        solid.animate()
        sleep(1)
        if hit_count == 0:
            if boundary_violations % 60 == 0:  # Play message every 60 cycles
                amp_enable.value = True
                sleep(1)
                play_tone()
                sleep(1)
                play_message()
                sleep(1)
                amp_enable.value = False
            boundary_violations += 1
        else:
            boundary_violations = 0

    else:  # Docked
        boundary_violations = 0
        voltage = battery.value * 3.3 / 65535 * 2
        if voltage < 3.7:
            pulse.period = 1  # Speed up LED pulse for low battery
        else:
            pulse.period = 3
        pulse.animate()
