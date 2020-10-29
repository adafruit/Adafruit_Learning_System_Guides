# Lucio 2020
# Feather M4 + Propmaker + amps + lots of neopixels
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
import audioio
import audiomixer
import audiomp3
import adafruit_lis3dh
import neopixel
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.helper import PixelSubset
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.color import RED, ORANGE, WHITE

ORANGE_DIM = 0x801400  # half value version
RED_DIM = 0x800000

#  ---Set Volume Max Here---
VOLUME_MULT = 0.65  # 1 = full volume, 0.1 is very quiet, 0 is muted

#  ---SWITCH/BUTTON SETUP---
mode_switch = DigitalInOut(board.D9)
mode_switch.switch_to_input(pull=Pull.UP)
mode_state = mode_switch.value
trig_button = DigitalInOut(board.A4)
trig_button.switch_to_input(pull=Pull.UP)
alt_button = DigitalInOut(board.A5)
alt_button.switch_to_input(pull=Pull.UP)

#  ---ACCELEROMETER SETUP---
# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
int1 = DigitalInOut(board.D6)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)

#  ---SPEAKER SETUP---
enable = DigitalInOut(board.D10)
enable.direction = Direction.OUTPUT
enable.value = True
# Set up speakers and mixer. Stereo files, where music has empty right channel, FX empty left
speaker = audioio.AudioOut(board.A0, right_channel=board.A1)
mixer = audiomixer.Mixer(channel_count=2, buffer_size=2304, sample_rate=22050)

#  ---NEOPIXEL SETUP---
pixel_pin = board.D5
pixel_num = 154
pixels = neopixel.NeoPixel(
    pixel_pin, pixel_num, brightness=0.6, auto_write=False, pixel_order=neopixel.GRBW
)
# ^ change pixel_order depending on RGB vs. RGBW pixels


#  ---Pixel Map---
#  this is the physical order in which the strips are plugged
pixel_stripA = PixelSubset(pixels, 0, 18)  # 18 pixel strip
pixel_stripB = PixelSubset(pixels, 18, 36)  # 18 pixel strip
pixel_jewel = PixelSubset(pixels, 36, 43)  # 7 pixel jewel
pixel_ringsAll = PixelSubset(pixels, 43, 151)  # all of the rings
#  or use rings individually:
# pixel_ringA = PixelSubset(pixels, 43, 59)  # 16 pixel ring
# pixel_ringB = PixelSubset(pixels, 59, 75)  # 16 pixel ring
# pixel_ringC = PixelSubset(pixels, 75, 91)  # 16 pixel ring
# pixel_ringD = PixelSubset(pixels, 91, 151)  # 60 pixel ring

#  ---BPM---
BPM = 128
BEAT = 60 / BPM  # quarter note beat
b16TH = BEAT / 4  # 16TH note
b64TH = BEAT / 16  # sixty-fourth

#  ---Anim Setup---
# heal color mode
# Pulse 'speed' = smoothness
pulse_rings_m0 = Pulse(pixel_ringsAll, speed=0.01, color=ORANGE, period=BEAT)
pulse_jewel_m0 = Pulse(pixel_jewel, speed=0.01, color=ORANGE, period=BEAT)
comet_stripA_m0 = Comet(
    pixel_stripA, speed=b64TH, color=ORANGE, tail_length=9, bounce=False
)
comet_stripB_m0 = Comet(
    pixel_stripB, speed=b64TH, color=ORANGE, tail_length=9, bounce=False
)

# speed color mode
pulse_rings_m1 = Pulse(pixel_ringsAll, speed=0.02, color=RED, period=BEAT / 2)
pulse_jewel_m1 = Pulse(pixel_jewel, speed=0.02, color=RED, period=BEAT / 2)
comet_stripA_m1 = Comet(
    pixel_stripA, speed=b64TH, color=RED, tail_length=9, bounce=False
)
comet_stripB_m1 = Comet(
    pixel_stripB, speed=b64TH, color=RED, tail_length=9, bounce=False
)

solid_white = Solid(pixel_ringsAll, color=WHITE)

# ---Anim Modes---
vu_strip_animations_mode0 = AnimationGroup(comet_stripA_m0, comet_stripB_m0, sync=True)
vu_strip_animations_mode1 = AnimationGroup(comet_stripA_m1, comet_stripB_m1, sync=True)

#  ---Audio Setup---
if mode_state:
    BGM = "/lucio/bgmheal.mp3"
else:
    BGM = "/lucio/bgmspeed.mp3"
sample0 = audiomp3.MP3Decoder(open(BGM, "rb"))
FX = "/lucio/shoot.mp3"
sample1 = audiomp3.MP3Decoder(open(FX, "rb"))
speaker.play(mixer)
mixer.voice[0].play(sample0, loop=True)
mixer.voice[0].level = 0.3 * VOLUME_MULT
mixer.voice[1].level = 0.7 * VOLUME_MULT


while True:
    if mode_state:  # heal mode on startup
        vu_strip_animations_mode0.animate()
        pulse_rings_m0.animate()
        pulse_jewel_m0.animate()
    else:  # speed mode on startup
        vu_strip_animations_mode1.animate()
        pulse_rings_m1.animate()
        pulse_jewel_m1.animate()

    # Change modes
    if mode_switch.value:
        if mode_state == 0:  # state has changed, toggle it
            BGM = "/lucio/bgmheal.mp3"
            sample0.file = open(BGM, "rb")
            mixer.voice[0].play(sample0, loop=True)
            vu_strip_animations_mode0.animate()
            pulse_rings_m0.animate()
            pulse_jewel_m0.animate()
            mode_state = 1
    else:
        if mode_state == 1:
            BGM = "/lucio/bgmspeed.mp3"
            sample0.file = open(BGM, "rb")
            mixer.voice[0].play(sample0, loop=True)
            vu_strip_animations_mode1.animate()
            pulse_rings_m1.animate()
            pulse_jewel_m1.animate()
            mode_state = 0

    x, _, _ = accel.acceleration  # get accelerometer values

    if not mixer.voice[1].playing:
        if not trig_button.value:  # trigger squeezed
            FX_sample = "/lucio/shoot.mp3"
            sample1.file = open(FX_sample, "rb")
            mixer.voice[1].play(sample1)
            if mode_state:
                solid_white.animate()
            else:
                solid_white.animate()

        if not alt_button.value:  # alt trigger squeezed
            FX_sample = "/lucio/alt_shoot.mp3"
            sample1.file = open(FX_sample, "rb")
            mixer.voice[1].play(sample1)
            if mode_state:
                solid_white.animate()
            else:
                solid_white.animate()

        if accel.acceleration.x > 8:  # reload
            FX_sample = "/lucio/reload.mp3"
            sample1.file = open(FX_sample, "rb")
            mixer.voice[1].play(sample1)
            if mode_state:
                solid_white.animate()
            else:
                solid_white.animate()

        if accel.acceleration.x < -8:  # Ultimate
            FX_sample = "/lucio/ultimate.mp3"
            sample1.file = open(FX_sample, "rb")
            mixer.voice[1].play(sample1)
            if mode_state:
                solid_white.animate()
            else:
                solid_white.animate()
