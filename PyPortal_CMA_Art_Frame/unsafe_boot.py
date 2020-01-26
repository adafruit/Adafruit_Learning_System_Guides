import time
import digitalio
import storage
import board

# Either of these should work for the PyPortal
switch = digitalio.DigitalInOut(board.D4) # upper port
#switch = digitalio.DigitalInOut(board.D3) # lower port

switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# If the switch pin is connected to ground CircuitPython can write to the drive
# Use a female/female jumper wire to connect the outer pins in the D4 connecter

storage.remount("/", disable_concurrent_write_protection= not switch.value)
if switch.value:
    print("File system is read-only, insert jumper in data port between")
    print("pins 1 and 3 to make it writeable.")
else:
    print("File system is writable, remove jumper in data port to make")
    print("it read-only and available to CircuitPython.")

time.sleep(5)
