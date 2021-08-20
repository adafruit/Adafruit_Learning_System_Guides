import usb_hid
from adafruit_circuitplayground.express import cpx
from adafruit_hid.mouse import Mouse

m = Mouse(usb_hid.devices)

while True:
    if cpx.button_a:
        m.press(Mouse.LEFT_BUTTON)
        while cpx.button_a:    # Wait for button A to be released
            pass
        m.release(Mouse.LEFT_BUTTON)

    if cpx.button_b:
        m.press(Mouse.RIGHT_BUTTON)
        while cpx.button_b:    # Wait for button B to be released
            pass
        m.release(Mouse.RIGHT_BUTTON)
