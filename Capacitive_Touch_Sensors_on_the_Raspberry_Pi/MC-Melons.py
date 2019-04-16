import RPi.GPIO as GPIO
import time
import mcpi.minecraft as minecraft
mc = minecraft.Minecraft.create()

GPIO.setmode(GPIO.BCM)

padPin = 23

GPIO.setup(padPin, GPIO.IN)

# melon block
blockType = 103

while True:
    padPressed = GPIO.input(padPin)

    if padPressed:
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y
        z = pos.z
        mc.setBlock(x, y, z, blockType)

    time.sleep(0.1)
