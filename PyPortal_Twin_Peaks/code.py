# Adafruit PyPortal display of Twin Peaks
# Liz (BlitzCityDIY) for Adafruit Industries  MIT License
# Tutorial: https://learn.adafruit.com/twin-peaks-light-reactive-pyportal-picture-frame
import time
import board
from analogio import AnalogIn
from adafruit_pyportal import PyPortal

analogin = AnalogIn(board.LIGHT)

cwd = ("/"+__file__).rsplit('/', 1)[0]

laura = (cwd+"/laura.bmp")

woodsman = (cwd+"/woodsman.bmp")

gottaLight = (cwd+"/gottaLight.wav")

pyportal = PyPortal(default_bg=laura)

def getVoltage(pin):  # helper
    return (pin.value * 3.3) / 65536

while True:

    if getVoltage(analogin) > 0.175:
        pyportal.set_background(laura)
        time.sleep(1)
    else:
        pyportal.set_background(woodsman)
        pyportal.play_file(gottaLight)
        time.sleep(1)
