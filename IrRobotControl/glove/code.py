# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import busio
import board
import pulseio
import adafruit_irremote
import adafruit_lis3dh

# Control debug output: it takes time so don't unless you're debugging
DEBUG_LOG = False

# Control codes
STOP = 0x01
ROTATE_LEFT = 0x02
ROTATE_RIGHT = 0x03
FORWARD = 0x04
FORWARD_LEFT = 0x05
FORWARD_RIGHT = 0x06
REVERSE = 0x07
REVERSE_LEFT = 0x08
REVERSE_RIGHT = 0x09

TRANSMIT_DELAY = 0.1

# Setup accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
sensor = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)

# Create a 'pulseio' output, to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.IR_TX, frequency=38000, duty_cycle=2 ** 15)

# Create an encoder that will take numbers and turn them into IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9000, 4500],
                                            one=[560, 1700],
                                            zero=[560, 560],
                                            trail=0)

def log(s):
    """Optionally output some text.
    :param string s: test to output
    """
    if DEBUG_LOG:
        print(s)


while True:
    x, y, z = sensor.acceleration
    log("{0: 0.3f} {1: 0.3f} {2: 0.3f}".format(x, y, z))
    if z < -5.0 and abs(y) < 3.0:         # palm down
        if x < -5.0:                      # tipped counterclockwise
            log("ROTATE_LEFT")
            encoder.transmit(pulseout, [ROTATE_LEFT] * 4)
        elif x > 5.0:                     # tipped clockwise
            log("ROTATE_RIGHT")
            encoder.transmit(pulseout, [ROTATE_RIGHT] * 4)
        else:                             # level
            log("STOP")
            encoder.transmit(pulseout, [STOP] * 4)
    elif y > 5.0:                         # palm facing away
        if x < -5.0:                      # tipped counterclockwise
            log("FORWARD_LEFT")
            encoder.transmit(pulseout, [FORWARD_LEFT] * 4)
        elif x > 5.0:                     # tipped clockwise
            log("FORWARD_RIGHT")
            encoder.transmit(pulseout, [FORWARD_RIGHT] * 4)
        else:                             # straight up
            log("FORWARD")
            encoder.transmit(pulseout, [FORWARD] * 4)
    elif y < -5.0:                        # palm facing toward (hand down)
        if x < -5.0:                      # tipped counterclockwise
            log("REVERSE_RIGHT")
            encoder.transmit(pulseout, [REVERSE_RIGHT] * 4)
        elif x > 5.0:                     # tipped clockwise
            log("REVERSE_LEFT")
            encoder.transmit(pulseout, [REVERSE_LEFT] * 4)
        else:                             #straight down
            log("REVERSE")
            encoder.transmit(pulseout, [REVERSE] * 4)

    time.sleep(TRANSMIT_DELAY)
