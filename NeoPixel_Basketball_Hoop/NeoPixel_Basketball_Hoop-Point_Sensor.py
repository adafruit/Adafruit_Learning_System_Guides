import time
import board
import neopixel
import adafruit_irremote
import pulseio

pixpin = board.D1
ir_led = board.D0
ir_sensor = board.D2
basket_check_seconds = 0.1
numpix = 60

# NeoPixel LED
strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=False)

# IR LED output for 38kHz PWM
pwm = pulseio.PWMOut(ir_led, frequency=38000)

# IR Sensor input to detect basketball
pulses = pulseio.PulseIn(ir_sensor, maxlen=200, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if pos < 85:
        return (int(pos * 3), int(255 - (pos * 3)), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))

    pos -= 170
    return (0, int(pos * 3), int(255 - pos * 3))

def timed_rainbow_cycle(seconds, wait):
    # Get the starting time in seconds.
    start = time.monotonic()
    # Use a counter to increment the current color position.
    j = 0

    # Loop until it's time to stop (desired number of milliseconds have elapsed).
    while (time.monotonic() - start) < seconds:
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = wheel(idx & 255)
        strip.show()
        # Wait the desired number of milliseconds.
        time.sleep(wait)
        j += 1

    # Turn all the pixels off after the animation is done.
    for i in range(len(strip)):
        strip[i] = (0,0,0)
    strip.show()

def pulse_ir():
    # enable IR LED
    pwm.duty_cycle = (2 ** 16) - 1

def is_ball_in_hoop():
    # Check if the IR sensor picked up the pulse
    pulse = decoder.read_pulses(pulses)
    ir_detect = (len(pulse))

    if ir_detect == 0:
        return False    # Sensor can see LED, return false.
    return True         # Sensor can't see LED, return true.


while True:
    pulse_ir()
    is_ball_in_hoop()

    if is_ball_in_hoop():
        timed_rainbow_cycle(2, 0.01)
    time.sleep(basket_check_seconds)
