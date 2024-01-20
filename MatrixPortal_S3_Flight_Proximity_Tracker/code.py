# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import os
import ssl
import time
import board
import wifi
import terminalio
import socketpool
import adafruit_requests
import displayio
import rgbmatrix
import framebufferio
import adafruit_display_text.label
from displayio import OnDiskBitmap, TileGrid, Group

# Release any existing displays
displayio.release_displays()

# --- Matrix Properties ---
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# 432 Minutes - 7.2 Hours
NETWORK_CALL_INTERVAL = 25920

# --- Icon Properties ---
ICON_WIDTH = 26  # Width of the icons
ICON_HEIGHT = 26  # Height of the icons
# Calculate the gap between icons
gap_between_icons = 5

GAP_BETWEEN_ICONS = 15  # Gap between the icons
NUMBER_OF_ICONS = 2  # Number of icons to display
PLACEHOLDER_ICON_PATH = "/airline_logos/placeholder.bmp"

# --- Text Properties ---
TEXT_START_X = ICON_WIDTH + 4
TEXT_RESET_X = 170
FONT = terminalio.FONT
TEXT_COLOR = 0x22FF00  # e.g., Green

# Initialize the main display group
main_group = Group()

# Initialize the icon group (this remains static on the display)
static_icon_group = Group()

# Sample Bounding Box
bounding_box = {
    "min_latitude": 40.633013,  # Southernmost latitude
    "max_latitude": 44.953469,  # Northernmost latitude
    "min_longitude": -111.045360,  # Westernmost longitude
    "max_longitude": -104.046570,  # Easternmost longitude
}

