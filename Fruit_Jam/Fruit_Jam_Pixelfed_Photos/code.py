# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import gc
import os
import json
import random
import time

import board
import busio
from digitalio import DigitalInOut
from displayio import TileGrid, Group, OnDiskBitmap
import supervisor

import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_requests

# what kind of images to search for
search_tag = "cats"

# pixelfed search API URL
URL = f"https://pixelfed.social/api/v2/discover/tag?hashtag={search_tag}"

# small screen size
request_display_config(320, 240)
display = supervisor.runtime.display

# Get WiFi details, ensure these are setup in settings.toml
ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# Get AIO details, ensure these are setup in settings.toml
AIO_USERNAME = os.getenv("ADAFRUIT_AIO_USERNAME")
AIO_KEY = os.getenv("ADAFRUIT_AIO_KEY")

# AIO image converter URL template
IMAGE_CONVERTER_SERVICE = (
    f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/integrations/image-formatter?"
    f"x-aio-key={AIO_KEY}&width={display.width}&height={display.height}&output=BMP16&url=%s"
)

# Main group to hold visible elements
main_group = Group()
display.root_group = main_group

# try to load the previously downloaded image
try:
    img_bmp = OnDiskBitmap("/saves/downloaded_img.bmp")
    img_tg = TileGrid(img_bmp, pixel_shader=img_bmp.pixel_shader)
    main_group.append(img_tg)
except (ValueError, RuntimeError, OSError):
    img_tg = None

# Setup WIFI
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
radio = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

print("Connecting to AP...")
while not radio.is_connected:
    try:
        radio.connect_AP(ssid, password)
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(radio.ap_info.ssid, "utf-8"), "\tRSSI:", radio.ap_info.rssi)

# Initialize a requests session
pool = adafruit_connection_manager.get_radio_socketpool(radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)
requests = adafruit_requests.Session(pool, ssl_context)


def fetch_pixelfed_search():
    """
    Fetch search data from the pixelfed JSON API and cache the results
    in /saves/pixelfed.json

    :return: None
    """
    with requests.get(URL) as search_response:
        print(f"pixelfeld search status code: {search_response.status_code}")
        resp_data = search_response.text
        if search_response.status_code == 200:
            with open("/saves/pixelfed.json", "w") as cache_file:
                cache_file.write(resp_data)
                print("wrote search results to /saves/pixelfed.json")


def build_img_url_list():
    """
    Extract a list of URLs for images from the cached search data in /saves/pixelfed.json
    :return: The list of URLs
    """
    image_urls_to_show = []
    for i in range(len(search_results_obj["tags"])):
        post_obj = search_results_obj["tags"][i]
        for attachment in post_obj["status"]["media_attachments"]:
            if attachment["is_nsfw"] == 0:
                _img_url = attachment["preview_url"]
                image_urls_to_show.append(_img_url)

    # shuffle the order of the final list
    randomized_image_urls = []
    while len(image_urls_to_show) > 0:
        random_image_url = random.choice(image_urls_to_show)
        image_urls_to_show.remove(random_image_url)
        randomized_image_urls.append(random_image_url)
    return randomized_image_urls


# variable to store a timestamp of when we last searched
last_search_time = 0

# try to read cached search data
try:
    with open("/saves/pixelfed.json", "r") as cached_search_data:
        search_results_obj = json.loads(cached_search_data.read())

except OSError:  # if there is no cached search data
    # fetch search data now
    fetch_pixelfed_search()
    # update the timestamp
    last_search_time = time.monotonic()
    # load the fetched data from the cache file
    with open("/saves/pixelfed.json", "r") as cached_search_data:
        search_results_obj = json.loads(cached_search_data.read())

# get the list of images to show
images = build_img_url_list()

# main loop
while True:
    # loop over all images in the list
    for img_url in images:
        # prepare the converter URL for the current image
        converter_url = IMAGE_CONVERTER_SERVICE.replace("%s", img_url)
        print("Fetching converted img")
        # attempt to download the converted image
        with requests.get(converter_url) as response:
            print("conversion status code: ", response.status_code)
            # if the conversion was successful
            if response.status_code == 200:
                # save the image CPSAVES
                with open("/saves/downloaded_img.bmp", "wb") as outfile:
                    for chunk in response.iter_content(chunk_size=8192):
                        outfile.write(chunk)
                    img_download_success = True

            # if the conversion was not successful
            elif response.status_code == 429:  # rate limit error
                print("Img converter rate limit")
                img_download_success = False
                time.sleep(60)
            else:
                print(response.content)
                img_download_success = False
                time.sleep(60)

        if img_download_success:
            print("Loading img")
            # load and show the downloaded image file
            try:
                img_bmp = OnDiskBitmap("/saves/downloaded_img.bmp")
                if img_tg in main_group:
                    main_group.remove(img_tg)
                gc.collect()
                img_tg = TileGrid(img_bmp, pixel_shader=img_bmp.pixel_shader)
                main_group.append(img_tg)
            except (ValueError, RuntimeError, OSError):
                pass

            # wait for 4 minutes
            time.sleep(60 * 4)

        # if it has been at least an hour since the last search time
        if time.monotonic() - last_search_time > (60 * 60):
            # fetch new search data and load the list of images from it
            fetch_pixelfed_search()
            last_search_time = time.monotonic()
            with open("/saves/pixelfed.json", "r") as cached_search_data:
                search_results_obj = json.loads(cached_search_data.read())
            images = build_img_url_list()
