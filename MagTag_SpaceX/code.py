# SpaceX Launch Display, by Anne Barela November 2020
# MIT License - for Adafruit Industries LLC
# See https://github.com/r-spacex/SpaceX-API for API info

import time
import terminalio
from adafruit_magtag.magtag import MagTag

months = ["January", "February", "March", "April", "May", "June", "July", 
          "August", "September", "October", "November", "December"]

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
    # Uncomment the line below to get the full date and time and offset to UTC time (more universal)
    #  return "When: " + val2[0:10] + " at " + val2[11:19] + " (" + val2[19:25] + " UTC)"
    # Uncomment the lines below to get a Month Day and local launch time display am/pm (more US)
    hour = int(val2[11:12])
    if hour <= 12:
        return months[int(val2[5:7])-1] + " " + str(int(val2[8:10])) + ", " + val2[0:4] +  " at " + val2[11:16] + " am"
    else:
        hour = hour - 11
    return months[int(val2[5:7])-1] + " " + str(int(val2[8:10])) + ", " + val2[0:4] +  " at " + str(hour) + val2[13:16] + " pm"
	   
def details_transform(val3):
    if val3 == None:
        return "Details: To Be Determined"
    val3_length = len(val3)
    if val3_length == 0:
        return "Details: To Be Determined"
    return "Details: " + val3[0:min(val3_length,166)] + "..."

# Set up the MagTag with the JSON data parameters
magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(NAME_LOCATION, DATE_LOCATION, DETAIL_LOCATION)
)
# Have the MagTag connect to the internet
magtag.network.connect()

magtag.add_text(
    text_font="Lato-Bold-ltd-25.bdf",
    text_position=(10,15),
    text_scale=1,
    is_data=False
)
# Display heading text below with formatting above
magtag.set_text("Next SpaceX Launch")

# Formatting for the mission text
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10,38),
    text_scale=1,
    text_transform=mission_transform
)

# Formatting for the launch time text
magtag.add_text(
    text_font="Arial-12.bdf",
    text_position=(10,60),
    text_scale=1,
    text_transform=time_transform
)

# Formatting for the details text
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(10,94),
    text_scale=1,
    line_spacing=0.8, 
    text_wrap=47,     # wrap text at this count
    text_transform=details_transform
)

timestamp = None

# Loop forever, checking the time elapsed and updating the screen after a set time
# When power savings code is available, this can be used to save battery life below.
while True:
    if not timestamp or (time.monotonic() - timestamp) > 86400:  # once every day
        try:
            # This statement gets the JSON data and displays it automagically
            value = magtag.fetch()
            print("Response is", value)
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
    timestamp = time.monotonic()
# END
