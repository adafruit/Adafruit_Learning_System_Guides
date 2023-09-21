# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import asyncio
import board
import digitalio
from rainbowio import colorwheel
import keypad
import displayio
import busio
import adafruit_seesaw.seesaw
import adafruit_seesaw.neopixel
import adafruit_seesaw.rotaryio
import adafruit_seesaw.digitalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import neopixel

# default MIDI channel (1-16)
midi_in_channel = 2
midi_out_channel = 2

# MIDI CC messages, values and names assigned to each encoder
cc_values = [
    {'cc_val': (0, 127), 'cc_message': (14), 'cc_name': "Volume"},
    {'cc_val': (0, 127), 'cc_message': (15), 'cc_name': "Repeats"},
    {'cc_val': (0, 127), 'cc_message': (16), 'cc_name': "Size"},
    {'cc_val': (0, 127), 'cc_message': (17), 'cc_name': "Mod"},
    {'cc_val': (0, 127), 'cc_message': (18), 'cc_name': "Spread"},
    {'cc_val': (0, 127), 'cc_message': (19), 'cc_name': "Scan"},
    {'cc_val': (0, 127), 'cc_message': (20), 'cc_name': "Ramp"},
    {'cc_val': (1, 3), 'cc_message': (21), 'cc_name': "Mod Number"},
    {'cc_val': (1, 3), 'cc_message': (22), 'cc_name': "Mod Bank"},
    {'cc_val': (1, 3), 'cc_message': (23), 'cc_name': "Mode"},
    {'cc_val': (0, 1), 'cc_message': (102), 'cc_name': "Bypass/Engage"},
    {'cc_val': (0, 127), 'cc_message': (93), 'cc_name': "Tap Tempo"},
    {'cc_val': (0, 1), 'cc_message': (24), 'cc_name': "Loop (R Hold)"},
    {'cc_val': (0, 1), 'cc_message': (25), 'cc_name': "Scan (L Hold)"},
    {'cc_val': (0, 127), 'cc_message': (26), 'cc_name': "Clear (Both Hold)"},
    {'cc_val': (0, 1), 'cc_message': (51), 'cc_name': "MIDI Clock Ignore"}
    ]

displayio.release_displays()

oled_reset = board.D13

i2c = board.STEMMA_I2C()
# STEMMA OLED setup
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

splash = displayio.Group()
display.show(splash)
font = bitmap_font.load_font('/OCRA_small.pcf')
# main label/MIDI message name text; centered
main_area = label.Label(
    font, text="4x4 MIDI Messenger", color=0xFFFFFF)
main_area.anchor_point = (0.5, 0.0)
main_area.anchored_position = (display.width / 2, 0)
# MIDI message number text
msg_area = label.Label(
    font, text="CC Msg: 10", color=0xFFFFFF)
msg_area.anchor_point = (0.0, 0.5)
msg_area.anchored_position = (0, display.height / 2)
# MIDI message value text
val_area = label.Label(
    font, text="CC Val: 50", color=0xFFFFFF)
val_area.anchor_point = (0.0, 1.0)
val_area.anchored_position = (0, display.height)
# MIDI message status text
status_area = label.Label(
    font, text="Sent!", color=0xFFFFFF)
status_area.anchor_point = (1.0, 1.0)
status_area.anchored_position = (display.width, display.height)

