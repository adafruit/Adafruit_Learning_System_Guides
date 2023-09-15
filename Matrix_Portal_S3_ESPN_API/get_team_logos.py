# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Aug 3rd, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/2fabba2b-3f17-4ab6-a4d9-58206a3b9916

# process() function originally written by Phil B. for Adafruit Industries
# https://raw.githubusercontent.com/adafruit/Adafruit_Media_Converters/master/protomatter_dither.py

import os
import math
import requests
from PIL import Image

# the name of the sports you want to follow
sport_names = ["football", "baseball", "soccer", "hockey", "basketball"]
# the name of the corresponding leages you want to follow
sport_leagues = ["nfl", "mlb", "usa.1", "nhl", "nba"]
# directory to match CircuitPython code folder names
bitmap_directories = ["team0_logos", "team1_logos", "team2_logos", "team3_logos", "team4_logos"]

# Constants and function for image processing
GAMMA = 2.6

PASSTHROUGH = ((0, 0, 0),
               (255, 0, 0),
               (255, 255, 0),
               (0, 255, 0),
               (0, 255, 255),
               (0, 0, 255),
               (255, 0, 255),
               (255, 255, 255))

def process(filename, output_8_bit=True, passthrough=PASSTHROUGH):
    """Given a color image filename, load image and apply gamma correction
       and error-diffusion dithering while quantizing to 565 color
       resolution. If output_8_bit is True, image is reduced to 8-bit
       paletted mode after quantization/dithering. If passthrough (a list
       of 3-tuple RGB values) is provided, dithering won't be applied to
       colors in the provided list, they'll be quantized only (allows areas
       of the image to remain clean and dither-free). 
    """
    img = Image.open(filename).convert('RGB')
    err_next_pixel = (0, 0, 0)
    err_next_row = [(0, 0, 0) for _ in range(img.size[0])]
    for row in range(img.size[1]):
        for column in range(img.size[0]):
            pixel = img.getpixel((column, row))
            want = (math.pow(pixel[0] / 255.0, GAMMA) * 31.0,
                    math.pow(pixel[1] / 255.0, GAMMA) * 63.0,
                    math.pow(pixel[2] / 255.0, GAMMA) * 31.0)
            if pixel in passthrough:
                got = (pixel[0] >> 3,
                       pixel[1] >> 2,
                       pixel[2] >> 3)
            else:
                got = (min(max(int(err_next_pixel[0] * 0.5 +
                                   err_next_row[column][0] * 0.25 +
                                   want[0] + 0.5), 0), 31),
                       min(max(int(err_next_pixel[1] * 0.5 +
                                   err_next_row[column][1] * 0.25 +
                                   want[1] + 0.5), 0), 63),
                       min(max(int(err_next_pixel[2] * 0.5 +
                                   err_next_row[column][2] * 0.25 +
                                   want[2] + 0.5), 0), 31))
            err_next_pixel = (want[0] - got[0],
                              want[1] - got[1],
                              want[2] - got[2])
            err_next_row[column] = err_next_pixel
            rgb565 = ((got[0] << 3) | (got[0] >> 2),
                      (got[1] << 2) | (got[1] >> 4),
                      (got[2] << 3) | (got[2] >> 2))
            img.putpixel((column, row), rgb565)

    if output_8_bit:
        img = img.convert('P', palette=Image.ADAPTIVE)

    img.save(filename.split('.')[0] + '.bmp')

# Create a base directory to store the logos if it doesn't exist
base_dir = 'sport_logos'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

# Loop through each league to get the teams
for i in range(len(sport_leagues)):
    sport = sport_names[i]
    league = sport_leagues[i]

    # Create a directory for the current sport if it doesn't exist
    sport_dir = os.path.join(base_dir, bitmap_directories[i])
    if not os.path.exists(sport_dir):
        os.makedirs(sport_dir)

    # Set the URL for the JSON file for the current league
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"

    # Fetch the JSON data
    response = requests.get(url)
    data = response.json()

    # Extract team data
    teams = data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', [])

    # Download, process, resize, and save each logo
    for team in teams:
        abbreviation = team['team']['abbreviation']
        logo_url = team['team']['logos'][0]['href']

        print(f"Downloading logo for {abbreviation} from {league}...")

        img_path_png = os.path.join(sport_dir, f"{abbreviation}.png")
        response = requests.get(logo_url, stream=True)
        with open(img_path_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        # Open, resize, and save the image with PIL
        with Image.open(img_path_png) as the_img:
            img_resized = the_img.resize((32, 32))
            img_resized.save(img_path_png)
            process(img_path_png)

        # Delete the original .png file
        os.remove(img_path_png)

print("All logos have been downloaded, processed, and resized!")
