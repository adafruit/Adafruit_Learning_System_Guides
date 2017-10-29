import board
import neopixel
import time
from analogio import AnalogIn

try:
        import urandom as random
except ImportError:
        import random

wick_pin = board.D0         # The data-in pin of the NeoPixel
unconnected_pin = board.A0  # Any unconnected pin, to try to generate a random seed

# The LED can be in only one of these states at any given time
bright = 0
up = 1
down = 2
dim = 3
bright_hold = 4
dim_hold = 5

index_bottom_percent = 10   # Percent chance the LED will suddenly fall to minimum brightness
index_bottom = 128          # Absolute minimum red value (green value is a function of red's value)
index_min = 192             # Minimum red value during "normal" flickering (not a dramatic change)
index_max = 255             # Maximum red value

# Decreasing brightness will take place over a number of milliseconds in this range
down_min_msecs = 20 
down_max_msecs = 250 

# Increasing brightness will take place over a number of milliseconds in this range
up_min_msecs = 20 
up_max_msecs = 250  

# Percent chance the color will hold unchanged after brightening
bright_hold_percent = 20 

# When holding after brightening, hold for a number of milliseconds in this range
bright_hold_min_msecs = 0
bright_hold_max_msecs = 100 

# Percent chance the color will hold unchanged after dimming
dim_hold_percent = 5

# When holding after dimming, hold for a number of milliseconds in this range
dim_hold_min_msecs = 0
dim_hold_max_msecs = 50 

numpix = 1         # Number of NeoPixels
pixpin = board.D0  # Pin where NeoPixels are connected
strip  = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True) # initialize strip

# Random number generator is seeded from an unused 'floating'
# analog input - this helps ensure the random color choices
# aren't always the same order.
pin = AnalogIn(unconnected_pin)
random.seed(pin.value)
pin.deinit()

index_start = 255
index_start = 255
index_end = 255
state = bright

def set_color(index):
    index = max(min(index,index_max), index_bottom)
    if ( index >= index_min ):
        strip[0] = [index, int ( (index * 3) / 8 ), 0]
    elif ( index < index_min ):
        strip[0] = [index, int ( (index * 3.25) / 8 ) , 0]

set_color(255)

while True:

    current_time = time.monotonic()

    # BRIGHT
    if ( state == bright ):
        flicker_msecs = random.randint(0, down_max_msecs - down_min_msecs) + down_min_msecs
        flicker_start = current_time
        index_start = index_end

        if (( index_start > index_bottom ) and ( random.randint(0, 100) < index_bottom_percent)):
            index_end = random.randint(0, index_start - index_bottom) + index_bottom
        else:
            index_end = random.randint(0, index_start - index_min) + index_min 

        state = down

    # DIM
    elif ( state == dim ):
        flicker_msecs = random.randint(0, up_max_msecs - up_min_msecs) + up_min_msecs
        flicker_start = current_time
        index_start = index_end
        index_end = random.randint(0, (index_max - index_start) ) + index_min
        state = down

    # DIM_HOLD
    elif ( state == dim_hold ):
        if (current_time >= ( flicker_start + ( flicker_msecs / 1000) ) ):  # dividing flicker_msecs by 1000 to convert to milliseconds
            if ( state == bright_hold ):
                state = bright
            else:
                state = dim

    # DOWN
    elif ( state == down ):
      if (current_time < (flicker_start + ( flicker_msecs / 1000 ) )):  # dividing flicker_msecs by 1000 to convert to milliseconds
        set_color(index_start + int ( ((index_end - index_start) * (((current_time - flicker_start) * 1.0) / flicker_msecs))) )
      else:
        set_color(index_end)

        if (state == down):
          if (random.randint(0,100) < dim_hold_percent):
            flicker_start = current_time
            flicker_msecs = random.randint(0, dim_hold_max_msecs - dim_hold_min_msecs) + dim_hold_min_msecs
            state = dim_hold
          else:
            state = dim
        else:
          if (random.randint(0,100) < bright_hold_percent):
            flicker_start = current_time
            flicker_msecs = random.randint(0, bright_hold_max_msecs - bright_hold_min_msecs) + bright_hold_min_msecs
            state = bright_hold
          else:
            state = bright
