from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode


def log(message):
    print("\t\tHIDDEMO::%s" % message)


class SimpleHid:
    def __init__(self):
        self.kbd = Keyboard()
        print("SimpleHid inited")

    def run(self, detector, state_map, puff_stat):  # pylint:disable=unused-argument

        if state_map[detector.state]["name"] == "WAITING":
            self.kbd.send(Keycode.ONE)

        if state_map[detector.state]["name"] == "STARTED":
            self.kbd.send(Keycode.TWO)

        if state_map[detector.state]["name"] == "DETECTED":
            self.kbd.send(Keycode.SIX)
