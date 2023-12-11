# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Motorized fader demo
import time
import board
import pwmio
import analogio
import touchio
import neopixel
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
from adafruit_motor import motor

MIDI_DEMO = False  # set to True to send MIDI CC

# optional MIDI setup
if MIDI_DEMO:
    import usb_midi
    import adafruit_midi
    from adafruit_midi.control_change import ControlChange
    midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
    fader_cc_number = 16

# Button setup to store four saved values
button_pins = (board.D10, board.D9, board.D6, board.D5)
buttons = []
for button_pin in button_pins:
    tmp_pin = DigitalInOut(button_pin)
    tmp_pin.pull = Pull.UP
    buttons.append(Debouncer(tmp_pin))

saved_positions = (230, 180, 120, 60)  # pre-saved positions for the buttons to call

# Slide pot setup
fader = analogio.AnalogIn(board.A0)
fader_position = fader.value  # ranges from 0-65535
fader_pos = fader.value // 256  # make 0-255 range
last_fader_pos = fader_pos

# Motor setup
PWM_PIN_A = board.D12  # pick any pwm pins on their own channels
PWM_PIN_B = board.D11

# DC motor driver setup -- these pins go to h-bridge driver such as L9110
pwm_a = pwmio.PWMOut(PWM_PIN_A, frequency=50)
pwm_b = pwmio.PWMOut(PWM_PIN_B, frequency=50)
motor1 = motor.DCMotor(pwm_a, pwm_b)

# Touch setup  pin goes from touch pin on slide pot to touch capable pin and then 1MΩ to gnd
touch = touchio.TouchIn(board.A3)
touch.threshold = touch.raw_value + 30  # tune for fader knob cap

# NeoPixel setup
led = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)
led.fill(0xff0000)

def clamp(num, min_value, max_value):  # function for clamping motor throttle -1.0 to 1.0
    return max(min(num, max_value), min_value)

def go_to_position(new_position):
    global fader_pos  # pylint: disable=global-statement
    fader_pos = int(fader.value//256)
    while abs(fader_pos - new_position) > 2 :
        if fader_pos > new_position :
            speed = 2.25 * abs(fader_pos - new_position) / 256 + 0.12
            speed = clamp(speed, -1.0, 1.0)
            motor1.throttle = speed
            led[0] = (fader_pos, 0, 0)

            if MIDI_DEMO:
                global fader_cc  # pylint: disable=global-statement
                fader_cc = int(fader_pos / 2)  # cc is 0-127
                midi.send(ControlChange(fader_cc_number, fader_cc))

        if fader_pos < new_position:
            speed = -2.25 * abs(fader_pos - new_position) / 256 - 0.12
            speed = clamp(speed, -1.0, 1.0)
            motor1.throttle = speed
            led[0] = (fader_pos, 0, 0)

            if MIDI_DEMO:
                fader_cc = int(fader_pos / 2)  # cc is 0-127
                midi.send(ControlChange(fader_cc_number, fader_cc))

        fader_pos = int(fader.value//256)
    motor1.throttle = None
print("--__ Flying Fader Demo __--")
print("\n"*4)

go_to_position(saved_positions[3])  # boot up demo
go_to_position(saved_positions[0])
time.sleep(.6)

current_saved_position = 0  # state to store which is current position from the list

while True:
    for i in range(len(buttons)):
        buttons[i].update()
        if buttons[i].fell:  # if a button is pressed, update the position from list
            current_saved_position = i

    if touch.value:
        motor1.throttle = None  # idle
    else:
        go_to_position(saved_positions[current_saved_position])

    filter_amt = 0.1  # higher number will be a slower filter between 1.0 and 0.1 is good
    fader_pos = int((filter_amt * last_fader_pos) + ((1.0-filter_amt) * fader.value//256))
    led[0] = (fader_pos, 0, 0)
    if abs(fader_pos - last_fader_pos) > 1 :  # do things in here, e.g. send MIDI CC
        fader_width = 90  # for text visualization in serial output
        print("-" * (fader_width - int(fader_pos/3)), fader_pos, "-" * int(fader_pos/3), end='\r')
        last_fader_pos = fader_pos
        if MIDI_DEMO:
            fader_cc = int(fader_pos / 2)  # cc is 0-127
            midi.send(ControlChange(fader_cc_number, fader_cc))
