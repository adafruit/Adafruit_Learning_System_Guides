# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Aug 3rd, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/2fabba2b-3f17-4ab6-a4d9-58206a3b9916

# process() function originally written by Phil B. for Adafruit Industries
# https://raw.githubusercontent.com/adafruit/Adafruit_Media_Converters/master/protomatter_dither.py

# Based on Airline-Logos Scraper by Cal Stephens, 2017 MIT License
# https://github.com/calda/Airline-Logos

import os
import math
import requests
from PIL import Image

# directory to match CircuitPython code folder names
bitmap_directories = "airline_logos"

img_width = 32
img_height = 32

chars = ["A", "B", "C", "D", "E",
     "F", "G", "H", "I", "J", "K", "L",
     "M", "N", "O", "P", "Q", "R", "S",
     "T", "U", "V", "W", "X", "Y", "Z",
     "0", "1", "2", "3", "4", "5", "6",
     "7", "8", "9"]
# pylint: disable=inconsistent-return-statements
def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for _ in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.1f}"
        num /= 1024.0

def file_size(file_path):
    """
    this function will return the file size
    """
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        print(file_info.st_size)
        return file_info.st_size

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
base_dir = 'airline_logos'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

# Loop through each combo of characters to find all of the airlines
# this takes a while..
for f in range(len(chars)):
    for s in range(len(chars)):
        # Set the URL for IATA
        # pylint: disable=line-too-long
        url = f"https://content.r9cdn.net/rimg/provider-logos/airlines/v/{chars[f]}{chars[s]}.png?crop=false&width=300&height=300"
        print(f"Downloading logo for {chars[f]}{chars[s]} from IATA...")

        img_path_png = os.path.join(base_dir, f"{chars[f]}{chars[s]}.png")
        response = requests.get(url, stream=True, timeout=60)
        try:
            with open(img_path_png, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)

            z = os.stat(img_path_png)
            print(z.st_size)
            if z.st_size <= 2506:
                print("deleting empty file")
                os.remove(img_path_png)
            else:
                with Image.open(img_path_png) as the_img:
                    img_resized = the_img.resize((img_width, img_height))
                    img_resized.save(img_path_png)
                    process(img_path_png)

                    # Delete the original .png file
                os.remove(img_path_png)
        except Exception: # pylint: disable=broad-except
            print("file is missing, moving on..")
        for t in range(len(chars)):
            # Set the URL for ICAO
            # pylint: disable=line-too-long
            url_1 = f"https://flightaware.com/images/airline_logos/90p/{chars[f]}{chars[s]}{chars[t]}.png"

            print(f"Downloading logo for {chars[f]}{chars[s]}{chars[t]} from ICAO...")

            img_path_png_0 = os.path.join(base_dir, f"{chars[f]}{chars[s]}{chars[t]}.png")
            response_1 = requests.get(url_1, stream=True, timeout=60)
            try:
                with open(img_path_png_0, 'wb') as file:
                    for chunk in response_1.iter_content(chunk_size=1024):
                        file.write(chunk)

                z = os.stat(img_path_png_0)
                print(z.st_size)
                if z.st_size <= 2506:
                    print("deleting empty file")
                    os.remove(img_path_png_0)
                else:
                    with Image.open(img_path_png_0) as the_img:
                        img_resized = the_img.resize((img_width, img_height))
                        img_resized.save(img_path_png_0)
                        process(img_path_png_0)

                    # Delete the original .png file
                    os.remove(img_path_png_0)
            except Exception: # pylint: disable=broad-except
                print("file is missing, moving on..")
