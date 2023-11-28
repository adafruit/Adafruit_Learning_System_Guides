# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_magtag.magtag import MagTag
from adafruit_progressbar.progressbar import ProgressBar

# Set up where we'll be fetching data from
DATA_SOURCE = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/country_data/United%20States.csv"  # pylint: disable=line-too-long
# Find data for other countries/states here:
# https://github.com/owid/covid-19-data/tree/master/public/data/vaccinations

magtag = MagTag(url=DATA_SOURCE)
magtag.network.connect()

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        8,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Title

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        23,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Date

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        40,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Vaccinated text

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        85,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Fully vaccinated text

BAR_WIDTH = magtag.graphics.display.width - 80
BAR_HEIGHT = 25
BAR_X = magtag.graphics.display.width // 2 - BAR_WIDTH // 2

progress_bar = ProgressBar(
    BAR_X, 50, BAR_WIDTH, BAR_HEIGHT, 1.0, bar_color=0x999999, outline_color=0x000000
)

progress_bar_1 = ProgressBar(
    BAR_X, 95, BAR_WIDTH, BAR_HEIGHT, 1.0, bar_color=0x999999, outline_color=0x000000
)

magtag.graphics.splash.append(progress_bar)
magtag.graphics.splash.append(progress_bar_1)
magtag.graphics.set_background("/bmps/background.bmp")


def l_split(line):
    line_list = []
    print(line)
    while "," in line:
        if line[0] == '"':
            temp = line.split('"', 2)[1]
            line_list.append(temp)
            line = line.split('"', 2)[2][1:]
        else:
            temp, line = line.split(",", 1)
            line_list.append(temp)
    line_list.append(line)
    return line_list


try:
    table = magtag.fetch().split("\n")
    columns = l_split(table[0])
    latest = l_split(table[-2])
    print(columns)
    print(latest)
    value = dict(zip(columns, latest))
    print("Response is", value)
    print(value)

    vaccinated = int(value["people_vaccinated"]) / 331984513
    fully_vaccinated = int(value["people_fully_vaccinated"]) / 331984513

    magtag.set_text(f"{value['location']} Vaccination Rates", 0, False)
    magtag.set_text(value["date"], 1, False)
    magtag.set_text("Vaccinated: {:.2f}%".format(vaccinated * 100), 2, False)
    magtag.set_text(
        "Fully Vaccinated: {:.2f}%".format(fully_vaccinated * 100), 3, False
    )

    progress_bar.progress = vaccinated
    progress_bar_1.progress = fully_vaccinated

    magtag.refresh()

    SECONDS_TO_SLEEP = 24 * 60 * 60  # Sleep for one day

except (ValueError, RuntimeError, ConnectionError, OSError) as e:
    print("Some error occured, retrying in one hour! -", e)
    seconds_to_sleep = 60 * 60  # Sleep for one hour

print(f"Sleeping for {SECONDS_TO_SLEEP} seconds")
magtag.exit_and_deep_sleep(SECONDS_TO_SLEEP)
