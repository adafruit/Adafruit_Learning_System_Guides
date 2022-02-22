# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=wrong-import-position
import time
import gc
import pulseio
from busio import I2C
import board
gc.collect()
import adafruit_irremote
gc.collect()
from adafruit_motor import motor
gc.collect()
from adafruit_seesaw.seesaw import Seesaw
gc.collect()
from adafruit_seesaw.pwmout import PWMOut
gc.collect()
import neopixel
gc.collect()
import audioio
gc.collect()
import audiocore
gc.collect()


print("Blimp!")

# Create Infrared reader
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=100, idle_state=True)
decoder = adafruit_irremote.GenericDecode()
REMOTE_FORWARD = [255, 2, 175, 80]
REMOTE_BACKWARD = [255, 2, 239, 16]
REMOTE_PAUSE = [255, 2, 127, 128]

# Create seesaw object
seesaw = Seesaw(I2C(board.SCL, board.SDA))

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0

# Neopix!@
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# audio file
a = audioio.AudioOut(board.A0)

def play_audio(wavfile):
    f = open(wavfile, "rb")
    wav = audiocore.WaveFile(f)
    a.play(wav)
    while a.playing:
        pass
    f.close()
    gc.collect()

play_audio("overview.wav")
t = time.monotonic()

while True:
    command = None   # assume no remote commands came in
    if len(pulsein) > 25:  # check in any IR data came in
        pulses = decoder.read_pulses(pulsein)
    try:
        code = decoder.decode_bits(pulses, debug=False)
        if code in (REMOTE_FORWARD, REMOTE_BACKWARD, REMOTE_PAUSE):
            # we only listen to a few different codes
            command = code
        else:
            continue
    # on any failure, lets just restart
    # pylint: disable=bare-except
    except:
        continue

    if command:
        if code == REMOTE_FORWARD:
            play_audio("fan_forward.wav")
            motor_a.throttle = 1  # full speed forward
            pixels.fill((255,0,0))
        elif code == REMOTE_BACKWARD:
            play_audio("fan_backward.wav")
            motor_a.throttle = -1  # full speed backward
            pixels.fill((0,0,255))
        elif code == REMOTE_PAUSE:
            motor_a.throttle = 0  # stop motor
            play_audio("fan_stopped.wav")
            pixels.fill((0,0,0))
        time.sleep(0.5)

    # play yayayay every 3 seconds
    if (time.monotonic() - t > 3) and motor_a.throttle != 0:
        t = time.monotonic()
        play_audio("yayyayyay.wav")
