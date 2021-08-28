import time
from adafruit_circuitplayground.express import cpx
import adafruit_irremote
import pulseio
import board

# Create a 'pulseio' output, to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.IR_TX, frequency=38000, duty_cycle=2 ** 15)
# Create an encoder that will take numbers and turn them into NEC IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9500, 4500], one=[550, 550],
                                            zero=[550, 1700], trail=0)

while True:
    if cpx.button_a:
        print("Button A pressed! \n")
        cpx.red_led = True
        encoder.transmit(pulseout, [255, 2, 255, 0])
        cpx.red_led = False
        # wait so the receiver can get the full message
        time.sleep(0.2)
    if cpx.button_b:
        print("Button B pressed! \n")
        cpx.red_led = True
        encoder.transmit(pulseout, [255, 2, 191, 64])
        cpx.red_led = False
        time.sleep(0.2)
