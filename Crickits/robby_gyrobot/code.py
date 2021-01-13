import time
import gc
from digitalio import DigitalInOut, Direction, Pull
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
import touchio
import audioio
import audiocore
import neopixel
import board

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0,0,0))

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# switch
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# We need some extra captouches
touch2 = touchio.TouchIn(board.A2)
touch3 = touchio.TouchIn(board.A3)

# LED for debugging
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Create drive (PWM) object
INFRARED_LED_SS = 13
my_drive = PWMOut(seesaw, INFRARED_LED_SS)    # Drive 1 is on s.s. pin 13
my_drive.frequency = 1000        # Our default frequency is 1KHz

CAPTOUCH_THRESH = 850

# Commands, each 8 bit command is preceded by the 5 bit Init sequence
Init = [0, 0, 0, 1, 0]            # This must precede any command
Calibrate = [1, 0, 1, 0, 1, 0, 1, 1]  # the initial calibration
Up = [1, 0, 1, 1, 1, 0, 1, 1]     # Move arms/body down
Down = [1, 1, 1, 1, 1, 0, 1, 1]   # Move arms/body up
Left = [1, 0, 1, 1, 1, 0, 1, 0]   # Twist body left
Right = [1, 1, 1, 0, 1, 0, 1, 0]  # Twist body right
Close = [1, 0, 1, 1, 1, 1, 1, 0]  # Close arms
Open = [1, 1, 1, 0, 1, 1, 1, 0]   # Open arms
Test = [1, 1, 1, 0, 1, 0, 1, 1]   # Turns R.O.B. head LED on

print("R.O.B. Start")


def IR_Command(cmd):
    print("Sending ", cmd)
    gc.collect()                     # collect memory now, timing specific!
    # Output initialization and then command cmd
    for val in Init+cmd:             # For each value in initial+command
        if val:                      # if it's a one, flash the IR LED
            seesaw.analog_write(INFRARED_LED_SS, 65535)  # on
            seesaw.analog_write(INFRARED_LED_SS, 0)      # off 2ms later
        time.sleep(0.013)       # 17 ms total
    # pylint: disable=useless-else-on-loop
    else:
        time.sleep(0.015)       # 17 ms total

a = audioio.AudioOut(board.A0)
startfile = "startup.wav"
loopfile = "loop.wav"
with open(startfile, "rb") as f:
    wav = audiocore.WaveFile(f)
    a.play(wav)
    for _ in range(3):
        IR_Command(Calibrate)
        time.sleep(0.5)
    while a.playing:
        IR_Command(Open)
        time.sleep(1)
        IR_Command(Close)
        time.sleep(1)
f = open(loopfile, "rb")
wav = audiocore.WaveFile(f)
a.play(wav, loop=True)

while True:                          # Main Loop poll switches, do commands
    led.value = switch.value         # easily tell if we're running
    if not switch.value:
        continue

    #touch_vals = (touch2.raw_value, touch3.raw_value, seesaw.touch_read(0), seesaw.touch_read(1),
    #              seesaw.touch_read(2), seesaw.touch_read(3))
    #print(touch_vals)

    if touch2.raw_value > 3000:
        print("Open jaws")
        pixels.fill((50,50,0))
        IR_Command(Open)             # Button A opens arms

    elif touch3.raw_value > 3000:
        print("Close jaws")
        pixels.fill((0,50,0))
        IR_Command(Close)            # Button B closes arms

    elif seesaw.touch_read(0) > CAPTOUCH_THRESH:
        print("Up")
        pixels.fill((50,0,50))
        IR_Command(Up)

    elif seesaw.touch_read(1) > CAPTOUCH_THRESH:
        print("Down")
        pixels.fill((50,50,50))
        IR_Command(Down)

    elif seesaw.touch_read(2) > CAPTOUCH_THRESH:
        print("Left")
        pixels.fill((50,0,0))
        IR_Command(Left)

    elif seesaw.touch_read(3) > CAPTOUCH_THRESH:
        print("Right")
        pixels.fill((0,0,50))
        IR_Command(Right)

    time.sleep(0.1)
    pixels.fill((0,0,0))
