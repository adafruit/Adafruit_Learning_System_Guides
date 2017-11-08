import board
import neopixel
import time
from analogio import AnalogIn
import array

led_pin     = board.D0      # NeoPixel LED strand is connected to GPIO #0 / D0
n_pixels    = 12            # Number of pixels you are using
dc_offset   = 0             # DC offset in mic signal - if unusure, leave 0
noise       = 100           # Noise/hum/interference in mic signal
samples     = 60            # Length of buffer for dynamic level adjustment
top         = n_pixels + 1  # Allow dot to go slightly off scale

peak        = 0             # Used for falling dot
dotcount    = 0             # Frame counter for delaying dot-falling speed
volcount    = 0             # Frame counter for storing past volume data

lvl         = 10            # Current "dampened" audio level
minlvlavg   = 0             # For dynamic adjustment of graph low & high
maxlvlavg   = 512

# Collection of prior volume samples
vol = array.array('H', [0]*samples)    

mic_pin = AnalogIn(board.A1)

strip = neopixel.NeoPixel(led_pin, n_pixels, brightness=.1, auto_write=True)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if (pos < 85):
        return (int(pos * 3), int(255 - (pos*3)), 0)
    elif (pos < 170):
        pos -= 85
        return (int(255 - pos*3), 0, int(pos*3))
    else:
        pos -= 170
        return (0, int(pos*3), int(255 - pos*3))

def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))

while True:
    n = int ( ( mic_pin.value / 65536 ) * 1000 )    # 10-bit ADC format
    n = abs(n - 512 - dc_offset)                    # Center on zero                   

    if ( n >= noise ):                              # Remove noise/hum
        n = n - noise       

    lvl = int ( ( (lvl * 7) + n ) / 8 )             # "Dampened" reading (else looks twitchy) - divide by 8 (2^3)

    # Calculate bar height based on dynamic min/max levels (fixed point):
    height = top * (lvl - minlvlavg) / (maxlvlavg - minlvlavg)

    # Clip output
    if(height < 0):       
        height = 0              
    elif (height > top): 
        height = top

    # Keep 'peak' dot at top
    if(height > peak):
        peak = height         

    # Color pixels based on rainbow gradient
    for i in range(0, len(strip)):
        if (i >= height):
            strip[i] = [0,0,0]
        else:
            strip[i] = wheel(remapRange(i, 0, (n_pixels - 1), 30, 150))

    # Save sample for dynamic leveling
    vol[volcount] = n   

    # Advance/rollover sample counter                      
    if (++volcount >= samples):
        volcount = 0    

    # Get volume range of prior frames
    minlvl = vol[0]
    maxlvl = vol[0]

    for i in range(1, len(vol)):
        if(vol[i] < minlvl):      
            minlvl = vol[i]
        elif (vol[i] > maxlvl):
            maxlvl = vol[i]

    # minlvl and maxlvl indicate the volume range over prior frames, used
    # for vertically scaling the output graph (so it looks interesting
    # regardless of volume level).  If they're too close together though
    # (e.g. at very low volume levels) the graph becomes super coarse
    # and 'jumpy'...so keep some minimum distance between them (this
    # also lets the graph go to zero when no sound is playing):
    if( (maxlvl - minlvl) < top ):
        maxlvl = minlvl + top

    minlvlavg = ( minlvlavg * 63 + minlvl ) >> 6 # Dampen min/max levels - divide by 64 (2^6)
    maxlvlavg = ( maxlvlavg * 63 + maxlvl ) >> 6 # fake rolling average - divide by 64 (2^6)
 
    print(n)

