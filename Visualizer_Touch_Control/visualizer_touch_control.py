import time
import board
import busio
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import usb_hid
import adafruit_mpr121

# Create I2C bus.
i2c = busio.I2C(board.SCL, board.SDA)
# Create MPR121 object.
mpr121 = adafruit_mpr121.MPR121(i2c)
# Note you can optionally change the address of the device:
# mpr121 = adafruit_mpr121.MPR121(i2c, address=0x91)
kbd = Keyboard(usb_hid.devices)
keylist = [
    Keycode.RIGHT_ARROW,
    Keycode.ONE,
    Keycode.TWO,
    Keycode.THREE,
    Keycode.FOUR,
    Keycode.W,
    Keycode.A,
    Keycode.S,
    Keycode.D,
    Keycode.B,
    Keycode.I,
    Keycode.H,
]

# Loop forever testing each input and sending keystrokes when they're touched.
while True:
    # Loop through all 12 inputs (0-11).
    for i in range(12):
        # Call is_touched and pass it then number of the input.  If it's touched
        # it will return True, otherwise it will return False.
        if mpr121[i].value:
            # print("Input {} touched!".format(i))
            kbd.send(keylist[i])
    time.sleep(0.15)  # Small delay to keep from spamming output messages.
