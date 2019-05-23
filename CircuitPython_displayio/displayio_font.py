import board
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

display = board.DISPLAY

# Set text, font, and color
text = "HELLO WORLD"
font = bitmap_font.load_font("/Helvetica-Bold-16.bdf")
color = 0xFF00FF

# Create the tet label
text_area = label.Label(font, text=text, color=color)

# Set the location
text_area.x = 20
text_area.y = 20

# Show it
display.show(text_area)
