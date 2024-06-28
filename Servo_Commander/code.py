# SPDX-FileCopyrightText: 2024 johnpark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
Servo Commander
- Feather Reverse TFT ESP32-S3 + two servos + two push encoders
- test servo ranges with encoder rotation
- store saved positions with enc button + D0, D1, D2 buttons
- recall saved positions with D0, D1, D2
- playback animation by pressing both push encoders
'''

import time
import board
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import rotaryio
import pwmio
from adafruit_motor import servo
import keypad

# Define custom servo pulse range variables
s_cfgs = [
    {'min_pulse': 600, 'max_pulse': 2400, 'min_ang': 10, 'max_ang': 170},
    {'min_pulse': 600, 'max_pulse': 2300, 'min_ang': 10, 'max_ang': 170}
]

# Setup the PWM output for the servos
pwm_pins = [board.D10, board.D11]
servo_motors = []

for i, config in enumerate(s_cfgs):
    pwm = pwmio.PWMOut(pwm_pins[i], duty_cycle=2**15, frequency=50)
    servo_motor = servo.Servo(pwm, min_pulse=config['min_pulse'], max_pulse=config['max_pulse'])
    servo_motors.append(servo_motor)
    servo_motor.angle = 90

s_saves = [
    [s_cfgs[0]['min_ang'], 90, s_cfgs[0]['max_ang']],
    [s_cfgs[1]['min_ang'], 90, s_cfgs[1]['max_ang']]
]

# Setup the rotary encs
encs = [
    rotaryio.IncrementalEncoder(board.A2, board.A1),
    rotaryio.IncrementalEncoder(board.A5, board.A4)
]

for enc in encs:
    enc.position = 90

last_positions = [enc.position for enc in encs]

# Setup the buttons
enc_buttons = keypad.Keys((board.D13, board.D12), value_when_pressed=False, pull=True)
tft_d0_button = keypad.Keys((board.D0,), value_when_pressed=False, pull=True)
tft_buttons = keypad.Keys((board.D1, board.D2), value_when_pressed=True, pull=True)

def set_servo_angle(s_servo_motor, s_angle, s_enc, min_ang, max_ang):
    s_angle = min(max(s_angle, min_ang), max_ang)
    s_servo_motor.angle = s_angle
    s_enc.position = s_angle

def playback(mode, speed, steps):
    for k in range(3):  # Loop through each save position (assuming 3 saves per motor)
        for m in range(len(servo_motors)):
            p_servo_motor = servo_motors[m]
            p_enc = encs[m]
            save = s_saves[m][k]  # Get the k-th save position for the m-th motor

            if mode:
                direction = 1 if save > enc.position else -1
                for p_angle in range(enc.position, save, direction * steps):
                    p_servo_motor.angle = p_angle
                    time.sleep(speed)
                p_enc.position = save
            else:
                servo_motor.angle = save
                time.sleep(0.75)


# Setup the display
display = board.DISPLAY
group = displayio.Group()
background_rect = Rect(0, 10, display.width, display.height - 10, fill=0x000010)
group.append(background_rect)
mid_bar = Rect(116, 0, 3, display.height, fill=0x00000)
group.append(mid_bar)
top_bar = Rect(0, 0, display.width, 20, fill=0x000000)
group.append(top_bar)

FONT = terminalio.FONT
TXTCOL = 0xFFFF00

# Create labels
labels = []
for i, config in enumerate(s_cfgs):
    lbl = label.Label(FONT, text=f"Pulse: {config['min_pulse']}-{config['max_pulse']}",color=TXTCOL,
            scale=1, anchor_point=(0, 0), anchored_position=(5 + 125 * i, 5))
    labels.append(lbl)
    group.append(lbl)

for i in range(2):
    lbl = label.Label(FONT, text="Angle:-", color=TXTCOL, scale=2, anchor_point=(0, 0),
            anchored_position=(4 + 126 * i, 24))
    labels.append(lbl)
    group.append(lbl)

for i in range(2):
    for j in range(3):
        lbl = label.Label(FONT, text=f"D{j}:{s_saves[i][j]}", color=TXTCOL, scale=2,
                anchor_point=(0, 0), anchored_position=(4 + i * 126, 48 + 24 * j))
        labels.append(lbl)
        group.append(lbl)

display.root_group = group

modifier1 = False
modifier2 = False

print("[]-Servo Commander READY-[]")

while True:
    enc_button_event = enc_buttons.events.get()
    if enc_button_event:
        if enc_button_event.pressed:
            if enc_button_event.key_number == 0:
                modifier1 = True
            elif enc_button_event.key_number == 1:
                modifier2 = True

        if enc_button_event.released:
            if enc_button_event.key_number == 0:
                modifier1 = False
            elif enc_button_event.key_number == 1:
                modifier2 = False

    if modifier1 and modifier2:
        print("Playback")
        playback(True, 0.006, 2)

    tft_d0_button_event = tft_d0_button.events.get()
    if tft_d0_button_event and tft_d0_button_event.pressed:
        if modifier1:
            s_saves[0][0] = min(max(encs[0].position, s_cfgs[0]['min_ang']), s_cfgs[0]['max_ang'])
            print("D0 save motor1:", s_saves[0][0])
            labels[4].text = f"D0:{s_saves[0][0]}"
        elif modifier2:
            s_saves[1][0] = min(max(encs[1].position, s_cfgs[1]['min_ang']), s_cfgs[1]['max_ang'])
            print("D0 save motor2:", s_saves[1][0])
            labels[7].text = f"D0:{s_saves[1][0]}"
        else:
            for i in range(len(servo_motors)):
                servo_motor = servo_motors[i]
                enc = encs[i]
                s_save = s_saves[i][0]
                config = s_cfgs[i]
                print(f"D0 recalled motor{i+1}:", s_save)
                set_servo_angle(servo_motor, s_save, enc, config['min_ang'], config['max_ang'])
                labels[2 + i].text = f"Angle:{s_save}"

    tft_buttons_event = tft_buttons.events.get()
    if tft_buttons_event and tft_buttons_event.pressed:
        if tft_buttons_event.key_number == 0:
            if modifier1:
                s_saves[0][1] = min(max(encs[0].position,s_cfgs[0]['min_ang']),s_cfgs[0]['max_ang'])
                print("D1 save motor1:", s_saves[0][1])
                labels[5].text = f"D1:{s_saves[0][1]}"
            elif modifier2:
                s_saves[1][1] = min(max(encs[1].position,s_cfgs[1]['min_ang']),s_cfgs[1]['max_ang'])
                print("D1 save motor2:", s_saves[1][1])
                labels[8].text = f"D1:{s_saves[1][1]}"
            else:
                for i in range(len(servo_motors)):
                    servo_motor = servo_motors[i]
                    enc = encs[i]
                    s_save = s_saves[i][1]
                    config = s_cfgs[i]
                    print(f"D1 recalled motor{i+1}:", s_save)
                    set_servo_angle(servo_motor, s_save, enc, config['min_ang'], config['max_ang'])
                    labels[2 + i].text = f"Angle:{s_save}"
        elif tft_buttons_event.key_number == 1:
            if modifier1:
                s_saves[0][2] = min(max(encs[0].position,s_cfgs[0]['min_ang']),s_cfgs[0]['max_ang'])
                print("D2 save motor1:", s_saves[0][2])
                labels[6].text = f"D2:{s_saves[0][2]}"
            elif modifier2:
                s_saves[1][2] = min(max(encs[1].position,s_cfgs[1]['min_ang']),s_cfgs[1]['max_ang'])
                print("D2 save motor2:", s_saves[1][2])
                labels[9].text = f"D2:{s_saves[1][2]}"
            else:
                for i in range(len(servo_motors)):
                    servo_motor = servo_motors[i]
                    enc = encs[i]
                    s_save = s_saves[i][2]
                    config = s_cfgs[i]
                    print(f"D2 recalled motor{i+1}:", s_save)
                    set_servo_angle(servo_motor, s_save, enc, config['min_ang'], config['max_ang'])
                    labels[2 + i].text = f"Angle:{s_save}"

    for i in range(len(servo_motors)):
        current_position = encs[i].position
        if current_position != last_positions[i]:
            config = s_cfgs[i]
            angle = min(max(current_position, config['min_ang']), config['max_ang'])
            servo_motor = servo_motors[i]
            enc = encs[i]
            set_servo_angle(servo_motor, angle, enc, config['min_ang'], config['max_ang'])
            labels[2 + i].text = f"Angle:{angle}"
            last_positions[i] = current_position
