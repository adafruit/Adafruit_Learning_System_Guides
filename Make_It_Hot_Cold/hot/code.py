import time
import board
from analogio import AnalogIn
from adafruit_crickit import crickit
import neopixel

print("Heating Pad Demo")

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)

def show_value(heat_val):         # Show throttle on NeoPixels on CPX
    num_pixels = int(10 * (heat_val + 0.002))
    for i in range(num_pixels):
        pixels[i] = (10*(i+1), 0, 0)
    for i in range(num_pixels, 10):
        pixels[i] = (0, 0, 0)
    pixels.show()
    return

TMP36 = AnalogIn(board.A3)  # TMP36 connected to A3, power & ground
POT = AnalogIn(board.A7)    # potentiometer connected to A7, power & ground

heating_pad = crickit.dc_motor_2  # Set the motor object to heating pad

while True:   # Loop Forever

    voltage = TMP36.value * 3.3 / 65536.0  # Read temp sensor, get voltage
    tempC = (voltage - 0.5) * 100.0        # Calculate Celsius
    tempF = (tempC * 9.0 / 5.0) + 32.0     # Calculate Fahrenheit

    heat_value = POT.value / 65536.0   # Value (0.0 to 1.0) to drive pad

    print((tempF, heat_value))         # Display temperature and drive
    show_value(heat_value)

    heating_pad.throttle = heat_value  # set Motor throttle value to heat_value

    time.sleep(0.25)                   # Wait a bit before checking all again
