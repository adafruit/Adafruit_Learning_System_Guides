import time
import audioio
import audiocore
from digitalio import DigitalInOut, Pull, Direction
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import neopixel
import board


# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Two onboard CPX buttons for FOG
buttona = DigitalInOut(board.BUTTON_A)
buttona.direction = Direction.INPUT
buttona.pull = Pull.DOWN

buttonb = DigitalInOut(board.BUTTON_B)
buttonb.direction = Direction.INPUT
buttonb.pull = Pull.DOWN


# Use the signal port for potentiometer w/switch
MORECOW = 2    # A switch on Signal #1
SWITCH = 3     # A potentiometer on Signal #2
# Add a pullup on the switch
seesaw.pin_mode(SWITCH, seesaw.INPUT_PULLUP)

# Servo angles
BELL_START = 60
BELL_END = 75
MOUTH_START = 95
MOUTH_END = 105

# Create servos list
servos = []
for ss_pin in (17, 16): #17 is labeled 1 on CRICKIT, 16 is labeled 2
    pwm = PWMOut(seesaw, ss_pin)
    pwm.frequency = 50 #must be 50 cannot change
    _servo = servo.Servo(pwm, min_pulse=400, max_pulse=2500)
    servos.append(_servo)
# Starting servo locations
servos[0].angle = BELL_START
servos[1].angle = MOUTH_START

# For the fog machine we actually use the PWM on the motor port cause it really needs 5V!
fog_off = PWMOut(seesaw, 22)
fog_off.duty_cycle = 0
fog_on = PWMOut(seesaw, 23)
fog_on.duty_cycle = 0


# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)
def play_file(wavfile):
    with open(wavfile, "rb") as file:
        wavf = audiocore.WaveFile(file)
        a.play(wavf)
        while a.playing:
            servos[1].angle = MOUTH_START
            time.sleep(.2)
            servos[1].angle = MOUTH_END
            time.sleep(.2)

# NeoPixels for EYES
pixels = neopixel.NeoPixel(board.A1, 9, brightness=0.5)
pixels[8] = (255, 255, 0)
pixels[7] = (255, 255, 0)


# Maps a number from one range to another.
def map_range(x, in_min, in_max, out_min, out_max):
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)


# Wait before starting up
time.sleep(3)
play_file("i-gotta-have-more-cowbell.wav")
# a pause between audio clips
time.sleep(1)
play_file("only-prescription-more-cowbell.wav")

while seesaw.digital_read(SWITCH):
    pass

print("Ready for playing audio")
time.sleep(1)

f = open("fear11.wav", "rb")
wav = audiocore.WaveFile(f)
a.play(wav)

while True:
    if seesaw.digital_read(SWITCH):
        break    # time to bail!
    pot = seesaw.analog_read(MORECOW)
    print(pot)
    eyecolor = (int(map_range(pot, 0, 1023, 255, 0)), int(map_range(pot, 0, 1023, 0, 255)), 0)
    pixels[8] = eyecolor
    pixels[7] = eyecolor

    if buttonb.value:
        fog_on.duty_cycle = 65535
    else:
        fog_on.duty_cycle = 0

    if buttona.value:
        fog_off.duty_cycle = 65535
    else:
        fog_off.duty_cycle = 0

    if pot < 200:  # wait for a bit before we start
        continue
    delay = map_range(pot, 200, 1023, 1.0, 0.1)
    servos[0].angle = BELL_END
    time.sleep(0.1)
    servos[0].angle = BELL_START
    time.sleep(delay)

a.stop()
f.close()

# Fog machine test
fog_off.duty_cycle = 65535
fog_on.duty_cycle = 0
time.sleep(0.1)
fog_off.duty_cycle = 0

pixels[8] = (255, 255, 0)
pixels[7] = (255, 255, 0)
time.sleep(1.5)
play_file("i-coulda-used-more-cow-bell.wav")
