# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''QT Py RP2040 MIDI Breath Controller with BMP585'''
import time
import board
import simpleio
from adafruit_bmp5xx import BMP5XX
from adafruit_seesaw import digitalio, neopixel, rotaryio, seesaw
import usb_midi
import adafruit_midi
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.channel_pressure import ChannelPressure

SEALEVELPRESSURE_HPA = 1013.25
change_sense = 0.1 # change sensitivity
low_press = 995 # lowest pressure reading range
high_press = 1032 # highest pressure reading range

i2c = board.STEMMA_I2C()
bmp = BMP5XX.over_i2c(i2c)
bmp.sea_level_pressure = SEALEVELPRESSURE_HPA

seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
encoder = rotaryio.IncrementalEncoder(seesaw)
pixel = neopixel.NeoPixel(seesaw, 6, 1)
pixel.brightness = 0.2

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
# CC message channels
# last index is place holder for Channel Pressure message type
messages = [1, 2, 7, 64, 0]
# neopixel colors to associate with CC messages
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
          (255, 255, 0), (255, 0, 255)]

pressure = 0
mod_val1 = 0
mod_val2 = 0
effect_index = 0
last_position = 0
button_state = False
pixel.fill(colors[effect_index])

while True:
    position = -encoder.position
    if position != last_position:
        # encoder changes midi CC message type
        if position > last_position:
            effect_index = (effect_index + 1) % len(messages)
        else:
            effect_index = (effect_index - 1) % len(messages)
        pixel.fill(colors[effect_index])
        last_position = position
    if not button.value and not button_state:
        pixel.fill((255, 255, 255))
        # button press sends MIDI panic
        panic = ControlChange(123, 0)
        midi.send(panic)
        # and turns sustain off
        sus_off = ControlChange(64, 0)
        midi.send(sus_off)
        button_state = True
    if button.value and button_state:
        # reset neopixel to CC msg color
        pixel.fill(colors[effect_index])
        button_state = False
    if bmp.data_ready:
        # get pressure reading
        pressure = bmp.pressure
        # if the pressure has changed enough
        # (adjust change_sense value at top to inc or dec)
        if abs(pressure - mod_val2) > change_sense:
            # map pressure reading to CC range
            mod_val1 = round(simpleio.map_range(pressure, low_press, high_press, 0, 127))
            #  updates previous value to hold current value
            mod_val2 = pressure
            # MIDI data has to be sent as an integer
            modulation = int(mod_val1)
            # possible midi messages determined by effect_index value:
            # 1: modulation
            # 2: breath controller
            # 7: volume
            # 64: sustain
            # ChannelPressure(modulation)
            if effect_index < 4:
                # prep CC message with CC number and value as mapped pressure reading
                modWheel = ControlChange(messages[effect_index], modulation)
            else:
                # prep Channel Pressure message with value as mapped pressure reading
                modWheel = ChannelPressure(modulation)
            # CC message is sent
            midi.send(modWheel)
            # print(modWheel)
            # delay to settle MIDI data
            time.sleep(0.001)
