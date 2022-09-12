# SPDX-FileCopyrightText: 2022 Brian Rossman
# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
A CircuitPython program to identify reed switch terminals on a switch with three
terminals (normally closed, normally open, and common). This code is not designed
for two terminal reed switches.
"""
import time
import board
import digitalio
import supervisor

# Update these pins to match the pins to which you connected the reed switch.
TERMINAL_ONE = board.D14
TERMINAL_TWO = board.D32
TERMINAL_THREE = board.D15

# Create digital pin objects using the pins defined above.
pin_1 = digitalio.DigitalInOut(TERMINAL_ONE)
pin_2 = digitalio.DigitalInOut(TERMINAL_TWO)
pin_3 = digitalio.DigitalInOut(TERMINAL_THREE)

# Wait for the serial connection to be established.
while not supervisor.runtime.serial_connected:
    time.sleep(0.25)
time.sleep(1)

# Prompt and wait for confirmation the magnet is NOT near the reed switch.
print("Ensure no magnet is near the reed switch.")
print("Press ENTER to continue")
input()  # Waits for you to press enter to continue.

# Set Terminal 1 as the only output.
pin_1.switch_to_output()

# Set Terminal 2 & 3 as inputs to detect connectivity.
pin_2.switch_to_input(pull=digitalio.Pull.UP)
pin_3.switch_to_input(pull=digitalio.Pull.UP)

# Set the output pin to False.
pin_1.value = False

# Negate pin logic due to use of pull-up.
ab_common = not pin_2.value
ac_common = not pin_3.value

# Prompt and wait for confirmation the magnet IS near the reed switch.
print("Place the magnet against the reed switch.")
print("Press ENTER to continue")
input()  # Waits for you to press enter to continue.

# Negate pin logic due to use of pull-up.
b_when_closed = not pin_2.value
c_when_closed = not pin_3.value

# Print pin assignments for reference.
print(f"Terminal pin assignments:\nTerminal 1 = {TERMINAL_ONE}" +
      f"\nTerminal 2 = {TERMINAL_TWO}\nTerminal 3 = {TERMINAL_THREE}\n")

# Print which terminal is Normally Closed, Common, and Normally Open.
if ab_common and not ac_common and not b_when_closed and not c_when_closed:
    print("Normally Closed: Terminal 1, Common: Terminal 2, Normally Open: Terminal 3")
elif not ab_common and ac_common and not b_when_closed and not c_when_closed:
    print("Normally Closed: Terminal 1, Common: Terminal 3, Normally Open: Terminal 2")
elif ab_common and not ac_common and not b_when_closed and c_when_closed:
    print("Normally Closed: Terminal 2, Common: Terminal 1, Normally Open: Terminal 3")
elif not ab_common and not ac_common and not b_when_closed and c_when_closed:
    print("Normally Closed: Terminal 2, Common: Terminal 3, Normally Open: Terminal 1")
elif not ab_common and ac_common and b_when_closed and not c_when_closed:
    print("Normally Closed: Terminal 3, Common: Terminal 1, Normally Open: Terminal 2")
elif not ab_common and not ac_common and b_when_closed and not c_when_closed:
    print("Normally Closed: Terminal 3, Common: Terminal 2, Normally Open: Terminal 1")
else:
    # All options are covered above. If none are valid, there may be an issue with your wiring.
    print("Something went wrong, check connections and try again.")
