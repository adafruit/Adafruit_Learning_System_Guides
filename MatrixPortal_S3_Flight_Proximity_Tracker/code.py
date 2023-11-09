# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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

quotes_url = "https://www.adafruit.com/api/quotes.php"

ICON_WIDTH = 26  # Adjust according to your actual icon width
TEXT_START_X = ICON_WIDTH + 4

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

with open("/ssl.com-root.pem", "rb") as certfile:
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
#font = bitmap_font.load_font("/tom-thumb.pcf")
font = terminalio.FONT
text_color = 0xFC6900  # e.g., Retro Orange
colors = [0xFC6900, 0xDD8000]

group = Group()
# Associate the RGB matrix with a Display
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# --- Icon Positioning ---
ICON_HEIGHT = 26  # Height of the icon
GAP_BETWEEN_ICONS = 12  # Gap between the icons
NUMBER_OF_ICONS = 2  # Number of icons to display
total_icons_height = (ICON_HEIGHT * NUMBER_OF_ICONS) + (GAP_BETWEEN_ICONS * (NUMBER_OF_ICONS - 1))

# Calculate the starting y-position for the first icon to center them vertically
start_y = (DISPLAY_HEIGHT - total_icons_height) // 2


 # Create icon group
icon_group = Group()


gap_between_lines = 12

display.show(icon_group)

def scroll_icons(icon_tile):
    icon_tile.x -= 1
    if icon_tile.x < -64:  # Assuming each icon is 64 pixels wide
        icon_tile.x = 128  # Reset position to the rightmost






# Function to scroll the icons
TEXT_RESET_X = 170


# Function to scroll objects
def scroll_text_labels(text_labels):
    for label in text_labels:
        label.x -= 1  # Move label left.
        if label.x < -256:  # If label has moved off screen.
            label.x = TEXT_RESET_X



seen_flight_numbers = set()  # To keep track of processed flight numbers

bounding_box = {
    "min_latitude": 40.962321,   # Southernmost latitude
    "max_latitude": 44.953469,   # Northernmost latitude
    "min_longitude": -111.045360, # Westernmost longitude
    "max_longitude": -104.046570, # Easternmost longitude
}

# curl -X GET "https://aeroapi.flightaware.com/aeroapi/flights/search?query=-latlong+%2244.953469+-111.045360+40.962321+-104.046577%22&max_pages=1" \
# -H "Accept: application/json; charset=UTF-8" \
# -H "x-apikey:  -AN API KEY-"

def degrees_to_cardinal(d):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = round(d / 45)
    return dirs[ix % 8]


def construct_query_string(params):
    return "&".join(f"{key}={value}" for key, value in params.items())

def update_flight_labels(flights_data):
    for i, flight in enumerate(flights_data[:4]):  # Update up to 4 flights
        flight_text = f"{flight['icao']} | {flight['country']} | {flight['altitude']} | {flight['direction']}"
        labels[i].text = flight_text  # Assuming you have a list of Label objects

# Call this function with fetched flight data


#anA5AXJkYlfC2SNgWghB27mkNO9RRaTI

def fetch_flight_data():
    print("Running fetch_flight_data")
    base_url = "https://aeroapi.flightaware.com/aeroapi/flights/search"
    params = {
        "query": f"-latlong+\"{bounding_box['min_latitude']}+{bounding_box['min_longitude']}+{bounding_box['max_latitude']}+{bounding_box['max_longitude']}\"",
        "max_pages": "1"
    }
    headers = {
        "Accept": "application/json; charset=UTF-8",
        "x-apikey": "anA5AXJkYlfC2SNgWghB27mkNO9RRaTI"  # Replace with your actual API key
    }
    full_url = f"{base_url}?{construct_query_string(params)}"
    response = requests.get(full_url, headers=headers)

    if response.status_code == 200:
        json_response = response.json()  # Parse JSON only once
        return process_flight_data(json_response)  # Process flights and return
    else:
        print(f"Request failed with status code {response.status_code}")
        if response.content:
            print(f"Response content: {response.content}")
        return []  # Return an empty list if the request failed

