import time
import pulseio
import board
import adafruit_irremote
import digitalio
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

button_a = digitalio.DigitalInOut(board.BUTTON_A)
button_a.switch_to_input(pull=digitalio.Pull.DOWN)

button_b = digitalio.DigitalInOut(board.BUTTON_B)
button_b.switch_to_input(pull=digitalio.Pull.DOWN)

red_led = digitalio.DigitalInOut(board.D13)
red_led.direction = digitalio.Direction.OUTPUT

# Create a 'pulseio' input, to listen to infrared signals on the IR receiver
pulsein = pulseio.PulseIn(board.IR_RX, maxlen=120, idle_state=True)
# Create a decoder that will take pulses and turn them into numbers
decoder = adafruit_irremote.GenericDecode()

# Create a 'pulseio' output, to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.IR_TX, frequency=38000, duty_cycle=2 ** 15)
# Create an encoder that will take numbers and turn them into NEC IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9500, 4500], one=[550, 550],
                                            zero=[550, 1700], trail=0)

# Set between 0 and 1 to set LED pulse speed. Smaller numbers are slower.
healer_led_pulse = 0.008
zombie_led_pulse = 0.07
pixels.brightness = 0.0

# Change to set number of seconds between each signal being sent.
HEALER_TIME = 1
ZOMBIE_TIME = 3

# The Healer and Zombie IR signal codes
HEALER_IR = [72, 69, 65, 76]
ZOMBIE_IR = [90, 79, 77, 66]

human_health_counter = 10
human = 0
healer = 1
zombie = 2

if button_a.value:  # Hold button A down before starting up to set mode Healer.
    mode = healer
    pixels.fill((255, 255, 255))
    pixels.brightness = 0.3
elif button_b.value:  # Hold button A down before starting up to set mode Zombie.
    mode = zombie
    pixels.fill((255, 0, 0))
    pixels.brightness = 0.8
else:  # Defaults to human mode!
    mode = human
    pixels.fill((0, 255, 0))
    pixels.brightness = 0.5

start = time.monotonic()
while True:
    now = time.monotonic()
    if mode is human:
        pulses = decoder.read_pulses(pulsein)
        try:
            # Attempt to convert received pulses into numbers
            received_code = decoder.decode_bits(pulses)
        except adafruit_irremote.IRNECRepeatException:
            # We got an unusual short code, probably a 'repeat' signal
            continue
        except adafruit_irremote.IRDecodeException:
            # Something got distorted or maybe its not an NEC-type remote?
            continue
        print("NEC Infrared code received: ", received_code)
        if received_code == ZOMBIE_IR:
            print("Zombie code received!")
            pixels.fill(0)
            human_health_counter -= 1
            for i in range(human_health_counter):
                pixels[i] = (0, 255, 0)
            if human_health_counter < 1:
                mode = zombie
                pixels.fill((255, 0, 0))
                print("Zombified!")
        if received_code == HEALER_IR:
            print("Healer code received!")
            if human_health_counter < 10:
                pixels.fill(0)
                human_health_counter += 1
                for i in range(human_health_counter):
                    pixels[i] = (0, 255, 0)
            else:
                pass
    elif mode is zombie:
        brightness = pixels.brightness
        brightness += zombie_led_pulse
        if not 0.0 <= brightness <= 1.0:
            zombie_led_pulse = -zombie_led_pulse
            continue
        pixels.brightness = brightness
        if now - start > ZOMBIE_TIME:
            print("Zombie code sent! \n")
            red_led.value = True
            encoder.transmit(pulseout, ZOMBIE_IR)
            red_led.value = False
            start = time.monotonic()
    elif mode is healer:
        brightness = pixels.brightness
        brightness += healer_led_pulse
        if not 0.0 <= brightness <= 0.5:
            healer_led_pulse = -healer_led_pulse
            continue
        pixels.brightness = brightness
        if now - start > HEALER_TIME:
            print("Healer code sent! \n")
            red_led.value = True
            encoder.transmit(pulseout, HEALER_IR)
            red_led.value = False
            start = time.monotonic()
