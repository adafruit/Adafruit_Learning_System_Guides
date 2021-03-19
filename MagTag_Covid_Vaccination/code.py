from adafruit_magtag.magtag import MagTag
from adafruit_progressbar import ProgressBar

# Set up where we'll be fetching data from
DATA_SOURCE = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/country_data/United%20States.csv"
# Find data for other countries/states here:
# https://github.com/owid/covid-19-data/tree/master/public/data/vaccinations

magtag = MagTag(url=DATA_SOURCE)
magtag.network.connect()

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=((magtag.graphics.display.width // 2) - 1, 8,),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Title

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=((magtag.graphics.display.width // 2) - 1, 23,),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Date

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=((magtag.graphics.display.width // 2) - 1, 40,),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Vaccinated text

magtag.add_text(
    text_font="/fonts/ncenR14.pcf",
    text_position=((magtag.graphics.display.width // 2) - 1, 85,),
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


try:
    value = magtag.fetch().split("\n")[-2].split(",")
    print("Response is", value)

    vaccinated = int(value[-2]) / 331984513
    fully_vaccinated = int(value[-1]) / 331984513

    magtag.set_text(f"{value[0]} Vaccination Rates", 0, False)
    magtag.set_text(value[1], 1, False)
    magtag.set_text("Vaccinated: {:.2f}%".format(vaccinated * 100), 2, False)
    magtag.set_text(
        "Fully Vaccinated: {:.2f}%".format(fully_vaccinated * 100), 3, False
    )

    progress_bar.progress = vaccinated
    progress_bar_1.progress = fully_vaccinated

    magtag.refresh()

except (ValueError, RuntimeError) as e:
    print("Some error occured, retrying! -", e)

seconds_to_sleep = 24 * 60 * 60  # Sleep for one day
print(f"Sleeping for {seconds_to_sleep} seconds")
magtag.exit_and_deep_sleep(seconds_to_sleep)
