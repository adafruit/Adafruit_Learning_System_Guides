import board
import pulseio
import adafruit_irremote
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

last_command = None

brightness_up = 95  # Up arrow
brightness_down = 79  # Down arrow

command_to_color = {  # button = color
    247: (255, 0, 0),  # 1 = red
    119: (255, 40, 0),  # 2 = orange
    183: (255, 150, 0),  # 3 = yellow
    215: (0, 255, 0),  # 4 = green
    87: (0, 255, 120),  # 5 = teal
    151: (0, 255, 255),  # 6 = cyan
    231: (0, 0, 255),  # 7 = blue
    103: (180, 0, 255),  # 8 = purple
    167: (255, 0, 20),  # 9 = magenta
    207: (255, 255, 255),  # 0 = white
    127: (0, 0, 0),  # Play/Pause = off
}

while True:
    pulses = decoder.read_pulses(pulsein, max_pulse=5000)
    command = None
    try:
        code = decoder.decode_bits(pulses)
        if len(code) > 3:
            command = code[2]
        print("Decoded:", command)
        print("-------------")
    except adafruit_irremote.IRNECRepeatException:  # Catches the repeat signal
        command = last_command
    except adafruit_irremote.IRDecodeException:  # Failed to decode
        pass

    if not command:
        continue
    last_command = command

    if command == brightness_up:
        pixels.brightness += 0.1
    elif command == brightness_down:
        pixels.brightness -= 0.1
    elif command in command_to_color:
        pixels.fill(command_to_color[command])
