# HalloWing Jump Scare Trap
# use PIR sensor, speaker, and servo
import time
import array
import math
import board
import displayio
import pulseio
from adafruit_motor import servo
import digitalio
import touchio
import audioio
# Setup LED and PIR pins
LED_PIN = board.D13  # Pin number for the board's built in LED.
PIR_PIN = board.SENSE   # Pin port connected to PIR sensor output wire.
# Setup digital input for PIR sensor:
pir = digitalio.DigitalInOut(PIR_PIN)
pir.direction = digitalio.Direction.INPUT
# Setup digital output for LED:
led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT
# Setup servo
# servo = pulseio.PWMOut(board.D4, frequency=50)
pwm = pulseio.PWMOut(board.D4)
servo = servo.Servo(pwm)

# Setup cap touch button
ready_button = touchio.TouchIn(board.TOUCH1)

def servo_ready():
    servo.angle = 0
def servo_release():
    servo.angle = 90

# Set servo to ready position
servo_ready()
# Function for playing wav file, releasing servo
def play_wave():
    wave_file = open("hiss01.wav", "rb")  # open a wav file
    wave = audioio.WaveFile(wave_file)
    audio.play(wave)  # play the wave file
    led.value = True
    servo_release()
    print('Motion detected!')
    while audio.playing:  # turn on LED, turn servo
        pass
    wave_file.close()  # close the wav file
# Setup audio out pin
audio = audioio.AudioOut(board.A0)

# tone player setup for status beeps
tone_volume = 0.1  # Increase this to increase the volume of the tone.
frequency_hz = 880  # Set this to the Hz of the tone you want to generate.
length = 8000 // frequency_hz
sine_wave = array.array("H", [0] * length)
for i in range(length):
    sine_wave[i] = int((1 + math.sin(math.pi * 2 * i / length)) * tone_volume * (2 ** 15 - 1))
sine_wave_sample = audioio.RawSample(sine_wave)

# Function for beeping, usage: 'beep(3)' will beep 3x
def beep(count):
    for _ in range(count):
        audio.play(sine_wave_sample, loop=True)
        time.sleep(0.1)
        audio.stop()
        time.sleep(0.05)

# Function for counting down, usage: 'countdown(5)'
def countdown(count):
    for k in range(count):
        print(count - k)
        led.value = True
        time.sleep(0.1)
        led.value = False
        time.sleep(1)

# function for blinking, usage: 'blink(5, 0.2)'
def blink(count, speed):
    for _ in range(count):
        led.value = True
        time.sleep(speed)
        led.value = False
        time.sleep(speed)

# display setup
backlight = pulseio.PWMOut(board.TFT_BACKLIGHT)
splash = displayio.Group()
board.DISPLAY.show(splash)
max_brightness = 2 ** 15
backlight.duty_cycle = 0
# Image list
images = ["trap_sprung.bmp", "reset_trap.bmp", "please_standby.bmp",
          "trap_set.bmp"]
# Function for displaying images on HalloWing TFT screen
def show_image(filename):
    image_file = open(filename, "rb")
    odb = displayio.OnDiskBitmap(image_file)
    face = displayio.Sprite(odb, pixel_shader=displayio.ColorConverter(), position=(0, 0))
    backlight.duty_cycle = 0
    splash.append(face)
    # Wait for the image to load.
    board.DISPLAY.wait_for_frame()
    backlight.duty_cycle = max_brightness

beep(1)  # startup beep
show_image(images[2])  # waiting display
print('Stabilizing')
countdown(3)
print('Ready')
blink(3, 0.2)
beep(3)  # ready beeps
triggered = False
ready = True

show_image(images[3])  # ready display

while True:
    # Check PIR sensor
    pir_value = pir.value
    # Check touch button
    ready = ready_button.value

    if pir_value and triggered is not True:
        # PIR is detecting movement!
        play_wave()
        splash.pop()
        show_image(images[0])
        print('Triggered')
        countdown(8)
        blink(3, 0.2)
        beep(1)
        print('Please reset')
        led.value = False
        triggered = True
        servo_ready()
        splash.pop()
        show_image(images[1])

    if ready:  # touch sensor has been pressed
        beep(1)
        splash.pop()
        show_image(images[2])
        countdown(8)
        print('Ready.')
        blink(3, 0.2)
        beep(3)
        splash.pop()
        show_image(images[3])
        triggered = False
