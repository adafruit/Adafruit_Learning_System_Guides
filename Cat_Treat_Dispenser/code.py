import time
import board
import audioio
from adafruit_crickit import crickit

print("Cat Feeder")

feed_servo = crickit.servo_1

# audio output
cpx_audio = audioio.AudioOut(board.A0)
f = open("activate.wav", "rb")
wav = audioio.WaveFile(f)

while True:
    if crickit.touch_1.value:
        time.sleep(0.1)
        cpx_audio.play(wav)
        feed_servo.angle = 180
        time.sleep(0.2)
        feed_servo.angle = 0
        time.sleep(0.1)
