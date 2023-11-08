import board
import os
import ssl
import wifi
import time
import json
import math
import terminalio
import socketpool
import adafruit_requests
import displayio
import rgbmatrix
import framebufferio
import adafruit_display_text.label
import adafruit_json_stream as json_stream
from adafruit_bitmap_font import bitmap_font
from displayio import OnDiskBitmap, TileGrid, Group
from adafruit_matrixportal.matrixportal import MatrixPortal
import microcontroller


# Release any existing displays
displayio.release_displays()

# max - 40.702570, -73.832641
# min - 40.677529, -74.017174

# --- API Configuration ---
API_URL = "http://airlabs.co/api/v9/flights?api_key="
API_KEY = "f1880f2c-1a0e-4165-bbc7-7507cff6c936"
TEST_API = "http://opensky-network.org/api/states/all?lamin=40.696377&lomin=-73.940979&lamax=40.699356&lomax=-73.911090"

quotes_url = "https://www.adafruit.com/api/quotes.php"


THRESHOLD_DISTANCE = 150  # 5 miles

# font = bitmap_font.load_font("/tom-thumb.pcf")
font = terminalio.FONT
text_color = 0xFC6900  # e.g., Retro Orange
colors = [0xFC6900, 0xDD8000]


# --- Wi-Fi setup ---
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

# --- Networking setup ---
context = ssl.create_default_context()


with open("/www.flightaware.com.cer", "rb") as certfile:
    context.load_verify_locations(cadata=certfile.read())

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

# --- Matrix setup ---
DISPLAY_WIDTH = 192
DISPLAY_HEIGHT = 64
matrix = rgbmatrix.RGBMatrix(
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    bit_depth=2,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
        board.MTX_ADDRE,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    tile=1,
    serpentine=True,
    doublebuffer=False,
)


# --- Drawing setup ---
group = Group()
# Create icon group


# Associate the RGB matrix with a Display
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)


# display.show(icon_group)


def degrees_to_cardinal(d):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = round(d / 45)
    return dirs[ix % 8]


seen_flight_numbers = set()  # To keep track of processed flight numbers

user_lat = 40.68406917331829
user_lng = -73.92215541728851
user_location = (user_lat, user_lng)


bounding_box = {
    "min_latitude": 40.7128,
    "max_latitude": 40.8138,
    "min_longitude": -74.0160,
    "max_longitude": -73.9160,
}


api_url = "https://aeroapi.flightaware.com/aeroapi/flights/search"
username = "UserName"
api_key = "API_KEY"

# Use CircuitPython base64 library for encoding
headers = {"x-apikey": api_key}

def construct_query_string(params):
    return "&".join(f"{key}={value}" for key, value in params.items())



def fetch_flight_data():
    base_url = "https://aeroapi.flightaware.com/aeroapi/flights/search"
    params = {
        "query": f"-latlong+\"{bounding_box['min_latitude']}+{bounding_box['min_longitude']}+{bounding_box['max_latitude']}+{bounding_box['max_longitude']}\"",
        "max_pages": "1"
    }
    headers = {
        "Accept": "application/json; charset=UTF-8",
        "x-apikey": "API_KEY"
    }

    # Construct the full URL with the query string
    full_url = f"{base_url}?{construct_query_string(params)}"

    # Use the requests object that was initialized with a session
    response = requests.get(full_url, headers=headers)

   if response.status_code == 200:
        flights = response.json()['flights']
        for flight in flights:
            print("Flight Properties:")
            print(f"Ident: {flight.get('ident', 'N/A')}")
            print(f"FA Flight ID: {flight.get('fa_flight_id', 'N/A')}")
            print(f"Origin: {flight.get('origin', {}).get('code', 'N/A')}")
            print(f"Destination: {flight.get('destination', {}).get('code', 'N/A')}")
            print(f"Altitude: {flight.get('last_position', {}).get('altitude', 'N/A')}00 ft")
            print(f"Groundspeed: {flight.get('last_position', {}).get('groundspeed', 'N/A')} knots")
            print(f"Heading: {flight.get('last_position', {}).get('heading', 'N/A')}")
            print(f"Latitude: {flight.get('last_position', {}).get('latitude', 'N/A')}")
            print(f"Longitude: {flight.get('last_position', {}).get('longitude', 'N/A')}")
            print(f"Timestamp: {flight.get('last_position', {}).get('timestamp', 'N/A')}")
            print("------")
            # Print only one flight's properties for brevity; remove the break to print all
            break
    else:
        print(f"Request failed with status code {response.status_code}")

def requestTest():
    try:
        #  pings adafruit quotes
        print("Fetching text from %s" % quotes_url)
        #  gets the quote from adafruit quotes
        response = requests.get(quotes_url)
        print("-" * 40)
        #  prints the response to the REPL
        print("Text Response: ", response.text)
        print("-" * 40)
        response.close()
        #  delays for 1 minute
        time.sleep(60)
    # pylint: disable=broad-except
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()

while True:
    fetch_flight_data()
