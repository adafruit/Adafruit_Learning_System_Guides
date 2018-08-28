import time
from adafruit_crickit import crickit
import board
import neopixel

print("Peltier Module Demo")

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)

def show_value(time_val):
    num_pixels = int(10-time_val)
    for i in range(num_pixels):
        pixels[i] = (10*(i+1), 0, 0)
    for i in range(num_pixels, 10):
        pixels[i] = (0, 0, 0)
    pixels.show()
    return

# For signal control, we'll chat directly with seesaw
ss = crickit.seesaw
TMP36 = crickit.SIGNAL1  # TMP36 connected to signal port 1 & ground
POT = crickit.SIGNAL8    # potentiometer connected to signal port 8 & ground

peltier = crickit.dc_motor_2  # Drive the Peltier from Motor 2 Output

while True:

    voltage = ss.analog_read(TMP36) * 3.3 / 1024.0
    tempC = (voltage - 0.5) * 100.0
    tempF = (tempC * 9.0 / 5.0) + 32.0

    cool_value = ss.analog_read(POT) / 102.30  # convert 0.0 to 10.0

    # timing can be zero or can be 1 second to 10 seconds
    # between 0 and 1 is too short a time for a Peltier module
    if cool_value < 0.2:
        cool_value = 0.0
    if cool_value >= 0.2 and cool_value < 1.0:
        cool_value = 1.0

    print((tempF, cool_value))
    show_value(cool_value)

    # Peltier cannot be PWM - either off or on
    # Use potentiometer read to set seconds b
    if cool_value > 0:
        peltier.throttle = 0.0     # turn off
        time.sleep(cool_value)     # wait

    peltier.throttle = 1.0         # turn on
    time.sleep(10.0 - cool_value)  # wait
