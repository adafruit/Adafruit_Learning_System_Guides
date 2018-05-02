from adafruit_circuitplayground.express import cpx
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1, auto_write=True)
pixels.fill(0)

while True:
    
    x_float, y_float, z_float = cpx.acceleration  # read acceleromter
    r, g, b = 0, 0, 0
    
    if abs(x_float) > 4.0:
        r = 255
    if abs(y_float) > 2.0:
        g = 255
    if z_float > -6.0 or z_float < -12.0:
       b = 255 
    
    pixels.fill((r,g,b))
    