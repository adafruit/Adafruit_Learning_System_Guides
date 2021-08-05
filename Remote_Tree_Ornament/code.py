import adafruit_irremote
import board
import digitalio
import neopixel
import pulseio

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

red_led = digitalio.DigitalInOut(board.D13)
red_led.direction = digitalio.Direction.OUTPUT

pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# among others, this example works with the Adafruit mini IR remote:
# https://www.adafruit.com/product/389
# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)

# IR Remote Mapping
'''
 1: [255, 2, 247, 8]
 2: [255, 2, 119, 136]
 3: [255, 2, 183, 72]
 4: [255, 2, 215, 40]
 5: [255, 2, 87, 168]
 6: [255, 2, 151, 104]
 7: [255, 2, 231, 24]
 8: [255, 2, 103, 152]
 9: [255, 2, 167, 88]
 0: [255, 2, 207, 48]

^ : [255, 2, 95, 160]
v : [255, 2, 79, 176]
> : [255, 2, 175, 80]
< : [255, 2, 239, 16]

Enter: [255, 2, 111, 144]
Setup: [255, 2, 223, 32]
Stop/Mode: [255, 2, 159, 96]
Back: [255, 2, 143, 112]

Vol - : [255, 2, 255, 0]
Vol + : [255, 2, 191, 64]

Play/Pause: [255, 2, 127, 128]
'''

RED = (255, 0, 0)
GREEN = (0, 255, 0)
WHITE = (85, 85, 85)
BLUE = (0, 0, 255)
PINK = (128, 0, 128)
YELLOW = (148, 108, 0)
PURPLE = (200, 0, 55)
TEAL = (0, 200, 100)
ORANGE = (100, 45, 0)
BLACK = (0, 0, 0)

last_command = None

while True:
    red_led.value = False
    try:
        pulses = decoder.read_pulses(pulsein)
    except MemoryError as e:
        print("Memory error: ", e)
        continue
    red_led.value = True
    print("Heard", len(pulses), "Pulses:", pulses)
    command = None
    try:
        code = decoder.decode_bits(pulses, debug=False)
        if len(code) > 3:
            command = code[2]
        print("Decoded:", code)
    except adafruit_irremote.IRNECRepeatException:  # unusual short code!
        print("NEC repeat!")
        command = last_command
    except adafruit_irremote.IRDecodeException as e:  # failed to decode
        print("Failed to decode:", e)
    except MemoryError as e:
        print("Memory error: ", e)

    if not command:
        continue
    last_command = command

    print("----------------------------")
    red_led.value = False

    if command == 247:  # IR button 1
        pixels.fill(RED)
    elif command == 119:  # 2
        pixels.fill(GREEN)
    elif command == 183:  # 3
        pixels.fill(WHITE)
    elif command == 215:  # 4
        pixels.fill(BLUE)
    elif command == 87:  # 5
        pixels.fill(PINK)
    elif command == 151:  # 6
        pixels.fill(YELLOW)
    elif command == 231:  # 7
        pixels.fill(PURPLE)
    elif command == 103:  # 8
        pixels.fill(TEAL)
    elif command == 167:  # 9
        pixels.fill(ORANGE)
    elif command == 207:
        pixels.fill(BLACK)  # 0/10+
