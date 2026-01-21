# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
MagTag ePaper Camera Display - receives and displays images from Adafruit IO
Optimized for battery operation with deep sleep between checks
"""

import binascii
import gc
import os
import ssl
import time
import traceback
from io import BytesIO

import adafruit_imageload
import adafruit_requests
import alarm
import displayio
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_magtag.magtag import MagTag

# ============ USER CONFIGURATION ============
# Sleep interval in seconds between image checks
# Examples: 60 = 1 min, 300 = 5 min, 900 = 15 min, 3600 = 1 hour
SLEEP_INTERVAL = 300  # Start with 300 seconds for testing
# ============================================

print("MagTag ePaper Camera Display (Deep Sleep Mode)")
print(f"Sleep interval: {SLEEP_INTERVAL} seconds")

# Check if we're waking from deep sleep
if alarm.wake_alarm:
    print("Woke from deep sleep")
else:
    print("Cold boot - clearing sleep memory")
    # Clear sleep memory on cold boot
    alarm.sleep_memory[0:100] = b"\x00" * 100

# Initialize MagTag
magtag = MagTag()

# Set NeoPixels brightness and turn amber on power up
magtag.peripherals.neopixels.brightness = 0.1
magtag.peripherals.neopixels.fill(0x202000)  # Amber

# WiFi credentials from settings.toml
print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

# Turn cyan when connected to WiFi
magtag.peripherals.neopixels.fill(0x002020)  # Cyan
time.sleep(0.3)

# Set up Adafruit IO
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")
io_client = IO_HTTP(aio_username, aio_key, requests)

# Get the camera feed
feed_camera = io_client.get_feed("epapercam")

# Pre-calculate display dimensions
DISPLAY_WIDTH = magtag.graphics.display.width  # 296
DISPLAY_HEIGHT = magtag.graphics.display.height  # 128


def get_last_timestamp():
    """Retrieve the last image timestamp from sleep memory."""
    try:
        # Read 100 bytes from sleep memory (enough for a timestamp string)
        stored = bytes(alarm.sleep_memory[0:100]).decode("utf-8").strip("\x00")
        if stored:
            print(f"Last stored timestamp: {stored}")
            return stored
        return None
    except (UnicodeDecodeError, AttributeError):
        return None


def save_timestamp(timestamp):
    """Save the current image timestamp to sleep memory."""
    try:
        # Encode timestamp as UTF-8 bytes and store in sleep memory
        timestamp_bytes = timestamp.encode("utf-8")
        # Pad with null bytes to fill 100 bytes
        padded = timestamp_bytes + b"\x00" * (100 - len(timestamp_bytes))
        alarm.sleep_memory[0:100] = padded[:100]
        print(f"Saved timestamp to memory: {timestamp}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error saving timestamp: {e}")


def scale_and_crop_image(src_bitmap, src_y_offset, scale, img_palette):
    """Scale and crop the source bitmap to display size."""
    # Create display-sized bitmap
    display_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, len(img_palette))

    # Scale and crop the image
    for y in range(DISPLAY_HEIGHT):
        src_y = int((y + src_y_offset) / scale)
        if src_y >= src_bitmap.height:
            src_y = src_bitmap.height - 1
        for x in range(DISPLAY_WIDTH):
            src_x = int(x / scale)
            if src_x >= src_bitmap.width:
                src_x = src_bitmap.width - 1
            display_bitmap[x, y] = src_bitmap[src_x, src_y]

    return display_bitmap


def fetch_and_display_epaper_cam_image(data):
    """Display ePaper Camera image from already-fetched Adafruit IO data."""
    try:
        # Force garbage collection before processing
        gc.collect()
        print(f"Free memory before processing: {gc.mem_free()} bytes")

        # Turn on NeoPixels to indicate processing
        magtag.peripherals.neopixels.fill(0x202020)  # Dim white

        print("Processing image...")
        base64_image = data["value"]
        print(f"Received image data: {len(base64_image)} bytes (base64)")

        # Decode base64 to get GIF binary data
        gif_data = binascii.a2b_base64(base64_image)
        print(f"Decoded GIF: {len(gif_data)} bytes")

        # Free base64_image
        base64_image = None
        gc.collect()

        # Create a BytesIO wrapper for the GIF data
        gif_stream = BytesIO(gif_data)

        # Load with adafruit_imageload (supports GIF)
        bitmap, palette = adafruit_imageload.load(
            gif_stream, bitmap=displayio.Bitmap, palette=displayio.Palette
        )
        print(f"Loaded image: {bitmap.width}x{bitmap.height}")

        # Free gif_data and gif_stream
        gif_data = None
        gif_stream = None
        gc.collect()

        # Calculate scale factor to fill display width
        scale = DISPLAY_WIDTH / bitmap.width
        scaled_height = int(bitmap.height * scale)

        print(f"Scaling to: {DISPLAY_WIDTH}x{scaled_height} (scale={scale:.2f})")

        # Calculate vertical offset for centering (if scaled image is taller than display)
        src_y_offset = (
            (scaled_height - DISPLAY_HEIGHT) // 2
            if scaled_height > DISPLAY_HEIGHT
            else 0
        )

        # Scale and crop the image using helper function
        display_bitmap = scale_and_crop_image(bitmap, src_y_offset, scale, palette)

        # Free original bitmap after scaling
        bitmap = None
        gc.collect()

        # Create a TileGrid for display
        tile_grid = displayio.TileGrid(display_bitmap, pixel_shader=palette, x=0, y=0)

        # Create a group and add the tile grid
        group = displayio.Group()
        group.append(tile_grid)

        # Display on the MagTag
        magtag.graphics.display.root_group = group

        print("Refreshing display...")
        magtag.graphics.display.refresh()

        print("Image displayed on MagTag!")

        # Turn off NeoPixels after successful display
        magtag.peripherals.neopixels.fill(0x000000)

        # Final garbage collection
        gc.collect()
        print(f"Free memory after processing: {gc.mem_free()} bytes")

        return True  # Success

    except Exception as err:  # pylint: disable=broad-except
        # Turn NeoPixels red to indicate error
        magtag.peripherals.neopixels.fill(0x200000)  # Dim red
        time.sleep(2)
        magtag.peripherals.neopixels.fill(0x000000)

        print(f"Error: {err}")
        traceback.print_exception(type(err), err, err.__traceback__)

        # Garbage collection on error
        gc.collect()

        return False  # Failure


# Main execution - check for new image then deep sleep
try:
    # Turn green while checking for new images
    magtag.peripherals.neopixels.fill(0x002000)  # Green

    # Get last known timestamp
    last_timestamp = get_last_timestamp()

    # Fetch metadata to check timestamp
    print("Checking for new image...")
    feed_data = io_client.receive_data(feed_camera["key"])
    current_timestamp = feed_data.get("updated_at")

    print(f"Current image timestamp: {current_timestamp}")

    # Compare timestamps
    if current_timestamp != last_timestamp:
        print("New image detected! Downloading and displaying...")
        success = fetch_and_display_epaper_cam_image(feed_data)

        if success:
            # Save the new timestamp
            save_timestamp(current_timestamp)
        else:
            print("Display failed - not updating stored timestamp")
    else:
        print("No new image - skipping download to save battery")
        # Turn off green LED since we're not doing anything
        magtag.peripherals.neopixels.fill(0x000000)

    print(f"Going to deep sleep for {SLEEP_INTERVAL} seconds...")
    time.sleep(1)  # Brief delay to see the message

    # Create a time alarm for waking up
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_INTERVAL)

    # Enter deep sleep - this will restart the program when it wakes
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

except Exception as main_err:  # pylint: disable=broad-except
    print(f"Error in main execution: {main_err}")
    traceback.print_exception(type(main_err), main_err, main_err.__traceback__)

    # Even on error, go to sleep to preserve battery
    magtag.peripherals.neopixels.fill(0x200000)  # Red error indicator
    time.sleep(2)
    magtag.peripherals.neopixels.fill(0x000000)

    print(f"Error - sleeping for {SLEEP_INTERVAL} seconds...")
    time.sleep(1)

    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_INTERVAL)
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
