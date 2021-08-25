import time
import board
from analogio import AnalogIn
from adafruit_crickit import crickit
import neopixel

print("Peltier Module Demo")

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)

def show_value(time_val):         # Show time on NeoPixels on CPX
    num_pixels = int(10-time_val)
    for i in range(num_pixels):
        pixels[i] = (10*(i+1), 0, 0)
    for i in range(num_pixels, 10):
        pixels[i] = (0, 0, 0)
    pixels.show()
    return

TMP36 = AnalogIn(board.A3)  # TMP36 connected to A3, power & ground
POT = AnalogIn(board.A7)    # potentiometer connected to A7, power & ground

peltier = crickit.dc_motor_2  # Drive the Peltier from Motor 2 Output

while True:                   # Loop forever

    voltage = TMP36.value * 3.3 / 65536.0
    tempC = (voltage - 0.5) * 100.0
    tempF = (tempC * 9.0 / 5.0) + 32.0

    cool_value = POT.value / 6553.6  # convert 0.0 to 10.0

    # timing can be zero or can be 1 second to 10 seconds
    # between 0 and 1 is too short a time for a Peltier module
    if cool_value < 0.2:
        cool_value = 0.0
    if cool_value >= 0.2 and cool_value < 1.0:
        cool_value = 1.0

    print((tempF, cool_value))  # Show in REPL
    show_value(cool_value)      # Show on NeoPixels

    # Peltier cannot be PWM - either off or on
    # Use potentiometer read to set seconds b
    if cool_value > 0:
        peltier.throttle = 0.0     # turn off
        time.sleep(cool_value)     # wait

    peltier.throttle = 1.0         # turn on
    time.sleep(10.0 - cool_value)  # wait
