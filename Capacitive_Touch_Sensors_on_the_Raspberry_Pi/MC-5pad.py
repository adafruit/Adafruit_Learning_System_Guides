import time
import board
import mcpi.minecraft as minecraft
from digitalio import DigitalInOut, Direction
mc = minecraft.Minecraft.create()

# set the GPIO input pins
pad0_pin = board.D22
pad1_pin = board.D21
pad2_pin = board.D17
pad3_pin = board.D24
pad4_pin = board.D23

pad0 = DigitalInOut(pad0_pin)
pad1 = DigitalInOut(pad1_pin)
pad2 = DigitalInOut(pad2_pin)
pad3 = DigitalInOut(pad3_pin)
pad4 = DigitalInOut(pad4_pin)

pad0.direction = Direction.INPUT
pad1.direction = Direction.INPUT
pad2.direction = Direction.INPUT
pad3.direction = Direction.INPUT
pad4.direction = Direction.INPUT

pad0_already_pressed = False
pad3_already_pressed = False
pad4_already_pressed = False

immutable = False

tnt = 46
water = 9
flowers = 38

while True:
    pad0_pressed = not pad0.value
    pad1_pressed = not pad1.value
    pad2_pressed = not pad2.value
    pad3_pressed = not pad3.value
    pad4_pressed = not pad4.value

    if pad0_pressed and not pad0_already_pressed:
        #teleport
        x = 0
        y = 0
        z = 0
        mc.player.setPos(x, y, z)
    pad0_already_pressed = pad0_pressed

    if pad1_pressed:
        #Flowers
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, flowers)

    if pad2_pressed:
        #TNT
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, tnt, 1)

    if pad3_pressed and not pad3_already_pressed:
        #Chat message: Are in water?
        pos = mc.player.getPos()
        block = mc.getBlock(pos.x, pos.y, pos.z)
        inWater = block == water
        mc.postToChat("In water: " + str(inWater))
    pad3_already_pressed = pad3_pressed

    if pad4_pressed and not pad4_already_pressed:
        #Immutable
        immutable = not immutable
        mc.setting("world_immutable", immutable)
        mc.postToChat("Immutable: " + str(immutable))
    pad4_already_pressed = pad4_pressed

    time.sleep(0.1)
