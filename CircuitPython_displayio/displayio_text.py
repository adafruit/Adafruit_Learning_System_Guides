import board
import terminalio
from adafruit_display_text import label

display = board.DISPLAY

# Set text, font, and color
text = "HELLO WORLD"
font = terminalio.FONT
color = 0x0000FF

# Create the tet label
text_area = label.Label(font, text="HELLO WORLD", color=0x00FF00)

# Set the location
text_area.x = 100
text_area.y = 80

# Show it
display.show(text_area)
