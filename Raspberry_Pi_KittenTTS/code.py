# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import json
import time
import glob
import os
import tomllib
from datetime import datetime
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer


from kittentts import KittenTTS
import soundfile as sf


print("initializing...")

with open("weather_narrator.toml", "rb") as f:
    config = tomllib.load(f)
voice = config.get("voice", None)
sound_device = config.get("sound_device", None)

day_of_month_words = [
    "1st",
    "2nd",
    "3rd",
    "4th",
    "5th",
    "6th",
    "7th",
    "8th",
    "9th",
    "10th",
    "11th",
    "12th",
    "13th",
    "14th",
    "15th",
    "16th",
    "17th",
    "18th",
    "19th",
    "20th",
    "21st",
    "22nd",
    "23rd",
    "24th",
    "25th",
    "26th",
    "27th",
    "28th",
    "29th",
    "30th",
    "31st",
]

button = DigitalInOut(board.D17)
button.direction = Direction.INPUT
button.pull = Pull.UP

debounced_btn = Debouncer(button)

with open("forecast.json", "r") as f:
    forecast = json.load(f)

m = KittenTTS("KittenML/kitten-tts-nano-0.1")


def generate_date_time_audio(date_obj):
    replacements = {
        "00": "oh clock",
        "01": "oh 1",
        "02": "oh 2",
        "03": "oh 3",
        "04": "oh 4",
        "05": "oh 5",
        "06": "oh 6",
        "07": "oh 7",
        "08": "oh 8",
        "09": "oh 9",
    }

    now_date_obj = datetime.now()
    try:
        os.remove("date.wav")
    except FileNotFoundError:
        pass
    month = date_obj.strftime("%B")
    day_word = day_of_month_words[date_obj.day - 1]
    date_script = f"{month} {day_word}, {date_obj.year}."

    time_script = now_date_obj.strftime("%-I %M %p")
    for key, val in replacements.items():
        time_script = time_script.replace(key, val)

    date_script += f" The time is: {time_script}."
    audio = m.generate(date_script, voice=voice)
    sf.write("date.wav", audio, 24000)


print("Press button to hear time and weather...")
while True:
    debounced_btn.update()
    if debounced_btn.fell:
        print("just pressed")

        dt_format = "%Y-%m-%dT%H:%M:%S%z"
        forecast_date_obj = datetime.strptime(
            forecast["properties"]["periods"][0]["startTime"], dt_format
        )

        generate_date_time_audio(forecast_date_obj)

        files_to_read = glob.glob("sound_files/*.wav")
        sorted_files_asc = sorted(files_to_read, key=os.path.getmtime)
        sorted_files_asc.insert(0, "date.wav")
        for file in sorted_files_asc:
            if sound_device is None:
                os.system(f"aplay {file}")
            else:
                os.system(f"aplay -D {sound_device} {file}")

    time.sleep(0.01)
