import time
import board
import busio
import random
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_requests as requests
import adafruit_fancyled.adafruit_fancyled as fancy

print("ESP32 Open Weather API demo")

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = "Manhattan, US"

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.openweathermap.org/data/2.5/weather?q="+LOCATION
DATA_SOURCE += "&appid="+secrets['openweather_token']

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2) # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
pixels = neopixel.NeoPixel(board.D2, 16, brightness=1.0, auto_write=False)
pixels.fill(0x050505)
pixels.show()

# clouds palette
cloudy_palette = [fancy.CRGB(1.0, 1.0, 1.0), # White
                  fancy.CRGB(0.5, 0.5, 0.5), # gray
                  fancy.CRGB(0.5, 0.5, 1.0)] # blue-gray
# sunny palette
sunny_palette = [fancy.CRGB(1.0, 1.0, 1.0), # White
                 fancy.CRGB(1.0, 1.0, 0.0),# Yellow
                 fancy.CRGB(1.0, 0.5, 0.0),] # Orange
# thunderstorm palette
thunder_palette = [fancy.CRGB(0.0, 0.0, 1.0), # blue
                   fancy.CRGB(0.5, 0.5, 0.5), # gray
                   fancy.CRGB(0.5, 0.5, 1.0)] # blue-gray
last_thunder_bolt = None

palette = None  # current palette
pal_offset = 0  # Positional offset into color palette to get it to 'spin'
levels = (0.25, 0.3, 0.15)  # Color balance / brightness for gamma function
raining = False
thundering = False

weather_refresh = None
weather_type = None
while True:
    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            response = wifi.get(DATA_SOURCE).json()
            print("Response is", response)
            weather_type = response['weather'][0]['main']
            weather_type = 'Thunderstorm' # manually adjust weather type for testing!

            print(weather_type) # See https://openweathermap.org/weather-conditions
            # default to no rain or thunder
            raining = thundering = False
            if weather_type == 'Clouds':
                palette = cloudy_palette
            if weather_type == 'Rain':
                palette = cloudy_palette
                raining = True
            if weather_type == 'Sunny':
                palette = sunny_palette
            if weather_type == 'Thunderstorm':
                palette = thunder_palette
                raining = thundering = True
                # pick next thunderbolt time now
                next_bolt_time = time.monotonic() + random.randint(1, 5)
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            time.sleep(5)
            continue

    if palette:
        for i in range(len(pixels)):
            color = fancy.palette_lookup(palette, pal_offset + i / len(pixels))
            color = fancy.gamma_adjust(color, brightness=levels)
            pixels[i] = color.pack()
        pixels.show()
        pal_offset += 0.01  # Bigger number = faster spin

    if raining:
        # don't have a droplet every time
        if (random.randint(0, 25) == 0):  # 1 out of 25 times
            pixels[random.randint(0, len(pixels)-1)] = 0xFFFFFF  # make a random pixel white
            pixels.show()

    # if its time for a thunderbolt
    if thundering and (time.monotonic() > next_bolt_time):
        print("Ka Bam!")
        # fill pixels white, delay, a few times
        for i in range(random.randint(1, 3)):  # up to 3 times...
            pixels.fill(0xFFFFFF) # bright white!
            pixels.show()
            time.sleep(random.uniform(0.01, 0.2)) # pause
            pixels.fill(0x0F0F0F) # gray
            pixels.show()
            time.sleep(random.uniform(0.01, 0.3)) # pause
        # pick next thunderbolt time now
        next_bolt_time = time.monotonic() + random.randint(5, 15) # between 5 and 15 s

