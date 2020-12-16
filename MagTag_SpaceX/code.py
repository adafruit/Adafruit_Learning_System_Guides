# SpaceX Launch Display, by Anne Barela November 2020
# MIT License - for Adafruit Industries LLC
# See https://github.com/r-spacex/SpaceX-API for API info

import time
import terminalio
from adafruit_magtag.magtag import MagTag

months = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
USE_24HR_TIME = True
# in seconds, we can refresh about 100 times on a battery
TIME_BETWEEN_REFRESHES = 24 * 60 * 60  # once a day delay

# Set up data location and fields
DATA_SOURCE = "https://api.spacexdata.com/v4/launches/next"
DETAIL_LOCATION = ['details']
NAME_LOCATION = ['name']
DATE_LOCATION = ['date_local']

# These functions take the JSON data keys and does checks to determine
#   how to display the data. They're used in the add_text blocks below

def mission_transform(val):
    if val == None:
        val = "Unavailable"
    return "Mission: " + val

def time_transform(val2):
    if val2 == None:
        return "When: Unavailable"
    month = int(val2[5:7])
    day = int(val2[8:10])
    hour = int(val2[11:13])
    min = int(val2[14:16])

    if USE_24HR_TIME:
        timestring = "%d:%02d" % (hour, min)
    elif hour > 12:
        timestring = "%d:%02d pm" % (hour-12, min)
    else:
        timestring = "%d:%02d am" % (hour, min)

    return "%s %d, at %s" % (months[month-1], day, timestring)

def details_transform(val3):
    if val3 == None or not len(val3):
        return "Details: To Be Determined"
    return "Details: " + val3[0:166] + "..."

# Set up the MagTag with the JSON data parameters
magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(NAME_LOCATION, DATE_LOCATION, DETAIL_LOCATION)
)

magtag.add_text(
    text_font="Lato-Bold-ltd-25.bdf",
    text_position=(10, 15),
    is_data=False
)
# Display heading text below with formatting above
magtag.set_text("Next SpaceX Launch")

# Formatting for the mission text
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 38),
    text_transform=mission_transform
)

# Formatting for the launch time text
magtag.add_text(
    text_font="Arial-12.bdf",
    text_position=(10, 60),
    text_transform=time_transform
)

# Formatting for the details text
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(10, 94),
    line_spacing=0.8, 
    text_wrap=47,     # wrap text at this count
    text_transform=details_transform
)

try:
    # Have the MagTag connect to the internet
    magtag.network.connect()
    # This statement gets the JSON data and displays it automagically
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    print("Some error occured, retrying! -", e)

# wait 2 seconds for display to complete
time.sleep(2)
magtag.exit_and_deep_sleep(TIME_BETWEEN_REFRESHES)
