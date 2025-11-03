# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import argparse
import json
from pathlib import Path
import os
import shutil
import wave
import requests
from ollama import chat
from ollama import ChatResponse
from piper import PiperVoice

# pylint: disable=line-too-long
parser = argparse.ArgumentParser(
    prog="python generate_translated_weather_audio.py",
    description="Multi-Lingual Weather & Wardrobe Assistant - "
    "Fetches weather conditions from weather.gov for a given set of location points. "
    "Generates a wardrobe suggestion based on the weather conditions. "
    "Translates the weather and wardrobe suggestion into one of 5 other languages. "
    "Synthesizes a wave audio file narrating the weather and wardrobe info in "
    "the specified language.",
    epilog="Made with: SmolLM3 & Piper1-gpl",
)
parser.add_argument(
    "-l",
    "--language",
    default="es",
    help="The language to translate into. One of (de, es, fr, it, pt). Default is es.",
)
parser.add_argument(
    "-p",
    "--location-points",
    default="36,33",
    help="The weather.gov API location points to get weather for. Default is 36,33. "
    "Visit https://api.weather.gov/points/{lat},{lon} to find location points "
    "for GPS coordinates",
)
parser.add_argument(
    "-e",
    "--period",
    default="current",
    help="The weather period to consider, current or next. Default is current.",
)
parser.add_argument(
    "-c",
    "--cached",
    action="store_true",
    help="Use the cached weather data from forecast.json instead of fetching from the server.",
)
args = parser.parse_args()
language_name_map = {
    "es": "spanish",
    "de": "german",
    "fr": "french",
    "it": "italian",
    "pt": "portuguese",
}

language_voice_map = {
    "es": "es_MX-claude-high.onnx",
    "de": "de_DE-kerstin-low.onnx",
    "fr": "fr_FR-upmc-medium.onnx",
    "it": "it_IT-paola-medium.onnx",
    "pt": "pt_BR-jeff-medium.onnx",
}
if args.language not in language_name_map.keys():  # pylint: disable=consider-iterating-dictionary
    raise ValueError(
        f"Invalid language {args.language}. Valid languages are {language_name_map.keys()}"
    )

if args.period.lower() not in {"current", "cur", "next"}:
    raise ValueError(
        f"Invalid period {args.period}. Valid periods are 'current', 'next'"
    )

replacements = {"mph": "miles per hour"}

# latlng_lookup_url = "https://api.weather.gov/points/{lat},{lon}"
location_points = args.location_points

if not args.cached:
    weather_data = requests.get(
        f"https://api.weather.gov/gridpoints/TOP/{location_points}/forecast", timeout=20
    ).json()
    print("Fetched weather...")

    with open("forecast.json", "w") as f:
        json.dump(weather_data, f)
else:
    weather_data = json.loads(Path("forecast.json").read_text())
    print("Read cached weather...")
period_index = 0
if args.period == "next":
    period_index = 1
elif args.period in {"cur", "current"}:
    period_index = 0

period = weather_data["properties"]["periods"][period_index]

english_weather = (
    f'Current Temperature is {period["temperature"]}{period["temperatureUnit"]}. '
)
english_weather += f'{period["name"]} {period["detailedForecast"]}'

for key, replacement in replacements.items():
    english_weather = english_weather.replace(key, replacement)

print(f"english_weather: {english_weather}")

print("Generating wardrobe suggestion...")
response: ChatResponse = chat(
    model="translator-smollm3",
    messages=[
        {
            "role": "system",
            "content": "You are a wardrobe assistant. Your job is to suggest some appropriate "
            "clothes attire for a person to wear based on the weather. You can include clothing items "
            "and accessories that are appropriate for the specified weather conditions. "
            "Use positive and re-affirming language. Do not output any explanations, "
            "only output the wardrobe suggestion. Do not summarize the weather."
            "The wardrobe suggestion output should be no more than 2 sentences.",
        },
        {
            "role": "user",
            "content": f"{english_weather}",
        },
    ],
)

print(response["message"]["content"])
# combine weather and wardrobe suggestion
english_weather += " " + response["message"]["content"]

print("Translating weather & wardrobe...")

language = language_name_map[args.language]
response: ChatResponse = chat(
    model="translator-smollm3",
    messages=[
        {
            "role": "system",
            "content": "You are a translation assistant. The user is going to give you a short passage in english, "
            f"please translate it to {language}. Output only the {language} translation of the input. "
            "Do not output explanations, notes, or anything else. If there is not an exact literal translation, "
            "just output the best fitting alternate word or phrase that you can. Do not explain anything, "
            f"only output the translation. All output should be in {language}",
        },
        {
            "role": "user",
            "content": f"{english_weather}",
        },
    ],
)
translated_weather = response["message"]["content"]
print(translated_weather)

print("Generating audio...")

shutil.rmtree("sound_files", ignore_errors=True)
os.mkdir("sound_files")

voice = PiperVoice.load(language_voice_map[args.language])
with wave.open("sound_files/weather_and_wardrobe.wav", "wb") as wav_file:
    voice.synthesize_wav(translated_weather, wav_file)

print("Audio generation complete...")