# --- Matrix setup ---
BIT_DEPTH = 2
matrix = rgbmatrix.RGBMatrix(
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    bit_depth=BIT_DEPTH,
    rgb_pins=[
        board.MTX_B1,
        board.MTX_G1,
        board.MTX_R1,
        board.MTX_B2,
        board.MTX_G2,
        board.MTX_R2,
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
    doublebuffer=True,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

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

# --- Icon Positioning ---
total_icons_height = (ICON_HEIGHT * NUMBER_OF_ICONS) + (
    GAP_BETWEEN_ICONS * (NUMBER_OF_ICONS - 1)
)

# Function to scroll objects
def scroll_text_labels(text_labels):
    for label in text_labels:
        label.x -= 1  # Move label left.
        if label.x < -300:  # If label has moved off screen.
            label.x = TEXT_RESET_X


def construct_query_string(params):
    return "&".join(f"{key}={value}" for key, value in params.items())

def fetch_flight_data():
    print("Running fetch_flight_data")

    base_url = "https://aeroapi.flightaware.com/aeroapi/flights/search"
    query_prefix = "-latlong+\""
    query_suffix = (
        str(bounding_box['min_latitude']) + "+" +
        str(bounding_box['min_longitude']) + "+" +
        str(bounding_box['max_latitude']) + "+" +
        str(bounding_box['max_longitude']) + "\"")
    query = query_prefix + query_suffix

    params = {
        "query": query,
        "max_pages": "1",}


    headers = {
        "Accept": "application/json; charset=UTF-8",
        "x-apikey": os.getenv("AERO_API_KEY"),  # Replace with your actual API key
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
        return []

def process_flight_data(json_data):
    # Initialize an empty list to hold processed flight data
    processed_flights = []

    for flight in json_data.get("flights", []):
        # Use 'get' with default values to avoid KeyError
        flight_info = {
            "ident": flight.get("ident", "N/A"),
            "ident_icao": flight.get("ident_icao", "N/A"),
            "fa_flight_id": flight.get("fa_flight_id", "N/A"),
            "actual_off": flight.get("actual_off", "N/A"),
            "actual_on": flight.get("actual_on", "N/A"),
            "origin_code": flight.get("origin", {}).get("code", "UnknownA"),
            "origin_city": flight.get("origin", {}).get("city", "UnknownB"),
            "origin_country": flight.get("origin", {}).get("country", "UnknownC"),
            "destination_code": flight.get("destination", {}).get("code", "UnknownD")
            if flight.get("destination")
            else "UnknownE",
            "destination_city": flight.get("destination", {}).get("city", "UnknownH")
            if flight.get("destination")
            else "Unknown Destination",
            "destination_country": flight.get("destination", {}).get(
                "country", "UnknownZ"
            )
            if flight.get("destination")
            else "UnknownG",
            "altitude": flight.get("last_position", {}).get("altitude", "N/A"),
            "groundspeed": flight.get("last_position", {}).get("groundspeed", "N/A"),
            "heading": flight.get("last_position", {}).get("heading", "N/A"),
            "latitude": flight.get("last_position", {}).get("latitude", "N/A"),
            "longitude": flight.get("last_position", {}).get("longitude", "N/A"),
            "timestamp": flight.get("last_position", {}).get("timestamp", "N/A"),
            "aircraft_type": flight.get("aircraft_type", "N/A"),
        }
        # Only add flight_info if the 'ident_icao' is present and not 'N/A'
        if flight_info["ident_icao"] != "N/A":
            processed_flights.append(flight_info)

    return processed_flights


def create_text_labels(flight_data, Ypositions):
    local_text_labels = []
    for i, flight in enumerate(flight_data):
        y_position = Ypositions[i] + GAP_BETWEEN_ICONS

        # Since 'country' is not present, use 'origin_city' and 'destination_city' instead
        origin_city = flight.get("origin_city", "Unknown City")
        destination_city = flight.get("destination_city", "Unknown City")

        # Construct the display text for each flight
        single_line_text = (
            f"{flight['ident']} | From: {origin_city} To: {destination_city}"
        )

        text_label = adafruit_display_text.label.Label(
            FONT, color=TEXT_COLOR, x=TEXT_START_X, y=y_position, text=single_line_text
        )
        local_text_labels.append(text_label)
    return local_text_labels



def create_icon_tilegrid(ident):
    airline_code = ident[:3].upper()  # Use the first three characters of 'ident'
    icon_path = f"/airline_logos/{airline_code}.bmp"

    try:
        file = open(icon_path, "rb")
        icon_bitmap = OnDiskBitmap(file)
    except OSError:
        print(f"Icon for {airline_code} not found. Using placeholder.")
        file = open(PLACEHOLDER_ICON_PATH, "rb")
        icon_bitmap = OnDiskBitmap(file)

    icon_tilegrid = TileGrid(icon_bitmap, pixel_shader=icon_bitmap.pixel_shader, x=0, y=0)
    return icon_tilegrid


def update_display_with_flight_data(flight_data, icon_group, display_group):
    # Clear previous display items
    while len(display_group):
        display_group.pop()

    # Clear previous icon items
    while len(icon_group):
        icon_group.pop()

    # Limit flight data to the adjusted number of icons
    flight_data = flight_data[:NUMBER_OF_ICONS]

    # Calculate the y position for each icon
    y_positions = [
        gap_between_icons + (ICON_HEIGHT + gap_between_icons) * i
        for i in range(NUMBER_OF_ICONS)
    ]

    # Create text labels for up to NUMBER_OF_ICONS flights
    text_labels = create_text_labels(flight_data, y_positions)

    # Add text labels to the display group first so they are behind icons
    for label in text_labels:
        display_group.append(label)

    # Load icons and create icon tilegrids for up to NUMBER_OF_ICONS flights
    for i, flight in enumerate(flight_data):
        # Calculate the y position for each icon
        y_position = y_positions[i]

        # Load the icon dynamically
        icon_tilegrid = create_icon_tilegrid(flight["ident"])
        if icon_tilegrid:
            icon_tilegrid.y = y_position
            icon_group.append(icon_tilegrid)

    # Add the icon group to the main display group after text labels
    display_group.append(icon_group)

    # Show the updated group on the display
    display.show(display_group)
    display.refresh()
    return text_labels



def display_no_flights():
    # Clear the previous group content
    while len(main_group):
        main_group.pop()

    # Create a label for "Looking for flights..."
    looking_label = adafruit_display_text.label.Label(
        FONT, color=TEXT_COLOR, text="LOOKING FOR FLIGHTS", x=8, y=DISPLAY_HEIGHT // 2
    )
    main_group.append(looking_label)

    # Update the display with the new group
    display.show(main_group)
    display.refresh()


display_no_flights()

flight_json_response = fetch_flight_data()

# Check if we received any flight data
if flight_json_response:
    flight_data_labels = update_display_with_flight_data(
        flight_json_response, static_icon_group, main_group
    )

last_network_call_time = time.monotonic()


while True:
    # Scroll the text labels
    scroll_text_labels(flight_data_labels)
    # Refresh the display
    display.refresh(minimum_frames_per_second=0)
    current_time = time.monotonic()

    # Check if NETWORK_CALL_INTERVAL seconds have passed
    if (current_time - last_network_call_time) >= NETWORK_CALL_INTERVAL:
        print("Fetching new flight data...")
        new_flight_data = fetch_flight_data()

        if new_flight_data:
            # If flight data is found, update the display with it
            new_text_labels = update_display_with_flight_data(
                new_flight_data, static_icon_group, main_group
            )
        else:
            # If no flight data is found, display the "Looking for flights..." message
            display_no_flights()

        # Reset the last network call time
        last_network_call_time = current_time

        # Sleep for a short period to prevent maxing out your CPU
        time.sleep(1)  # Sleep for 1 second