splash.append(main_area)
splash.append(msg_area)
splash.append(val_area)
splash.append(status_area)
# MIDI over UART setup for MIDI FeatherWing
uart = busio.UART(board.TX, board.RX, baudrate=31250, timeout=0.001)
midi = adafruit_midi.MIDI(
    midi_in=uart,
    midi_out=uart,
    in_channel=(midi_in_channel - 1),
    out_channel=(midi_out_channel - 1),
    debug=False,
)
# quad rotary encoder setup
ss0 = adafruit_seesaw.seesaw.Seesaw(i2c, 0x49)
ss1 = adafruit_seesaw.seesaw.Seesaw(i2c, 0x4A)
ss2 = adafruit_seesaw.seesaw.Seesaw(i2c, 0x4B)
ss3 = adafruit_seesaw.seesaw.Seesaw(i2c, 0x4C)
# button pins for the encoders
pins = [12, 14, 17, 9]
# interrupts for the button pins. pins are passed as a bitmask
ss0.set_GPIO_interrupts(1 << pins[0] | 1 << pins[1] | 1 << pins[2] | 1 << pins[3], True)
ss1.set_GPIO_interrupts(1 << pins[0] | 1 << pins[1] | 1 << pins[2] | 1 << pins[3], True)
ss2.set_GPIO_interrupts(1 << pins[0] | 1 << pins[1] | 1 << pins[2] | 1 << pins[3], True)
ss3.set_GPIO_interrupts(1 << pins[0] | 1 << pins[1] | 1 << pins[2] | 1 << pins[3], True)
# arrays for the encoders and switches
enc0 = []
enc1 = []
enc2 = []
enc3 = []
sw0 = []
sw1 = []
sw2 = []
sw3 = []
# creating encoders and switches, enabling interrupts for encoders
for i in range(4):
    enc0.append(adafruit_seesaw.rotaryio.IncrementalEncoder(ss0, i))
    enc1.append(adafruit_seesaw.rotaryio.IncrementalEncoder(ss1, i))
    enc2.append(adafruit_seesaw.rotaryio.IncrementalEncoder(ss2, i))
    enc3.append(adafruit_seesaw.rotaryio.IncrementalEncoder(ss3, i))
    sw0.append(adafruit_seesaw.digitalio.DigitalIO(ss0, pins[i]))
    sw0[i].switch_to_input(digitalio.Pull.UP)
    sw1.append(adafruit_seesaw.digitalio.DigitalIO(ss1, pins[i]))
    sw1[i].switch_to_input(digitalio.Pull.UP)
    sw2.append(adafruit_seesaw.digitalio.DigitalIO(ss2, pins[i]))
    sw2[i].switch_to_input(digitalio.Pull.UP)
    sw3.append(adafruit_seesaw.digitalio.DigitalIO(ss3, pins[i]))
    sw3[i].switch_to_input(digitalio.Pull.UP)
    ss0.enable_encoder_interrupt(encoder=i)
    ss1.enable_encoder_interrupt(encoder=i)
    ss2.enable_encoder_interrupt(encoder=i)
    ss3.enable_encoder_interrupt(encoder=i)
# neopixels on each PCB
pix0 = adafruit_seesaw.neopixel.NeoPixel(ss0, 18, 4, auto_write = True)
pix0.brightness = 0.5
pix1 = adafruit_seesaw.neopixel.NeoPixel(ss1, 18, 4, auto_write = True)
pix1.brightness = 0.5
pix2 = adafruit_seesaw.neopixel.NeoPixel(ss2, 18, 4, auto_write = True)
pix2.brightness = 0.5
pix3 = adafruit_seesaw.neopixel.NeoPixel(ss3, 18, 4, auto_write = True)
pix3.brightness = 0.5
# onboard Feather neopixel
pix_feather = neopixel.NeoPixel(board.NEOPIXEL, 1, auto_write = True)
pix_feather.brightness = 0.5
# encoder position arrays
last_pos0 = [60, 60, 60, 60]
last_pos1 = [60, 60, 60, 0]
last_pos2 = [0, 0, 0, 120]
last_pos3 = [0, 0, 0, 0]
pos0 = [60, 60, 60, 60]
pos1 = [60, 60, 60, 0]
pos2 = [0, 0, 0, 120]
pos3 = [0, 0, 0, 0]
# color arrays for the neopixels
c0 = [0, 16, 32, 48]
c1 = [64, 80, 96, 112]
c2 = [128, 144, 160, 176]
c3 = [192, 208, 224, 240]
# setting starting colors for neopixels
for r in range(4):
    pix0[r] = colorwheel(c0[r])
    pix1[r] = colorwheel(c1[r])
    pix2[r] = colorwheel(c2[r])
    pix3[r] = colorwheel(c3[r])
# feather neopixel color
c_feather = 0
pix_feather[0] = colorwheel(c_feather)
# array of all 16 encoder positions
encoder_posititions = [60, 60, 60, 60, 60, 60, 60, 60, 0, 0, 0, 120, 0, 0, 0, 0]

class MIDI_Messages:
    # tracks sending a message and index 0-15
    def __init__(self):
        self.send_msg = False
        self.midi_index = 0

class NeoPixel_Attributes:
    # tracks color, neopixel index and seesaw
    def __init__(self):
        self.color = c0
        self.index = 0
        self.strip = pix0
        self.feather_color = c_feather

async def send_midi(midi_msg):
    # sends MIDI message if send_msg is True/button pressed
    while True:
        if midi_msg.send_msg is True:
            m = midi_msg.midi_index
            main_area.text = f"{cc_values[m]['cc_name']}"
            msg_area.text = f"CC Msg: {cc_values[m]['cc_message']}"
            val_area.text = f"CC Val: {encoder_posititions[m]}"
            midi.send(ControlChange(cc_values[m]['cc_message'], encoder_posititions[m]))
            status_area.text = "Sent!"
            print(f"sending midi: {m}, {encoder_posititions[m]}, {cc_values[m]['cc_message']}")
            time.sleep(1)
            midi_msg.send_msg = False
        else:
            status_area.text = " "
        await asyncio.sleep(0)

