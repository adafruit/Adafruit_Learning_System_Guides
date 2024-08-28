# SPDX-FileCopyrightText: Copyright (c) 2024 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
USB C PD power supply w HUSB238
pick voltages and then set them, measures high side current with INA219
"""
import time
import board
import keypad
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import adafruit_husb238
from adafruit_ina219 import INA219

i2c = board.I2C()

tft_d0_button = keypad.Keys((board.D0,), value_when_pressed=False, pull=True)
tft_buttons = keypad.Keys((board.D1, board.D2), value_when_pressed=True, pull=True)

# Initialize INA219 current sensor
ina219 = INA219(i2c)

TXTCOL_VOLT = 0x8f00cd
TXTCOL_CURR = 0xb30090
TXTCOL_DIM = 0xCD8F00
TXTCOL_HEAD = 0xCD8F00
TXTCOL_BTN = 0xa0a0a0
BGCOL = 0x220030
display = board.DISPLAY
group = displayio.Group()

background_rect = Rect(0, 0, display.width, display.height, fill=BGCOL)
group.append(background_rect)

warning_text = "plug in USB C PD cable, press reset"

FONT = terminalio.FONT

display.root_group = group

RUNNING = None
PLUGGED = None

# Initialize HUSB238 PD dummy
try:
    pd = adafruit_husb238.Adafruit_HUSB238(i2c)
    RUNNING = True
    PLUGGED = True
except ValueError:
    print("plug in a USB C PD cable, then press reset")
    RUNNING = False
    PLUGGED = False

    warning_label = label.Label(
        FONT, text=warning_text, color=0xdd0000,
        scale=1, anchor_point=(0,0),
        anchored_position=(20, 10)
    )
    group.append(warning_label)
    #stop the code here

while not RUNNING:
    pass

while RUNNING:
    voltages = pd.available_voltages
    print("The following voltages are available:")
    for i, volts in enumerate(voltages):
        print(f"{volts}V")

    v = 0

    if pd.attached:
        pd.voltage = voltages[0]
        print(f"Voltage is set to {pd.voltage}V/{pd.current}A")

    display = board.DISPLAY

    group = displayio.Group()
    background_rect = Rect(0, 0, display.width, display.height, fill=BGCOL)
    group.append(background_rect)
    vert_bar = Rect(40, 0, 3, display.height, fill=0x000000)
    group.append(vert_bar)

    FONT = terminalio.FONT

    header_label = label.Label(
        FONT, text="Power Deliverer", color=TXTCOL_HEAD,
        scale=2, x=50, y=8
    )
    group.append(header_label)
    voltage_label = label.Label(
        FONT, text=str(voltages[0])+"V", color=TXTCOL_VOLT,
        scale=5, anchor_point=(0,0),
        anchored_position=(50, 20)
    )
    group.append(voltage_label)
    current_label = label.Label(
        FONT, text="0mA", color=TXTCOL_CURR,
        scale=5, anchor_point=(0,0),
        anchored_position=(50, 80)
    )
    group.append(current_label)
    go_label = label.Label(FONT, text="set", color=TXTCOL_BTN, scale=2, x=1, y=6)
    group.append(go_label)
    up_label = label.Label(FONT, text="+v", color=TXTCOL_BTN, scale=2, x=1, y=display.height//2-2)
    group.append(up_label)
    down_label = label.Label(FONT, text="-v", color=TXTCOL_BTN, scale=2, x=1, y=display.height-12)
    group.append(down_label)

    display.root_group = group


    while True:
        tft_d0_button_event = tft_d0_button.events.get()
        if tft_d0_button_event and tft_d0_button_event.pressed:
            try:
                print(f"Setting to {voltages[v]}V!")
                pd.voltage = voltages[v]
                voltage_label.text=str(voltages[v]) + "V"
                voltage_label.color=TXTCOL_VOLT
                print(f"It is set to {pd.voltage}V/{pd.current}A")
                print()
                PLUGGED=True
            except OSError:
                print(warning_text)
                voltage_label.text="replug"
                current_label.text="USB C"
                PLUGGED=False

        if PLUGGED:
            tft_buttons_event = tft_buttons.events.get()
            if tft_buttons_event and tft_buttons_event.pressed:
                if tft_buttons_event.key_number == 0:
                    v = (v + 1) % len(voltages)  # maybe have this stop at max
                    voltage_label.color=TXTCOL_DIM
                    voltage_label.text="["+str(voltages[v]) + "V]"
                    print(f"Voltage will be set to {voltages[v]}V")

                if tft_buttons_event.key_number == 1:
                    v = (v - 1) % len(voltages)  # maybe have this stop at min
                    voltage_label.color=TXTCOL_DIM
                    voltage_label.text="["+str(voltages[v]) + "V]"
                    print(f"Voltage will be set to {voltages[v]}V")

            current = ina219.current  # current in mA
            # power = ina219.power  # power in watts
            current_label.text= str(abs(int(current))) + "mA"

            if ina219.overflow:
                print("Internal Math Overflow Detected!")
                print("")
            time.sleep(0.2)
