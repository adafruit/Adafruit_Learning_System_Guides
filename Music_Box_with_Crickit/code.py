# Music Box code in CircuitPython - Dano Wall and Mike Barela
# Revised by Ladyada 2019-01-16

from adafruit_crickit import crickit
from analogio import AnalogIn
import neopixel
import audioio
import board

AUDIO_FILENAME = 'fur-elise.wav'

# Audio output
cpx_audio = audioio.AudioOut(board.A0)
audio = audioio.WaveFile(open(AUDIO_FILENAME, "rb"))

# Rotating dancer
dancer = crickit.servo_2
dancer.angle = 0
MAX_SERVO_ANGLE = 160
move_direction = 1

# neopixels!
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0, 0, 0))

# light sensor
light = AnalogIn(board.LIGHT)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))

def rainbow(value):
    for i in range(10):
        pixels[i] = wheel((value * i) & 255)


while True:
    # turn off LEDs so we can tell if its dark out!
    pixels.brightness = 0
    # read light level
    light_level = light.value
    # turn LEDs back on
    pixels.brightness = 1

    # Turn things off if light level < value, its dark
    if light_level < 2000:
        pixels.fill((0, 0, 0))
        cpx_audio.stop()
    else:
        if not cpx_audio.playing:
            # Start playing the song again
            cpx_audio.play(audio)
        # calculate servo rotation
        if dancer.angle <= 0:
            move_direction = 1
        if dancer.angle > MAX_SERVO_ANGLE:
            move_direction = -1
        # Move servo one degree forward or backward.
        rainbow(int(dancer.angle * 255/MAX_SERVO_ANGLE))
        dancer.angle += move_direction
