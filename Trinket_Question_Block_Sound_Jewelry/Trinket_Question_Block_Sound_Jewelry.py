import time
import board
import simpleio
import pulseio
import digitalio

# PWM is not available on Trinket D1
vibration_pin = board.D1    # vibration switch is connected
speaker_pin = board.D2      # PWM speaker
pwm_leds = board.D4         # PWM "fading" LEDs

# initialize PWM for LEDs
pwm = pulseio.PWMOut(pwm_leds, frequency=256, duty_cycle=50)
led_fade_delay = .001       # delay in seconds makes color fade visible
led_fade_step = 1024        # fade amount

# initialize vibration sensor
vpin = digitalio.DigitalInOut(vibration_pin)
vpin.direction = digitalio.Direction.INPUT
vpin.pull = digitalio.Pull.UP

def led_fade(brightness):
    pwm.duty_cycle = brightness
    brightness_start = brightness

    while brightness >= (brightness_start / 2):
        brightness -= led_fade_step
        pwm.duty_cycle = brightness
        time.sleep(led_fade_delay)

while True:
    # wait for vibration sensor detect (reverse logic)
    # play Super Mario Bros. coin sound
    # fade LEDs
    if not vpin.value:
        led_fade((2 ** 16) - 1)                 # full brightness
        simpleio.tone(speaker_pin, 988, 0.083)  # tone1 - B5
        led_fade(2 ** 15)                       # half brightness
        simpleio.tone(speaker_pin, 1319, 0.83)  # tone2 - E6
        led_fade(2 ** 14)                       # quarter brightness
    pwm.duty_cycle = 0                          # turn off LEDs
