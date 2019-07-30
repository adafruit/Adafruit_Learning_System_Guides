import time
import board
import mcpi.minecraft as minecraft
from digitalio import DigitalInOut, Direction

mc = minecraft.Minecraft.create()

pad_pin = board.D23

pad = DigitalInOut(pad_pin)
pad.direction = Direction.INPUT

# melon block
block_type = 103

while True:

    if pad.value:
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, block_type)

    time.sleep(0.1)
