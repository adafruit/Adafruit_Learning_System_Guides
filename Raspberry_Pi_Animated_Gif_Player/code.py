import usb_cdc
import rotaryio
import board
import digitalio

serial = usb_cdc.data
encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
button = digitalio.DigitalInOut(board.SWITCH)
button.switch_to_input(pull=digitalio.Pull.UP)

last_position = None
button_state = False

while True:
    position = encoder.position
    if last_position is None or position != last_position:
        serial.write(bytes(str(position) + ",", "utf-8"))
    last_position = position
    print(button.value)
    if not button.value and not button_state:
        button_state = True
    if button.value and button_state:
        serial.write(bytes("click,", "utf-8"))
        button_state = False
