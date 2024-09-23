# SPDX-FileCopyrightText: 2024 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import board
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_pyportal import PyPortal

# Adafruit IO shared feed key
IO_FEED_KEY = 'location'
# Fetch the location every 5 minutes
SLEEP_DELAY_MINUTES = 5
# Set the backlight brightness, 0.0 (off) to 1.0 (max brightness)
BACKLIGHT_BRIGHTNESS = 0.5
# Location text and images
LOCATION_IMAGES = { 'home': 'images/home.bmp', 'work': 'images/office.bmp',
                    'gym': 'images/workout.bmp', 'commute': 'images/subway.bmp' }

# Create the PyPortal object
pyportal = PyPortal(status_neopixel=board.NEOPIXEL)

# Configure the PyPortal's display
display = board.DISPLAY
display.rotation = 0
display.brightness = BACKLIGHT_BRIGHTNESS

# Display label and image coordinates
TEXT_AREA_X = display.width // 6
TEXT_AREA_Y = 20
TEXT_AREA_LOCATION_X = display.width // 3
TEXT_AREA_LOCATION_Y = display.height - 20
IMAGE_SPRITE_X = (display.width // 3) - 10
IMAGE_SPRITE_Y = display.height // 5

# Create a displayIO Group
group = displayio.Group()

# Draw the background
bg_group = displayio.Group()
rect = Rect(0, 0, display.width, display.height, fill=0xFFFFFF)
bg_group.append(rect)
group.append(bg_group)

# Use the default font
font = terminalio.FONT

# Draw a label for the header text
text_area = label.Label(font, text="Where's My Friend?", color=0x000000, scale=2)
text_area.x = TEXT_AREA_X
text_area.y = TEXT_AREA_Y
group.append(text_area)

# Draw a label for the location text
text_area_location = label.Label(font, text="", color=0x000000, scale=3)
text_area_location.x = TEXT_AREA_LOCATION_X
text_area_location.y = TEXT_AREA_LOCATION_Y
group.append(text_area_location)

# Create a group for the icon only
icon_group = displayio.Group()
group.append(icon_group)

# Show the group
display.root_group = group

def set_image(image_group, filename):
    """Sets the image file for a given group for display."""
    print(f"Set image to {filename}")
    if image_group:
        image_group.pop()

    image_file = open(filename, "rb")
    image = displayio.OnDiskBitmap(image_file)
    image_sprite = displayio.TileGrid(image,
                                      pixel_shader=getattr(image, 'pixel_shader',
                                      displayio.ColorConverter()))
    image_sprite.x = IMAGE_SPRITE_X
    image_sprite.y = IMAGE_SPRITE_Y
    image_group.append(image_sprite)

prv_location = None
while True:
    try:
        print("Fetching location data...")
        # Fetch the location data from Adafruit IO
        feed = pyportal.get_io_feed(IO_FEED_KEY)
        # If the location value is in the list of images
        if feed['last_value'] in LOCATION_IMAGES:
            # Check if the location has changed from the last time
            # we fetched the location
            if prv_location == feed['last_value']:
                print("Location has not changed!")
            else: # Location has changed
                print(f"Location: {feed['last_value']}")
                # Load the image for the current location
                set_image(icon_group, LOCATION_IMAGES[feed['last_value']])
                # Update the location text
                text_area_location.text=f"@ {feed['last_value']}"
                # Show the refreshed group
                display.root_group = group
                # Update the previous location
                prv_location = feed['last_value']
        else:
            print("Location not found in images!")
            # Update the location text
            text_area_location.text="@ unknown"
            # Show the refreshed group
            display.root_group = group
    except RuntimeError as e:
        print("Failed to fetch location data: ", e)

    # Wait 5 minutes (300 seconds) before fetching the location feed again
    print("Sleeping, fetching the location again in 5 minutes!")
    time.sleep(SLEEP_DELAY_MINUTES * 60)
