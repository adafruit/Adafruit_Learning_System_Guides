import time
import board
import pulseio
import adafruit_irremote
import neopixel

# Configure treasure information
TREASURE_ID = 1
TRANSMIT_DELAY = 15

# Create NeoPixel object to indicate status
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Create a 'pulseio' output, to send infrared signals on the IR transmitter @ 38KHz
pwm = pulseio.PWMOut(board.IR_TX, frequency=38000, duty_cycle=2 ** 15)
pulseout = pulseio.PulseOut(pwm)

# Create an encoder that will take numbers and turn them into IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9500, 4500],
                                            one=[550, 550],
                                            zero=[550, 1700],
                                            trail=0)

while True:
    pixels.fill(0xFF0000)
    encoder.transmit(pulseout, [TREASURE_ID]*4)
    time.sleep(0.25)
    pixels.fill(0)
    time.sleep(TRANSMIT_DELAY)
