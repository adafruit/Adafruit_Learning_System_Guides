# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_magtag.magtag import MagTag

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.covidtracking.com/v1/us/current.json"
DATE_LOCATION = [0, 'dateChecked']
NEWPOS_LOCATION = [0, 'positiveIncrease']
CURRHOSP_LOCATION = [0, 'hospitalizedCurrently']
NEWHOSP_LOCATION = [0, 'hospitalizedIncrease']
ALLDEATH_LOCATION = [0, 'death']
NEWDEATH_LOCATION = [0, 'deathIncrease']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(DATE_LOCATION, NEWPOS_LOCATION,
               CURRHOSP_LOCATION, NEWHOSP_LOCATION,
               ALLDEATH_LOCATION, NEWDEATH_LOCATION),
)
magtag.network.connect()

# All positive
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 15),
    text_transform=lambda x: "Date: {}".format(x[0:10]),
)
# Positive increase
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 35),
    text_transform=lambda x: "New positive:   {:,}".format(x),
)
# Curr hospitalized
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 55),
    text_transform=lambda x: "Current Hospital:   {:,}".format(x),
)
# Change in hospitalized
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 75),
    text_transform=lambda x: "Change in Hospital:   {:,}".format(x),
)
# All deaths
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 95),
    text_transform=lambda x: "Total deaths:   {:,}".format(x),
)
# new deaths
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 115),
    text_transform=lambda x: "New deaths:   {:,}".format(x),
)

timestamp = None
while True:
    if not timestamp or (time.monotonic() - timestamp) > 60:  # once every 60 seconds...
        try:
            value = magtag.fetch()
            print("Response is", value)
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
        timestamp = time.monotonic()
