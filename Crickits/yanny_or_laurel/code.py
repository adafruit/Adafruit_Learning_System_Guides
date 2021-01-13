# CircuitPython 3.0 CRICKIT demo
import time
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import audioio
import audiocore
import microcontroller
import board

i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

print("Yanny or Laurel data logging!")

LOOKATPERSON = 90
LOOKLEFT = 60
LOOKRIGHT = 120

#################### 1 Servo
pwm = PWMOut(ss, 17)
pwm.frequency = 50
myservo = servo.Servo(pwm)
myservo.angle = LOOKATPERSON # introduce yourself

#################### 2 buttons w/2 LEDs
BUTTON_1 = 2
BUTTON_2 = 3
LED_1    = 8
LED_2    = 9

# Two buttons are pullups, connect to ground to activate
ss.pin_mode(BUTTON_1, ss.INPUT_PULLUP)
ss.pin_mode(BUTTON_2, ss.INPUT_PULLUP)
# Two LEDs are outputs, on by default
ss.pin_mode(LED_1, ss.OUTPUT)
ss.pin_mode(LED_2, ss.OUTPUT)
ss.digital_write(LED_1, True)
ss.digital_write(LED_2, True)

#################### log files
logfile = "/log.csv"
# pylint: disable=pointless-statement
# check that we could append if wanted to
try:
    fp = open(logfile, "a")
    fp.close
# pylint: disable=bare-except
except:
    print("File system not writable, halting")
    while True:
        pass

#################### Audio files
wavfile = "yanny.wav"
f = open(wavfile, "rb")
wav = audiocore.WaveFile(f)
a = audioio.AudioOut(board.A0)
a.play(wav)
t = time.monotonic()

# Wait
while time.monotonic() - t < 7.5:
    pass

while time.monotonic() - t < 9.5:
    myservo.angle = LOOKLEFT
    ss.digital_write(LED_1, True)
    ss.digital_write(LED_2, False)
    time.sleep(0.5)
    myservo.angle = LOOKRIGHT
    ss.digital_write(LED_1, False)
    ss.digital_write(LED_2, True)
    time.sleep(0.5)

myservo.angle = LOOKATPERSON

# reset LEDs
ss.digital_write(LED_1, False)
ss.digital_write(LED_2, False)

selection = None
# wait until
while not selection:
    if not ss.digital_read(BUTTON_1):
        selection = "Yanny"
        ss.digital_write(LED_1, True)
        myservo.angle = LOOKLEFT
        break
    if not ss.digital_read(BUTTON_2):
        selection = "Laurel"
        ss.digital_write(LED_2, True)
        myservo.angle = LOOKRIGHT
        break
    # if we havent selected, wait until they do!
    if a.playing and time.monotonic() - t > 15.5:
        a.pause()

# now we have a selection!
with open(logfile, "a") as fp:
    print("Writing!"+selection+", 1\n")
    fp.write(selection+", 1\n")
    fp.flush()
print("Written")

# OK play the rest of the music
a.resume()
while a.playing:
    pass

ss.digital_write(LED_1, False)
ss.digital_write(LED_2, False)

microcontroller.reset()
