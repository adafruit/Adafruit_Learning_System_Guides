"""
Slider Trinkey Monitor Brightness Demo for Windows
(Requires Hue and Monitor Brightness CircuitPython example to be running on the Slider Trinkey)
"""
import sys
import screen_brightness_control as sbc
import serial
from serial.tools import list_ports

slider_trinkey_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x8102:
            slider_trinkey_port = p
            print("Found Slider Trinkey!")
            trinkey = serial.Serial(p.device)
            break
else:
    print("Did not find Slider Trinkey port :(")
    sys.exit()

curr_brightness = sbc.get_brightness()

while True:
    x = trinkey.readline().decode('utf-8')
    if not x.startswith("Slider: "):
        continue

    val = int(float(x.split(": ")[1]))

    if val != curr_brightness:
        print("Setting brightness to:", val)
        sbc.set_brightness(val)
        curr_brightness = sbc.get_brightness()
