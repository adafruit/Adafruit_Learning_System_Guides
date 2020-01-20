import usb_hid
from adafruit_circuitplayground.express import cpx
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

cc = ConsumerControl(usb_hid.devices)

while True:
    if cpx.button_a:
        cc.send(ConsumerControlCode.VOLUME_INCREMENT)
        while cpx.button_a:
            pass
    if cpx.button_b:
        cc.send(ConsumerControlCode.VOLUME_DECREMENT)
        while cpx.button_b:
            pass
