import board
import pulseio
import adafruit_irremote
from adafruit_crickit import crickit

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

left_wheel = crickit.dc_motor_1
right_wheel = crickit.dc_motor_2


def log(s):
    """Optionally output some text.
    :param string s: test to output
    """
    if DEBUG_LOG:
        print(s)


# These allow easy correction for motor speed variation.
# Factors are determined by observation and fiddling.
# Start with both having a factor of 1.0 (i.e. none) and
# adjust until the bot goes more or less straight
def set_right(speed):
    right_wheel.throttle = speed * 0.9

def set_left(speed):
    left_wheel.throttle = speed


# Uncomment this to find the above factors
# set_right(1.0)
# set_left(1.0)
# while True:
#     pass


# Create a 'pulseio' input, to listen to infrared signals on the IR receiver
pulsein = pulseio.PulseIn(board.IR_RX, maxlen=120, idle_state=True)

# Create a decoder that will take pulses and turn them into numbers
decoder = adafruit_irremote.GenericDecode()

while True:
    # Listen for incoming IR pulses
    pulses = decoder.read_pulses(pulsein)

    # Try and decode them
    try:
        # Attempt to convert received pulses into numbers
        received_code = decoder.decode_bits(pulses)
    except adafruit_irremote.IRNECRepeatException:
        # We got an unusual short code, probably a 'repeat' signal
        log("NEC repeat!")
        continue
    except adafruit_irremote.IRDecodeException as e:
        # Something got distorted or maybe its not an NEC-type remote?
        log("Failed to decode: {}".format(e.args))
        continue


    if received_code == [STOP] * 4:
        log("STOP")
        set_left(0.0)
        set_right(0.0)
    elif received_code == [ROTATE_LEFT] * 4:
        log("ROTATE_LEFT")
        set_left(-0.25)
        set_right(0.25)
    elif received_code == [ROTATE_RIGHT] * 4:
        log("ROTATE_RIGHT")
        set_left(0.25)
        set_right(-0.25)
    elif received_code == [FORWARD] * 4:
        log("FORWARD")
        set_left(0.5)
        set_right(0.5)
    elif received_code == [FORWARD_LEFT] * 4:
        log("FORWARD_LEFT")
        set_left(0.0)
        set_right(0.5)
    elif received_code == [FORWARD_RIGHT] * 4:
        log("FORWARD_RIGHT")
        set_left(0.5)
        set_right(0.0)
    elif received_code == [REVERSE] * 4:
        log("REVERSE")
        set_left(-0.5)
        set_right(-0.5)
    elif received_code == [REVERSE_LEFT] * 4:
        log("REVERSE_LEFT")
        set_left(-0.25)
        set_right(-0.5)
    elif received_code == [REVERSE_RIGHT] * 4:
        log("REVERSE_RIGHT")
        set_left(-0.5)
        set_right(-0.25)
    else:
        log("UNKNOWN")
