from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import usb_hid
import puff_detector

kbd = Keyboard(usb_hid.devices)

detector = puff_detector.PuffDetector()


@detector.on_sip
def on_sip(strength, duration):  # pylint:disable=unused-argument
    if strength == puff_detector.STRONG:
        kbd.send(Keycode.LEFT_ARROW)
        kbd.send(Keycode.LEFT_ARROW)
    if strength == puff_detector.SOFT:
        kbd.send(Keycode.LEFT_ARROW)


@detector.on_puff
def on_puff(strength, duration):  # pylint:disable=unused-argument
    if strength == puff_detector.STRONG:
        kbd.send(Keycode.RIGHT_ARROW)
        kbd.send(Keycode.RIGHT_ARROW)
    if strength == puff_detector.SOFT:
        kbd.send(Keycode.RIGHT_ARROW)


detector.run()
