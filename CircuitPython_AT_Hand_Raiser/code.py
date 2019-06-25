# ATMakers HandUp
# Listens to the USB Serial port and responds to incoming strings
# Sets appropriate colors on the DotStar LED

# This program uses the board package to access the Trinket's pin names
# and uses adafruit_dotstar to talk to the LED
# other boards would use the neopixel library instead

from time import sleep
import board
import adafruit_dotstar
import supervisor

# create an object for the dotstar pixel on the Trinket M0
# It's an array because it's a sequence of one pixel
pixels = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=.95)

# this function takes a standard "hex code" for a color and returns
# a tuple of (red, green, blue)
def hex2rgb(hex_code):
    red = int("0x"+hex_code[0:2], 16)
    green = int("0x"+hex_code[2:4], 16)
    blue = int("0x"+hex_code[4:6], 16)
    rgb = (red, green, blue)
    # print(rgb)
    return rgb

# This array contains digitized data for a heartbeat wave scaled to between 0 and 1.0
# It is used to create the "beat" mode. Ensure each line is <78 characters for Travis-CI
beatArray = [0.090909091,0.097902098,0.104895105,0.118881119,0.132867133,0.146853147,
             0.153846154,0.160839161,0.181818182,0.181818182,0.195804196,0.181818182,0.188811189,
             0.188811189,0.181818182,0.174825175,0.174825175,0.160839161,0.167832168,0.160839161,
             0.167832168,0.167832168,0.167832168,0.160839161,0.146853147,0.146853147,0.153846154,
             0.160839161,0.146853147,0.153846154,0.13986014,0.153846154,0.132867133,0.146853147,
             0.13986014,0.13986014,0.146853147,0.146853147,0.146853147,0.146853147,0.160839161,
             0.146853147,0.160839161,0.167832168,0.181818182,0.202797203,0.216783217,0.20979021,
             0.202797203,0.195804196,0.195804196,0.216783217,0.160839161,0.13986014,0.13986014,
             0.13986014,0.118881119,0.118881119,0.111888112,0.132867133,0.111888112,0.132867133,
             0.104895105,0.083916084,0.020979021,0,0.230769231,0.636363636,1,0.846153846,
             0.27972028,0.048951049,0.055944056,0.083916084,0.090909091,0.083916084,0.083916084,
             0.076923077,0.076923077,0.076923077,0.090909091,0.06993007,0.083916084,0.076923077,
             0.076923077,0.06993007,0.076923077,0.083916084,0.083916084,0.083916084,0.076923077,
             0.090909091,0.076923077,0.083916084,0.06993007,0.076923077,0.062937063,0.06993007,
             0.062937063,0.055944056,0.055944056,0.048951049,0.041958042,0.034965035,0.041958042,
             0.027972028]

# When we start up, make the LED black
black = (0, 0, 0)
# the color that's passed in over the text input
targetColor = black

# pos is used for all modes that cycle or progress
# it loops from 0-255 and starts over
pos = 0

# curColor is the color that will be displayed at the end of the main loop
# it is mapped using pos according to the mode
curColor = black

# the mode can be one of
# solid - just keep the current color
# blink - alternate between black and curColor
# ramp  - transition continuously between black and curColor
# beat - pulse to a recorded heartbeat intensity
# wheel - change hue around the colorwheel (curColor is ignored)

mode='wheel'

# standard function to rotate around the colorwheel
def wheel(cpos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if cpos < 85:
        return (int(cpos * 3), int(255 - (cpos * 3)), 0)
    elif cpos < 170:
        cpos -= 85
        return (int(255 - (cpos * 3)), 0, int(cpos * 3))
    else:
        cpos -= 170
        return (0, int(cpos * 3), int(255 - cpos * 3))

# We start by turning off pixels
pixels.fill(black)
pixels.show()

# Main Loop
while True:
    # Check to see if there's input available (requires CP 4.0 Alpha)
    if supervisor.runtime.serial_bytes_available:
        # read in text (@mode, #RRGGBB, %brightness, standard color)
        # input() will block until a newline is sent
        inText = input().strip()
        # Sometimes Windows sends an extra (or missing) newline - ignore them
        if inText == "":
            continue
        # Process the input text - start with the presets (no #,@,etc)
        # We use startswith to not have to worry about CR vs CR+LF differences
        if inText.lower().startswith("red"):
            # set the target color to red
            targetColor = (255, 0, 0)
            # and set the mode to solid if we're in a mode that ignores targetColor
            if mode == "wheel":
                mode="solid"
        # similar for green, yellow, and black
        elif inText.lower().startswith("green"):
            targetColor = (0, 255, 0)
            if mode == "wheel":
                mode="solid"
        elif inText.lower().startswith("yellow"):
            targetColor = (200, 200, 0)
            if mode == "wheel":
                mode="solid"
        elif inText.lower().startswith("black"):
            targetColor = (0, 0, 0)
            if mode == "wheel":
                mode="solid"
        # Here we're going to change the mode - which starts w/@
        elif inText.lower().startswith("@"):
            mode= inText[1:]
        # Here we can set the brightness with a "%" symbol
        elif inText.startswith("%"):
            pctText = inText[1:]
            pct = float(pctText)/100.0
            pixels.brightness=pct
        # If we get a hex code set it and go to solid
        elif inText.startswith("#"):
            hexcode = inText[1:]
            targetColor = hex2rgb(hexcode)
            if mode == "wheel":
                mode="solid"
        # if we get a command we don't understand, set it to gray
        # we should probably just ignore it but this helps debug
        else:
            targetColor =(50, 50, 50)
            if mode == "wheel":
                mode="solid"
    else:
        # If no text available, update the color according to the mode
        if mode == 'blink':
            if curColor == black:
                curColor = targetColor
            else:
                curColor = black
            sleep(.4)
            # print('.', end='')
            pixels.fill(curColor)
            pixels.show()
        elif mode == 'wheel':
            sleep(.05)
            pos = (pos + 1) % 255
            pixels.fill(wheel(pos))
            pixels.show()
        elif mode == 'solid':
            pixels.fill(targetColor)
            pixels.show()
        elif mode == 'beat':
            pos = (pos + 5 ) % 106
            scaleAvg = (beatArray[(pos-2)%106] + beatArray[(pos-1)%106] + beatArray[pos] +
                        beatArray[(pos+1)%106] + beatArray[(pos+2)%106])/5
            beatColor = tuple(int(scaleAvg*x) for x in targetColor)
            pixels.fill(beatColor)
            sleep(.025)
            pixels.show()
        elif mode == 'ramp':
            pos = ((pos + 5 ) % 255)
            scaleFactor = (2*abs(pos-127))/255
            beatColor = tuple(int(scaleFactor * x) for x in targetColor)
            pixels.fill(beatColor)
            sleep(.075)
            pixels.show()
