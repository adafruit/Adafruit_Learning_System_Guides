import digitalio
import board
import storage

# For Gemma M0, Trinket M0, Metro M0 Express, ItsyBitsy M0 Express
switch = digitalio.DigitalInOut(board.D2)
# switch = digitalio.DigitalInOut(board.D5)  # For Feather M0 Express
# switch = digitalio.DigitalInOut(board.D7)  # For Circuit Playground Express
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# If the switch pin is connected to ground CircuitPython can write to the drive
storage.remount("/", switch.value)
