"""
Power Glove BLE MIDI with Feather Sense nRF52840
Sends MIDI CC values based on finger flex sensors and accelerometer
"""
import time
import board
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import adafruit_ble_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
# from adafruit_midi.note_on import NoteOn
# from adafruit_midi.pitch_bend import PitchBend
import adafruit_lsm6ds  # accelerometer
import simpleio
from analogio import AnalogIn

i2c = board.I2C()
sense_accel = adafruit_lsm6ds.LSM6DS33(i2c)

analog_in_thumb = AnalogIn(board.A3)
analog_in_index = AnalogIn(board.A2)
analog_in_middle = AnalogIn(board.A1)
analog_in_ring = AnalogIn(board.A0)

# Pick your MIDI CC numbers here
cc_x_num = 7  # volume
cc_y_num = 70  # unassigned
cc_thumb_num = 71  # unassigned
cc_index_num = 75  # unassigned
cc_middle_num = 76  # unassigned
cc_ring_num = 77  # unassigned

midi_channel = 1  # pick your midi out channel here

# Use default HID descriptor
midi_service = adafruit_ble_midi.MIDIService()
advertisement = ProvideServicesAdvertisement(midi_service)

ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

midi = adafruit_midi.MIDI(midi_out=midi_service, out_channel=midi_channel - 1)

print("advertising")
ble.name="Power Glove MIDI"
ble.start_advertising(advertisement)

# reads an analog pin and returns value remapped to out range, e.g., 0-127
def get_flex_cc(sensor, low_in, high_in, min_out, max_out):
    flex_raw = sensor.value
    flex_cc = simpleio.map_range(flex_raw, low_in, high_in, min_out, max_out)
    flex_cc = int(flex_cc)
    return flex_cc


debug = False  # set debug mode True to test raw values, set False to run BLE MIDI

while True:
    if debug:
        accel_data = sense_accel.acceleration  # get accelerometer reading
        accel_x = accel_data[0]
        accel_y = accel_data[1]
        accel_z = accel_data[2]

        print(
            "x:{} y:{} z:{} thumb:{} index:{} middle:{} ring:{}".format(
                accel_x,
                accel_y,
                accel_x,
                analog_in_thumb.value,
                analog_in_index.value,
                analog_in_middle.value,
                analog_in_ring.value,
            )
        )
        time.sleep(0.2)

    else:
        print("Waiting for connection")
        while not ble.connected:
            pass
        print("Connected")
        while ble.connected:
            # Feather Sense accelerometer readings to CC
            accel_data = sense_accel.acceleration  # get accelerometer reading
            accel_x = accel_data[0]
            accel_y = accel_data[1]
            # accel_z = accel_data[2]
            # Remap analog readings to cc range
            cc_x = int(simpleio.map_range(accel_x, 0, 9, 127, 0))
            cc_y = int(simpleio.map_range(accel_y, 1, -9, 0, 127))

            cc_thumb = get_flex_cc(analog_in_thumb, 49000, 35000, 127, 0)
            cc_index = get_flex_cc(analog_in_index, 50000, 35000, 0, 127)
            cc_middle = get_flex_cc(analog_in_middle, 55000, 40000, 0, 127)
            cc_ring = get_flex_cc(analog_in_ring, 55000, 42000, 0, 127)
            '''
            print(
                "CC_X:{} CC_Y:{} CC_Thumb:{} CC_Index:{} CC_Middle:{} CC_Ring:{}".format(
                    cc_x, cc_y, cc_thumb, cc_index, cc_middle, cc_ring
                )
            )'''

            # send all the midi messages in a list
            midi.send(
                [
                    ControlChange(cc_x_num, cc_x),
                    ControlChange(cc_y_num, cc_y),
                    ControlChange(cc_thumb_num, cc_thumb),
                    ControlChange(cc_index_num, cc_index),
                    ControlChange(cc_middle_num, cc_middle),
                    ControlChange(cc_ring_num, cc_ring),
                ]
            )

            # If you want to send NoteOn or Pitch Bend, here are examples:
            # midi.send(NoteOn(44, 120))  # G sharp 2nd octave
            # a_pitch_bend = PitchBend(random.randint(0, 16383))
            # midi.send(a_pitch_bend)

        print("Disconnected")
        print()
        ble.start_advertising(advertisement)
