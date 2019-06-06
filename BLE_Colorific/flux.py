# Smart Bulb Flux Bulb Control With Bluez
# Author: Tony DiCola
# Author: (Flux Bulb modifications) Jeremy Plichta
#
# This script will cycle a Flux Bulb Bluetooth Low Energy light bulb
# through a rainbow of different hues.
#
# Dependencies:
# - You must install the pexpect library, typically with 'sudo pip install pexpect'.
# - You must have bluez installed and gatttool in your path (copy it from the
#   attrib directory after building bluez into the /usr/bin/ location).
#
# License: Released under an MIT license: http://opensource.org/licenses/MIT
import colorsys
import math
import sys
import time

import pexpect


# Configuration values.
HUE_RANGE  = (0.0, 1.0)  # Tuple with the minimum and maximum hue values for a 
                         # cycle. Stick with 0 to 1 to cover all hues.
SATURATION = 1.0         # Color saturation for hues (1 is full color).
VALUE      = 1.0         # Color value for hues (1 is full value).
CYCLE_SEC  = 5.0         # Amount of time for a full cycle of hues to complete.
SLEEP_SEC  = 0.01        # Amount of time to sleep between loop iterations.


# Get bulb address from command parameters.
if len(sys.argv) != 2:
    print 'Error must specify bulb address as parameter!'
    print 'Usage: sudo python colorific.py <bulb address>'
    print 'Example: sudo python colorific.py 5C:31:3E:F2:16:13'
    sys.exit(1)
bulb = sys.argv[1]

# Run gatttool interactively.
gatt = pexpect.spawn('gatttool -I')

# Connect to the device.
gatt.sendline('connect {0}'.format(bulb))
gatt.expect('Connection successful')

# Setup range of hue value and start at minimum hue.
hue_min, hue_max = HUE_RANGE
hue = hue_min

# Enter main loop.
print 'Press Ctrl-C to quit.'
last = time.time()
while True:
    # Get amount of time elapsed since last update, then compute hue delta.
    now = time.time()
    hue_delta = (now-last)/CYCLE_SEC*(hue_max-hue_min)
    hue += hue_delta
    # If hue exceeds the maximum wrap back around to start from the minimum.
    if hue > hue_max:
        hue = hue_min+math.modf(hue)[0]
    # Compute 24-bit RGB color based on HSV values.
    r, g, b = map(lambda x: int(x*255.0), colorsys.hsv_to_rgb(hue, SATURATION, 
                                                              VALUE))
    # Set light color by sending color change packet over BLE.
    # 56RRGGBB00f0aa
    line = 'char-write-cmd 0x002e 56{0:02X}{1:02X}{2:02X}00f0aa'.format(r, g, b)
    print line
    gatt.sendline(line)
    # Wait a short period of time and setup for the next loop iteration.
    time.sleep(SLEEP_SEC)
    last = now
