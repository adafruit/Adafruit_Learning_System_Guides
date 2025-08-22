# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import json
import os
import tomllib
import shutil
import requests
from kittentts import KittenTTS
import soundfile as sf


with open("weather_narrator.toml", "rb") as f:
    config = tomllib.load(f)

m = KittenTTS("KittenML/kitten-tts-nano-0.2")

replacements = {"mph": "miles per hour"}

# latlng_lookup_url = "https://api.weather.gov/points/{lat},{lon}"

voice = config.get("voice", None)
location_points = config.get("location_points", "36,33")

weather_data = requests.get(
    f"https://api.weather.gov/gridpoints/TOP/{location_points}/forecast", timeout=20
).json()
print("Got weather. Building script...")

with open("forecast.json", "w") as f:
    json.dump(weather_data, f)

forecast_length = config.get("forecast_length", None)

shutil.rmtree("sound_files", ignore_errors=True)
os.mkdir("sound_files")

for i, period in enumerate(weather_data["properties"]["periods"]):
    if forecast_length is None or i < forecast_length:
        filename = period["name"].replace(" ", "_")
        outstr = ""
        if i == 0:
            outstr += f'Current Temperature is {period["temperature"]} degrees. '
        outstr += f'{period["name"]} {period["detailedForecast"]}'

        for key, replacement in replacements.items():
            outstr = outstr.replace(key, replacement)
        print(f"script: {outstr}")
        print("Generating audio...")
        audio = m.generate(outstr, voice=voice)
        output_file = f"sound_files/{filename}.wav"
        print(f"Writing {output_file}")
        sf.write(output_file, audio, 24000)
print("Audio generation complete")