async def rainbows(the_color):
    # Updates colors of the neopixels to scroll through rainbow
    while True:
        the_color.feather_color += 8
        the_color.strip[the_color.index] = colorwheel(the_color.color[the_color.index])
        pix_feather[0] = colorwheel(the_color.feather_color)
        await asyncio.sleep(0)

async def monitor_interrupts(pin0, pin1, pin2, pin3, the_color, midi_msg): #pylint: disable=too-many-statements
    # function to keep encoder value pinned between CC value range
    def normalize(val, min_v, max_v):
        return max(min(max_v, val), min_v)
    # read encoder function
    def read_encoder(enc_group, pos, last_pos, pix, colors, index_diff):
        # check all four encoders if interrupt is detected
        for p in range(4):
            pos[p] = enc_group[p].position
            if pos[p] != last_pos[p]:
                main_index = p + index_diff
                # update CC value
                if pos[p] > last_pos[p]:
                    colors[p] += 8
                    encoder_posititions[main_index] = encoder_posititions[main_index] + 1
                else:
                    colors[p] -= 8
                    encoder_posititions[main_index] = encoder_posititions[main_index] - 1
                encoder_posititions[main_index] = normalize(encoder_posititions[main_index],
                                                cc_values[main_index]['cc_val'][0],
                                                cc_values[main_index]['cc_val'][1])
                colors[p] = (colors[p] + 256) % 256  # wrap around to 0-256
                print(main_index, encoder_posititions[main_index])
                main_area.text = f"{cc_values[main_index]['cc_name']}"
                msg_area.text = f"CC Msg: {cc_values[main_index]['cc_message']}"
                val_area.text = f"CC Val: {encoder_posititions[main_index]}"
                last_pos[p] = pos[p]
                # update NeoPixel colors
                the_color.color = colors
                the_color.index = p
                the_color.strip = pix
    # function to read button press
    def press_switches(sw, index):
        if not sw[index].value:
            # signals that a MIDI message should be sent
            midi_msg.send_msg = True
            midi_msg.midi_index = index
            print(f"button {index} pressed")
    # interrupt pins are passed as a keypad
    with keypad.Keys(
        (pin0, pin1, pin2, pin3,), value_when_pressed=False, pull=True
    ) as keys:
        while True:
            key_event = keys.events.get()
            if key_event and key_event.pressed:
                key_number = key_event.key_number
                # seesaw 0
                if key_number == 0:
                    read_encoder(enc0, pos0, last_pos0, pix0, c0, 0)
                    press_switches(sw0, 0)
                    press_switches(sw0, 1)
                    press_switches(sw0, 2)
                    press_switches(sw0, 3)
                # seesaw 1
                elif key_number == 1:
                    read_encoder(enc1, pos1, last_pos1, pix1, c1, 4)
                    press_switches(sw1, 0)
                    press_switches(sw1, 1)
                    press_switches(sw1, 2)
                    press_switches(sw1, 3)
                    # update index to 4-7
                    midi_msg.midi_index = midi_msg.midi_index + 4
                # seesaw 2
                elif key_number == 2:
                    read_encoder(enc2, pos2, last_pos2, pix2, c2, 8)
                    press_switches(sw2, 0)
                    press_switches(sw2, 1)
                    press_switches(sw2, 2)
                    press_switches(sw2, 3)
                    # update index 8-11
                    midi_msg.midi_index = midi_msg.midi_index + 8
                # seesaw 3
                else:
                    read_encoder(enc3, pos3, last_pos3, pix3, c3, 12)
                    press_switches(sw3, 0)
                    press_switches(sw3, 1)
                    press_switches(sw3, 2)
                    press_switches(sw3, 3)
                    # update index 12-15
                    midi_msg.midi_index = midi_msg.midi_index + 12
            # clear interrupt flag to reset interrupt pin
            ss0.get_GPIO_interrupt_flag()
            ss1.get_GPIO_interrupt_flag()
            ss2.get_GPIO_interrupt_flag()
            ss3.get_GPIO_interrupt_flag()
            await asyncio.sleep(0)

async def main():
    the_color = NeoPixel_Attributes()
    midi_msg = MIDI_Messages()
    # interrupt listener task
    interrupt_task = asyncio.create_task(monitor_interrupts(board.D5, board.D6, board.D9,
                                                            board.D10, the_color, midi_msg))
    # neopixel task
    pixels_task = asyncio.create_task(rainbows(the_color))
    # midi task
    midi_task = asyncio.create_task(send_midi(midi_msg))

    await asyncio.gather(interrupt_task, pixels_task, midi_task)

asyncio.run(main())
