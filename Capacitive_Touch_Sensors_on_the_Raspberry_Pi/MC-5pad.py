import RPi.GPIO as GPIO
import time
import mcpi.minecraft as minecraft
mc = minecraft.Minecraft.create()

GPIO.setmode(GPIO.BCM)

#set the GPIO input pins
pad0 = 22
pad1 = 27
pad2 = 17
pad3 = 24
pad4 = 23

GPIO.setup(pad0, GPIO.IN)
GPIO.setup(pad1, GPIO.IN)
GPIO.setup(pad2, GPIO.IN)
GPIO.setup(pad3, GPIO.IN)
GPIO.setup(pad4, GPIO.IN)

pad0alreadyPressed = False
pad3alreadyPressed = False
pad4alreadyPressed = False

immutable = False
tnt = 46
water = 9
flowers = 38

while True:
    pad0pressed = not GPIO.input(pad0)
    pad1pressed = not GPIO.input(pad1)
    pad2pressed = not GPIO.input(pad2)
    pad3pressed = not GPIO.input(pad3)
    pad4pressed = not GPIO.input(pad4)

    if pad0pressed and not pad0alreadyPressed:
        #teleport
        x = 0
        y = 0
        z = 0
        mc.player.setPos(x, y, z)
    pad0alreadyPressed = pad0pressed

    if pad1pressed:
        #Flowers
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, flowers)

    if pad2pressed:
        #TNT
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, tnt, 1)

    if pad3pressed and not pad3alreadyPressed:
        #Chat message: Are in water?
        pos = mc.player.getPos()
        block = mc.getBlock(pos.x, pos.y, pos.z)
        inWater = block == water
        mc.postToChat("In water: " + str(inWater))
    pad3alreadyPressed = pad3pressed

    if pad4pressed and not pad4alreadyPressed:
        #Immutable
        immutable = not immutable
        mc.setting("world_immutable", immutable)
        mc.postToChat("Immutable: " + str(immutable))
    pad4alreadyPressed = pad4pressed

    time.sleep(0.1)
