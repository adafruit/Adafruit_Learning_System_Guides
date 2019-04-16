import RPi.GPIO as GPIO
import time
import mcpi.minecraft as minecraft
mc = minecraft.Minecraft.create()

GPIO.setmode(GPIO.BCM)

padPin = 23

GPIO.setup(padPin, GPIO.IN)

alreadyPressed = False

while True:
    padPressed = GPIO.input(padPin)

    if padPressed and not alreadyPressed:
        pos = mc.player.getPos()
        x = pos.x
        y = pos.y + 10
        z = pos.z
        mc.player.setPos(x, y, z)
    alreadyPressed = padPressed
    time.sleep(0.1)
