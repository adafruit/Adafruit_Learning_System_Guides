"""
Code for the LED Infinity Mirror Collar. Allows the animation sequence 
and color to be controlled by input from the Adafruit Bluefruit App
"""
import board
import random
import neopixel
import digitalio
from adafruit_debouncer import Debouncer

# LED Animation modules
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import colorwheel


# Bluetooth modules
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# NeoPixel control pin
pixel_pin = board.D5

# Number of pixels in the collar (arranged in two rows)
pixel_num = 24

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.5, auto_write=False)

# Create a switch from the ItsyBity's on-board pushbutton to toggle charge mode
mode_pin = digitalio.DigitalInOut(board.SWITCH)
mode_pin.direction = digitalio.Direction.INPUT
mode_pin.pull = digitalio.Pull.UP
switch = Debouncer(mode_pin)

# Create the animations
comet = Comet(pixels, speed=0.06, color=(180,0,255), tail_length=10, bounce=True)
chase = Chase(pixels, speed=0.05, size=3, spacing=3, color=(0,255,255), reverse=True)
rainbow_comet = RainbowComet(pixels, speed=.06)
pulse = Pulse(pixels, speed=.04, color=(255,0,0), period = 0.2)


# Our animations sequence
seconds_per_animation = 10
animations = AnimationSequence(comet, rainbow_comet, chase, advance_interval=seconds_per_animation, auto_clear=True)
# Current display determines whether we are showing the animation sequence or the pulse animation
current_display = animations

# Mode changes the color of random animations randomly
random_color_mode = True

def random_animation_color(anims):
    if random_color_mode:
        anims.color = colorwheel(random.randint(0,255))
        
animations.add_cycle_complete_receiver(random_animation_color)


# After we complete three pulse cycles, return to main animations list
def pulse_finished(anim):
    global current_display
    current_display = animations

pulse.add_cycle_complete_receiver(pulse_finished)
pulse.notify_cycles = 3


# Bluetooth
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# Set charge_mode to True to turn off the LED Animations and Bluetooth
#  e.g. when charging the battery
charge_mode = False

# Checks the ItsyBitsy's switch button
def check_switch():
    global charge_mode
    switch.update()
    if switch.fell:  #Switch changed state
        charge_mode = not charge_mode
        # if display has just been turned off, clear all LEDs, disconnect, stop advertising
        if charge_mode:
            pixels.fill((0,0,0))
            pixels.show()
            if ble.connected:
                for conn in ble.connections:
                    conn.disconnect()
            if ble.advertising:
                ble.stop_advertising()

# Main program loop
while True:
    # Check whether charge mode has been changed
    check_switch()
    if charge_mode:
        pass
    else:
        current_display.animate()
        if ble.connected:
            if uart_service.in_waiting:
                #Packet is arriving
                packet = Packet.from_stream(uart_service)
                if isinstance(packet, ButtonPacket) and packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        # Animation colors change to a random new value after every animation sequence
                        random_color_mode = True
                    elif packet.button == ButtonPacket.BUTTON_2:
                        # Animation colors stay the same unless manually changed
                        random_color_mode = False
                    elif packet.button == ButtonPacket.BUTTON_3:
                        # Stay on the same animation
                        animations._advance_interval = None
                    elif packet.button == ButtonPacket.BUTTON_4:
                        # Auto-advance animations
                        animations._advance_interval = seconds_per_animation*1000
                    elif packet.button == ButtonPacket.LEFT:
                        # Go to first animation in the sequence
                        animations.activate(0)
                    elif packet.button == ButtonPacket.RIGHT:
                        # Go to the next animation in the sequence
                        animations.next()
                elif isinstance(packet, ColorPacket):
                    animations.color = packet.color
                    pulse.color = packet.color
                    # temporarily change to pulse display to show off the new color
                    current_display = pulse

        else:
            if not ble.advertising:
                ble.start_advertising(advertisement)
