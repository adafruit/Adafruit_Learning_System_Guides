'''BLE Synth
File for the Feather nFR52840
Keyboard Portion'''
import time
import board
import digitalio
import adafruit_led_animation.color as color
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

#  setup for LED to indicate BLE connection
blue_led = digitalio.DigitalInOut(board.BLUE_LED)
blue_led.direction = digitalio.Direction.OUTPUT

#  setting up the buttons
switch_pins = [board.D5, board.D6, board.D9, board.D10,
               board.D11, board.D12, board.D13, board.A0, board.A1, board.A2,
               board.A3, board.A4]
switch_array = []

#  creating the button array
for pin in switch_pins:
    switch_pin = digitalio.DigitalInOut(pin)
    switch_pin.direction = digitalio.Direction.INPUT
    switch_pin.pull = digitalio.Pull.UP
    switch_array.append(switch_pin)

#  states for button debouncing
switch1_pressed = False
switch2_pressed = False
switch3_pressed = False
switch4_pressed = False
switch5_pressed = False
switch6_pressed = False
switch7_pressed = False
switch8_pressed = False
switch9_pressed = False
switch10_pressed = False
switch11_pressed = False
switch12_pressed = False
switches_pressed = [switch1_pressed, switch2_pressed, switch3_pressed, switch4_pressed,
                    switch5_pressed, switch6_pressed, switch7_pressed, switch8_pressed,
                    switch9_pressed, switch10_pressed, switch11_pressed, switch12_pressed]

#  colors from Animation library to send as color packets
#  named for notes
color_C = color.RED
color_Csharp = color.ORANGE
color_D = color.YELLOW
color_Dsharp = color.GREEN
color_E = color.TEAL
color_F = color.CYAN
color_Fsharp = color.BLUE
color_G = color.PURPLE
color_Gsharp = color.MAGENTA
color_A = color.GOLD
color_Asharp = color.PINK
color_B = color.WHITE

#  array for colors
color = [color_C, color_Csharp, color_D, color_Dsharp, color_E,
         color_F, color_Fsharp, color_G, color_Gsharp, color_A,
         color_Asharp, color_B]

#  BLE send_packet function
def send_packet(uart_connection_name, packet):
    """Returns False if no longer connected."""
    try:
        uart_connection_name[UARTService].write(packet.to_bytes())
    except:  # pylint: disable=bare-except
        try:
            uart_connection_name.disconnect()
        except:  # pylint: disable=bare-except
            pass
        return False
    return True

ble = BLERadio()

uart_connection = None

if ble.connected:
    for connection in ble.connections:
        if UARTService in connection:
            uart_connection = connection
        break

while True:
    blue_led.value = False
    #  BLE connection
    if not uart_connection or not uart_connection.connected:  # If not connected...
        print("Scanning...")
        for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):  # Scan...
            if UARTService in adv.services:  # If UARTService found...
                print("Found a UARTService advertisement.")
                blue_led.value = True #  LED turns on when connected
                uart_connection = ble.connect(adv)  # Create a UART connection...
                break
        ble.stop_scan()  # And stop scanning.
    #  while connected..
    while uart_connection and uart_connection.connected:
    #  iterate through buttons and colors
        for switch_pin in switch_array:
            i = switch_array.index(switch_pin)
            switches_pressed_state = switches_pressed[i]
            colors = color[i]
            #  if the button is released
            #  worked best if placed before the button press portion
            if switch_pin.value and switches_pressed_state:
                print("button off")
                #  send button packet to stop tone & color (happens on CPB)
                if not send_packet(uart_connection,
                                   ButtonPacket(ButtonPacket.RIGHT, pressed=True)):
                    uart_connection = None
                    continue
                switches_pressed[i] = False  # Set to False.
                #  time delay for BLE, otherwise issues can arrise
                time.sleep(0.05)
            #  if button is pressed:
            if not switch_pin.value and not switches_pressed_state:  # If button A pressed...
                #  send color packet
                if not send_packet(uart_connection, ColorPacket(colors)):
                    uart_connection = None
                    continue
                switches_pressed[i] = True  # Set to True.
                time.sleep(0.05)  # Debounce.