def process_flight_data(json_data):
    # Initialize an empty list to hold processed flight data
    processed_flights = []

    for flight in json_data.get('flights', []):
        # Use 'get' with default values to avoid KeyError
        flight_info = {
            'ident': flight.get('ident', 'N/A'),
            'ident_icao': flight.get('ident_icao', 'N/A'),
            'fa_flight_id': flight.get('fa_flight_id', 'N/A'),
            'actual_off': flight.get('actual_off', 'N/A'),
            'actual_on': flight.get('actual_on', 'N/A'),
            'origin_code': flight.get('origin', {}).get('code', 'Unknown'),
            'origin_city': flight.get('origin', {}).get('city', 'Unknown'),
            'origin_country': flight.get('origin', {}).get('country', 'Unknown'),
            'destination_code': flight.get('destination', {}).get('code', 'Unknown') if flight.get('destination') else 'Unknown',
            'destination_city': flight.get('destination', {}).get('city', 'Unknown') if flight.get('destination') else 'Unknown',
            'destination_country': flight.get('destination', {}).get('country', 'Unknown') if flight.get('destination') else 'Unknown',
            'altitude': flight.get('last_position', {}).get('altitude', 'N/A'),
            'groundspeed': flight.get('last_position', {}).get('groundspeed', 'N/A'),
            'heading': flight.get('last_position', {}).get('heading', 'N/A'),
            'latitude': flight.get('last_position', {}).get('latitude', 'N/A'),
            'longitude': flight.get('last_position', {}).get('longitude', 'N/A'),
            'timestamp': flight.get('last_position', {}).get('timestamp', 'N/A'),
            'aircraft_type': flight.get('aircraft_type', 'N/A'),
        }
        # Only add flight_info if the 'ident_icao' is present and not 'N/A'
        if flight_info['ident_icao'] != 'N/A':
            processed_flights.append(flight_info)

    return processed_flights


    
    
    
def create_text_labels(flight_data, display_group):
    text_labels = []
    for i, flight in enumerate(flight_data):
        y_position = i * gap_between_lines + 15

        # Since 'country' is not present, we'll use 'origin_city' and 'destination_code' instead
        # Construct the display text for each flight without 'country'
        
        origin_city = flight.get('origin_city', 'Unknown City')
        origin_country = flight.get('origin_country', 'Unknown Country')
        destination_city = flight.get('destination_city', 'Unknown City')
        destination_country = flight.get('destination_country', 'Unknown Country')

        # Format from and to locations with city and country
        from_location = f"{origin_city}, {origin_country}"
        to_location = f"{destination_city}, {destination_country}"

        # Construct the display text for each flight
        single_line_text = f"{flight['ident']} | From: {from_location} To: {to_location}"

        text_label = adafruit_display_text.label.Label(
            font,
            color=text_color,
            x=TEXT_START_X,
            y=y_position,
            text=single_line_text
        )
        display_group.append(text_label)
        text_labels.append(text_label)
    return text_labels


def create_icon_tilegrid(ident):
    airline_code = ident[:3].upper()  # Use the first three characters of 'ident'
    icon_path = f"/airline_logos/{airline_code}.bmp"
    try:
        icon_bitmap = OnDiskBitmap(open(icon_path, "rb"))
        icon_tilegrid = TileGrid(icon_bitmap, pixel_shader=icon_bitmap.pixel_shader, x=0, y=0)
        return icon_tilegrid
    except OSError:
        print(f"Icon for {airline_code} not found.")
        return None

# Update your display update function to include icon creation and text label setup
def update_display_with_flight_data(flight_data, icon_group, display_group):
    # Clear previous display items
    while len(display_group):
        display_group.pop()



    # Limit flight data to only 4 flights
    flight_data = flight_data[:4]

    # Load icons and create text labels for up to 4 flights
    for i, flight in enumerate(flight_data):
        y_position = i * gap_between_lines + 10

        # Load the icon dynamically
        icon_tilegrid = create_icon_tilegrid(flight['ident'])
        if icon_tilegrid:
            icon_tilegrid.y = y_position
            icon_group.append(icon_tilegrid)

    # Append the icon group to the main display group
    display_group.append(icon_group)

    # Create and append text labels next to the icons
    text_labels = create_text_labels(flight_data, display_group)

    # Show the updated group on the display
    display.show(display_group)
    return text_labels


# Initialize the main display group
main_group = Group()

# Initialize the icon group (this remains static on the display)
static_icon_group = Group()
    
    
text_label = adafruit_display_text.label.Label(font, text="Label 1", color=0xFFFFFF, x=DISPLAY_WIDTH, y=1)
text_label2 = adafruit_display_text.label.Label(font, text="Label 2", color=0xFFFFFF, x=DISPLAY_WIDTH, y=3)
text_label3 = adafruit_display_text.label.Label(font, text="Label 3", color=0xFFFFFF, x=DISPLAY_WIDTH, y=6)
text_label4 = adafruit_display_text.label.Label(font, text="Label 4", color=0xFFFFFF, x=DISPLAY_WIDTH, y=15)

# Add labels to a display group
group = displayio.Group()
group.append(text_label)
group.append(text_label2)
group.append(text_label3)
group.append(text_label4)

# Show the group
display.show(group)
    
flight_data = fetch_flight_data()

# Initialize text labels list
text_labels = []

# Check if we received any flight data
if flight_data:
    text_labels = update_display_with_flight_data(flight_data, static_icon_group, main_group)
    
    
while True:
    scroll_text_labels(text_labels)

    # Refresh the display
    display.refresh(minimum_frames_per_second=0)
    
time.sleep (120000)
