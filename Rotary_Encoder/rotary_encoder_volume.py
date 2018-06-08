import rotaryio
import board
import digitalio
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

button = digitalio.DigitalInOut(board.D12)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

encoder = rotaryio.IncrementalEncoder(board.D10, board.D9)

cc = ConsumerControl()

button_state = None
last_position = encoder.position

while True:
    position = encoder.position
    diff = position - last_position
    if diff > 0:
        for _ in range(diff):
            cc.send(ConsumerControlCode.VOLUME_INCREMENT)
            print(position)
    elif diff < 0:
        for _ in range(-diff):  # or abs(diff)
            cc.send(ConsumerControlCode.VOLUME_DECREMENT)
            print(position)
    last_position = position
    if not button.value and button_state is None:
        button_state = "pressed"
    if button.value and button_state == "pressed":
        print("button")
        cc.send(ConsumerControlCode.PLAY_PAUSE)
        button_state = None
