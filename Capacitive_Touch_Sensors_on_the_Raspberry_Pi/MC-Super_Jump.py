import time
import board
import mcpi.minecraft as minecraft
from digitalio import DigitalInOut, Direction

mc = minecraft.Minecraft.create()

pad_pin = board.D23
pad = DigitalInOut(pad_pin)
pad.direction = Direction.INPUT

already_pressed = False

while True:

    if pad.value and not already_pressed:
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y + 10
        z = pos.z
        mc.player.setPos(x, y, z)
    alreadyPressed = pad.value
    time.sleep(0.1)
