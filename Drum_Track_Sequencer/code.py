# SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Drum Track Sequencer
 Feather RP2040, Motor FeatherWing, stepper motor,
 four reflection sensors, USB MIDI out
"""
import asyncio
import busio
import board
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
import keypad
import usb_midi

# Tempo setup
BPM = 100  # user set value
tempo_table = {  # motor speed seems non-linear, so we'll use a lookup table
    110: 0.0004,
    100: 0.001,
    90: 0.002,
    80: 0.003,
    75: 0.004,
    65: 0.005,
    60: 0.006,
    50: 0.008
}
def get_nearest_tempo(given_bpm):
    nearest_table_item = min(tempo_table.keys(), key=lambda k: abs(k - given_bpm))
    return tempo_table[nearest_table_item]
motor_pause = get_nearest_tempo(BPM)

i2c=busio.I2C(board.SCL, board.SDA, frequency=400_000)

# Motor setup
kit = MotorKit(i2c=i2c)
motor_run=True

# Sensor setup
optical_pins = (board.D6, board.D9, board.D10, board.D12)
optical_sensors = keypad.Keys(optical_pins, value_when_pressed=False, pull=True)

# MIDI setup
midi = usb_midi.ports[1]
midi_notes = (36, 37, 38, 39)  # typical drum voice notes

def play_drum(note):
    midi_msg_on = bytearray([0x99, note, 120])  # 0x90 noteOn ch1, 0x99 noteOn ch10
    midi_msg_off = bytearray([0x89, note, 0])
    midi.write(midi_msg_on)
    midi.write(midi_msg_off)

async def check_sensors():
    while True:
        optical_sensor = optical_sensors.events.get()
        if optical_sensor:
            if optical_sensor.pressed:
                track_num = optical_sensor.key_number
                # print("tripped", track_num)
                play_drum(midi_notes[track_num])
        await asyncio.sleep(0.008)  # don't check sensors constantly or motor speed reduced

async def run_motor():
    while True:
        kit.stepper1.onestep(
                                direction=stepper.BACKWARD,
                                style=stepper.DOUBLE
        )
        await asyncio.sleep(motor_pause)  # motor speed-- smaller numbers are faster

async def main():
    motor_task = asyncio.create_task(run_motor())
    sensor_task = asyncio.create_task(check_sensors())
    await asyncio.gather(motor_task, sensor_task)

asyncio.run(main())
