# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from os import getenv
import time
import random
import audioio
import audiocore
import board
import busio
from digitalio import DigitalInOut
import digitalio
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_fancyled.adafruit_fancyled as fancy

print("ESP32 Open Weather API demo")

button = digitalio.DigitalInOut(board.A1)
button.switch_to_input(pull=digitalio.Pull.UP)

with open("sound/Rain.wav", "rb") as wave_file:
    wave = audiocore.WaveFile(wave_file)
audio = audioio.AudioOut(board.A0)

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = getenv('timezone')

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.openweathermap.org/data/2.5/weather?q="+LOCATION
DATA_SOURCE += "&appid="+getenv('openweather_token')

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)  # Uncomment  for Most Boards
wifi = adafruit_esp32spi_wifimanager.WiFiManager(esp, ssid, password, status_pixel=status_pixel)
pixels = neopixel.NeoPixel(board.D2, 150, brightness=1.0, auto_write=False)
pixels.fill(0x050505)
pixels.show()

# clouds palette
cloudy_palette = [fancy.CRGB(1.0, 1.0, 1.0),  # White
                  fancy.CRGB(0.5, 0.5, 0.5),  # gray
                  fancy.CRGB(0.5, 0.5, 1.0)]  # blue-gray
# sunny palette
sunny_palette = [fancy.CRGB(1.0, 1.0, 1.0),  # White
                 fancy.CRGB(1.0, 1.0, 0.0),  # Yellow
                 fancy.CRGB(1.0, 0.5, 0.0), ]  # Orange
# thunderstorm palette
thunder_palette = [fancy.CRGB(0.0, 0.0, 1.0),  # blue
                   fancy.CRGB(0.5, 0.5, 0.5),  # gray
                   fancy.CRGB(0.5, 0.5, 1.0)]  # blue-gray
last_thunder_bolt = None

palette = None  # current palette
pal_offset = 0  # Positional offset into color palette to get it to 'spin'
levels = (0.25, 0.3, 0.15)  # Color balance / brightness for gamma function
raining = False
snowing = False
thundering = False
has_sound = False

weather_refresh = None
weather_type = None
button_mode = 4
button_select = False

cloud_on = True

while True:
    if not button.value:
        button_mode = button_mode + 1
        print("Button Pressed")
        if button_mode > 4:
            button_mode = 0
        print("Mode is:", button_mode)
        pressed_time = time.monotonic()
        button_select = True
        weather_refresh = None
        while not button.value:  # Debounce
            audio.stop()
            if (time.monotonic() - pressed_time) > 4:
                print("Turning OFF")
                cloud_on = False
                pixels.fill(0x000000)  # bright white!
                pixels.show()
                while not cloud_on:
                    while not button.value:  # Debounce
                        pass
                    if not button.value:
                        pressed_time = time.monotonic()
                        print("Button Pressed")
                        cloud_on = True
                        button_select = False
                        weather_refresh = None

            if button_mode == 0:
                weather_type = 'Sunny'
            if button_mode == 1:
                weather_type = 'Clouds'
            if button_mode == 2:
                weather_type = 'Rain'
            if button_mode == 3:
                weather_type = 'Thunderstorm'
            if button_mode == 4:
                weather_type = 'Snow'

    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            if not button_select:
                response = wifi.get(DATA_SOURCE).json()
                print("Response is", response)
                weather_type = response['weather'][0]['main']
                if weather_type == 'Clear':
                    weather_type = 'Sunny'
                print(weather_type)  # See https://openweathermap.org/weather-conditions
            # default to no rain or thunder
            raining = snowing = thundering = has_sound = False
            if weather_type == 'Sunny':
                palette = sunny_palette
                with open("sound/Clear.wav", "rb") as wave_file:
                    wave = audiocore.WaveFile(wave_file)
                has_sound = True
            if weather_type == 'Clouds':
                palette = cloudy_palette
                with open("sound/Clouds.wav", "rb") as wave_file:
                    wave = audiocore.WaveFile(wave_file)
                has_sound = True
            if weather_type == 'Rain':
                palette = cloudy_palette
                with open("sound/Rain.wav", "rb") as wave_file:
                    wave = audiocore.WaveFile(wave_file)
                raining = True
                has_sound = True
            if weather_type == 'Thunderstorm':
                palette = thunder_palette
                raining = thundering = True
                has_sound = True
                # pick next thunderbolt time now
                next_bolt_time = time.monotonic() + random.randint(1, 5)
            if weather_type == 'Snow':
                palette = cloudy_palette
                with open("sound/Snow.wav", "rb") as wave_file:
                    wave = audiocore.WaveFile(wave_file)
                snowing = True
                has_sound = True
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            time.sleep(5)
            continue

    if not audio.playing and has_sound:
        if not thundering:
            audio.play(wave)

    if palette:
        for i in range(len(pixels)):
            color = fancy.palette_lookup(palette, pal_offset + i / len(pixels))
            color = fancy.gamma_adjust(color, brightness=levels)
            pixels[i] = color.pack()
        pixels.show()
        pal_offset += 0.01  # Bigger number = faster spin

    if raining:
        # don't have a droplet every time
        for i in range(random.randint(1, 5)):  # up to 3 times...
            pixels[random.randint(0, len(pixels)-1)] = 0x0000FF  # make a random pixel Blue
        pixels.show()

    if snowing:
        # don't have a droplet every time
        for i in range(random.randint(1, 5)):  # up to 3 times...
            pixels[random.randint(0, len(pixels)-1)] = 0xFFFFFF  # make a random pixel white
        pixels.show()

    # if its time for a thunderbolt
    if thundering and (time.monotonic() > next_bolt_time):
        print("Ka Bam!")
        # fill pixels white, delay, a few times
        for i in range(random.randint(1, 3)):  # up to 3 times...
            pixels.fill(0xFFFFFF)  # bright white!
            pixels.show()
            time.sleep(random.uniform(0.01, 0.2))  # pause
            pixels.fill(0x0F0F0F)  # gray
            pixels.show()
            time.sleep(random.uniform(0.01, 0.3))  # pause
        # pick next thunderbolt time now
        Thunder = random.randint(0, 2)
        if Thunder == 0:
            wave_filename = "sound/Thunderstorm0.wav"
        elif Thunder == 1:
            wave_filename = "sound/Thunderstorm1.wav"
        elif Thunder == 2:
            wave_filename = "sound/Thunderstorm2.wav"
        if wave_filename:
            with open(wave_filename, "rb") as wave_file:
                wave = audiocore.WaveFile(wave_file)
            audio.play(wave)
        next_bolt_time = time.monotonic() + random.randint(5, 15)  # between 5 and 15 s
