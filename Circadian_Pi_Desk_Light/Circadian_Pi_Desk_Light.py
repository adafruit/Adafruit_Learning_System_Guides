import board
import neopixel
import sys
import datetime

pi_pin = board.D18
numpix = 144
brightness = 1.0
pixels = neopixel.NeoPixel(pi_pin, numpix, brightness=brightness) # Raspberry Pi wiring!

# valid argument check and color assignment
# morning == blue
# night == red
# off == all LEDs off
if len(sys.argv) == 2:
    if sys.argv[1] == "morning" :
        color = (0, 0, 255)
    elif sys.argv[1] == "night" :
        color = (255, 0, 0)
    elif sys.argv[1] == "day" :
        color = (255, 255, 255)
    elif sys.argv[1] == "off" :
        color = (0, 0, 0)

    pixels.fill(color)

else:
    print("valid arguments are morning, night or off")
