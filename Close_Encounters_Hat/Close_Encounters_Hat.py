# Close Encounters Hat with 10 NeoPixels
# ported from Leslie Birch's Arduino to CircuitPython
#
# Photocell voltage divider center wire to GPIO #2 (analog 1)
# and output tone to GPIO #0 (digital 0)

import board
import pulseio
import analogio
import time
import neopixel

# Initialize input/output pins
photocell_pin = board.A1# cds photocell connected to this ANALOG pin
speaker_pin = board.D0      # speaker is connected to this DIGITAL pin
pixpin = board.D1           # pin where NeoPixels are connected
scale = 0.03                # change this to adjust tone scale
numpix = 10                 # number of neopixels`
darkness_min = (2**16 / 2)  # more dark than light > 32k out of 64k

# this section is Close Encounters Sounds
toned = 294
tonee = 330
tonec = 262
toneC = 130
toneg = 392

photocell = analogio.AnalogIn(photocell_pin)
pwm       = pulseio.PWMOut(speaker_pin, variable_frequency=True, duty_cycle=0)
strip  = neopixel.NeoPixel(pixpin, numpix, brightness=.4) 

# Read photocell analog pin and convert voltage to frequency
def beep(tone_freq):
    pwm.frequency  = tone_freq
    pwm.duty_cycle = 32767  # 50% duty cycle
    time.sleep(1)           # Play for 1 second
    pwm.duty_cycle = 0      # Stop playing

def alien(): 
    strip[8] = (255, 255, 0)    # yellow front
    strip[3] = (255, 255, 0)    # yellow back
    beep(toned) 

    time.sleep(.025)

    strip[8] = (0, 0, 0)        # clear front
    strip[3] = (0, 0, 0)        # clear back

    time.sleep(.025)

    strip[7] = (255, 0, 255)    # pink front
    strip[2] = (255, 0, 255)    # pink back
    beep(tonee)

    time.sleep(.025)

    strip[7] = (0, 0, 0)        # clear front
    strip[2] = (0, 0, 0)        # clear back

    time.sleep(.025)

    strip[4] = (128, 255, 0)    # green front
    strip[9] = (128, 255, 0)    # green back
    beep(tonec)

    time.sleep(.025)

    strip[4] = (0, 0, 0)        # clear front
    strip[9] = (0, 0, 0)        # clear back

    time.sleep(.025)

    strip[5] = (0, 0, 255)      # blue front
    strip[0] = (0, 0, 255)      # blue back
    beep(toneC)

    time.sleep(.075)

    strip[5] = (0, 0, 0)        # clear front
    strip[0] = (0, 0, 0)        # clear back

    time.sleep(.1)

    strip[6] = (255, 0, 0)      # red front
    strip[1] = (255, 0, 0)      # red back
    beep(toneg)

    time.sleep(.1)

    strip[6] = (0, 0, 0)        # clear front
    strip[1] = (0, 0, 0)        # clear back

    time.sleep(.1)

# Loop forever...
while True:  

    # turn lights and audio on when dark 
    # (less than 50% light on analog pin)
    if ( photocell.value > darkness_min ):    
        alien()     # close Encounters Loop
