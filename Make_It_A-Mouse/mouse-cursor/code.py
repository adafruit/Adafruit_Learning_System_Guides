import usb_hid
from adafruit_circuitplayground.express import cpx
from adafruit_hid.mouse import Mouse

m = Mouse(usb_hid.devices)
cpx.adjust_touch_threshold(200)

while True:
    if cpx.touch_A4:
        m.move(-1, 0, 0)
    if cpx.touch_A3:
        m.move(1, 0, 0)
    if cpx.touch_A7:
        m.move(0, -1, 0)
    if cpx.touch_A1:
        m.move(0, 1, 0)
