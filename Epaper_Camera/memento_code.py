# SPDX-FileCopyrightText: 2023 Brent Rubell & 2026 John Park for Adafruit Industries
#
# An open-source IoT ePaper camera with the Adafruit MEMENTO and MagTag
#
# SPDX-License-Identifier: Unlicense

import binascii
import gc
import os
import ssl
import time
import traceback

import adafruit_imageload
import adafruit_pycamera
import adafruit_requests
import bitmaptools
import displayio
import gifio
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

print("CircuitPython ePaper Camera")

### WiFi ###
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

# Keep pool global but recreate requests/io each time
pool = socketpool.SocketPool(wifi.radio)

# Adafruit IO feed name
feed_name = "epapercam"

# Initialize memento camera
pycam = adafruit_pycamera.PyCamera()
pycam.effect = 2  # B&W
pycam.resolution = 0  # 240x240
pycam.led_level = 1
pycam.led_color = 4  # white
pycam.led_color = 0
time.sleep(0.1)
print(f"Camera now at: {pycam.camera.width}x{pycam.camera.height}")

pycam.display.brightness = 0.7

capture_count = 0


def load_and_dither_image(temp_jpeg):
    """Load JPEG and create dithered bitmap."""
    print("[] Loading bitmap...")
    captured_bitmap, _ = adafruit_imageload.load(temp_jpeg)
    print(f"[] Loaded bitmap: {captured_bitmap.width}x{captured_bitmap.height}")

    print("[] Creating dither bitmap...")
    dithered_frame = displayio.Bitmap(
        captured_bitmap.width, captured_bitmap.height, 65535
    )

    print("[] Dithering...")
    bitmaptools.dither(
        dithered_frame, captured_bitmap, displayio.Colorspace.RGB565_SWAPPED
    )
    print("[] Dithered!")

    # Free the captured bitmap
    captured_bitmap = None
    gc.collect()
    print(f"[] Cleared bitmap, free memory: {gc.mem_free()} bytes")

    return dithered_frame


def create_gif_from_bitmap(dithered_frame, temp_filename):
    """Create GIF file from dithered bitmap."""
    print("[] Creating GIF file...")
    with open(temp_filename, "wb") as f:
        with gifio.GifWriter(
            f,
            dithered_frame.width,
            dithered_frame.height,
            displayio.Colorspace.RGB565_SWAPPED,
            dither=True,
        ) as g:
            g.add_frame(dithered_frame, 1)
    print("[] GIF file created")


def send_to_adafruit_io(encoded_data):
    """Send encoded image data to Adafruit IO."""
    # Create FRESH requests and IO objects for this send
    print("[] Creating fresh network session...")
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    io = IO_HTTP(aio_username, aio_key, requests)

    # Get feed
    try:
        feed_camera = io.get_feed(feed_name)
    except AdafruitIO_RequestError:
        feed_camera = io.create_new_feed(feed_name)

    print("[] Fresh session created")

    # Send to IO
    print("[] Sending to Adafruit IO...")
    io.send_data(feed_camera["key"], encoded_data)
    print("[] Sent to IO successfully!")

    # Explicitly delete requests and io to free sockets
    print("[] Cleaning up network objects...")
    del io
    del requests
    gc.collect()
    print("[] Network objects cleaned up")


def capture_send_image():
    """Captures an image, dithers it to black and white, saves as GIF, and sends to Adafruit IO."""
    # pylint: disable=too-many-statements
    global capture_count  # pylint: disable=global-statement
    capture_count += 1

    print(f"\n=== CAPTURE #{capture_count} START ===")

    # Force garbage collection before capture
    gc.collect()
    print(f"[] Free memory: {gc.mem_free()} bytes")

    try:
        print("[] Starting autofocus...")
        pycam.autofocus()
        print("[] Autofocus complete")

        print("[] Capturing JPEG...")
        jpeg_data = pycam.capture_into_jpeg()
        print(f"[] Captured JPEG: {len(jpeg_data)} bytes")

        print("[] Writing temp file...")
        temp_jpeg = "/sd/temp_capture.jpg"
        with open(temp_jpeg, "wb") as f:
            f.write(jpeg_data)
        print("[] Temp file written")

        # Clear jpeg_data from memory
        jpeg_data = None
        gc.collect()
        print(f"[] Cleared JPEG data, free memory: {gc.mem_free()} bytes")

        # Load and dither image
        dithered_frame = load_and_dither_image(temp_jpeg)

        print("[] Displaying preview...")
        pycam.blit(dithered_frame)
        pycam.display.refresh()
        print("[] Preview displayed")

        # Create GIF
        temp_filename = "/sd/temp_doorbell.gif"
        create_gif_from_bitmap(dithered_frame, temp_filename)

        # Free dithered_frame
        dithered_frame = None
        gc.collect()
        print(f"[] Cleared dither frame, free memory: {gc.mem_free()} bytes")

        print("[] Reading GIF...")
        with open(temp_filename, "rb") as f:
            gif_data = f.read()
        print(f"[] Read GIF: {len(gif_data)} bytes")

        print("[] Encoding to base64...")
        encoded_data = binascii.b2a_base64(gif_data).strip().decode("ascii")
        print(f"[] Encoded: {len(encoded_data)} chars")

        # Free gif_data
        gif_data = None
        gc.collect()
        print(f"[] Cleared GIF data, free memory: {gc.mem_free()} bytes")

        # Send to Adafruit IO
        send_to_adafruit_io(encoded_data)

        # Free encoded data
        encoded_data = None
        gc.collect()
        print(f"[] Cleared encoded data, free memory: {gc.mem_free()} bytes")

        pycam.tone(3200, 0.1)

    except Exception as err:  # pylint: disable=broad-except
        print(f"[ERROR] Exception during capture: {err}")
        traceback.print_exception(type(err), err, err.__traceback__)
        pycam.tone(400, 0.3)  # Low error tone

    finally:
        print("[] Resuming live preview...")
        try:
            pycam.live_preview_mode()
            print("[] Live preview mode set")
            time.sleep(0.3)
            print("[] Waited for stabilization")
            pycam.display.refresh()
            print("[] Display refreshed")
        except Exception as resume_err:  # pylint: disable=broad-except
            print(f"[ERROR] Exception resuming preview: {resume_err}")

        gc.collect()
        print(f"[] Final free memory: {gc.mem_free()} bytes")
        print("=== CAPTURE COMPLETE ===\n")


print("ePaper camera ready.")
pycam.tone(800, 0.1)
pycam.tone(1200, 0.05)

while True:
    try:
        frame = pycam.continuous_capture()
        if frame and hasattr(frame, "width"):
            pycam.blit(frame)
        else:
            print("[WARNING] Invalid frame")

        pycam.keys_debounce()

        if pycam.shutter.short_count:
            print("\n>>> SHUTTER PRESSED <<<")
            pycam.tone(1200, 0.05)
            pycam.tone(1600, 0.05)
            capture_send_image()
            print(">>> Ready for next capture <<<\n")

        if pycam.up.rose:
            pycam.led_level = (pycam.led_level + 1) % 5
            print(f"LED brightness: {pycam.led_level}")
            pycam.led_color = 4
            time.sleep(0.2)
            pycam.led_color = 0

    except Exception as main_err:  # pylint: disable=broad-except
        print(f"[ERROR] Main loop exception: {main_err}")
        traceback.print_exception(type(main_err), main_err, main_err.__traceback__)
        time.sleep(0.5)

    time.sleep(0.01)
