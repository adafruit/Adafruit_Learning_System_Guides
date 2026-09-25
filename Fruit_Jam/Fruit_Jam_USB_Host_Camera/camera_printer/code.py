# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Photo booth: take a picture with a USB webcam on the Fruit Jam and print it
on a Bluetooth "cat printer" through the Fruit Jam's ESP32-C6.

Live view:  button 1 takes a photo, button 2 switches between the dithered
            and the color preview, button 3 changes the print lightness.
Photo view: button 1 prints, button 2 goes back to the live view,
            button 3 changes the print lightness.

The keys 1, 2 and 3 on the serial console work like the buttons.
"""

import sys
import time

import bitmapfilter
import bitmaptools
import board
import digitalio
import displayio
import jpegio
import keypad
import picodvi
import picogame
import supervisor
import terminalio
import ulab.numpy as np

# fruitjam_ble has to come before adafruit_ble
import fruitjam_ble  # pylint: disable=wrong-import-order
from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement

import adafruit_usb_host_camera
from thermalprinter import CatPrinter, MXW01Printer

# pylint: disable=global-statement

WIDTH, HEIGHT = 320, 240
# The camera runs in one mode for both the preview and the photo, because
# switching modes can stall some cameras.
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
PRINT_WIDTH, PRINT_HEIGHT = 384, 288  # the printer is 384 dots wide
PRINTER_NAMES = ("GB0", "GT0", "MX0", "MX1", "YT0")
# Newer printers with the MXW01 protocol
MXW01_NAMES = ("MXW01",)
FEED_ROWS = 80  # blank rows after a photo, so it clears the tear-off edge

# Thermal prints come out dark, so the photo is lightened with a gamma curve
# before dithering. Button 3 cycles through these.
LIGHTNESS = (("normal", 1.0), ("light", 0.75), ("lighter", 0.55), ("dark", 1.4))

BLACK = picogame.rgb565(0, 0, 0)
WHITE = picogame.rgb565(255, 255, 255)
STATUS_BG = picogame.rgb565(0, 0, 80)

displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    WIDTH,
    HEIGHT,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
target = picogame.Framebuffer(framebuffer, WIDTH, HEIGHT, native_rgb565=True)

buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)

# Bitmaps are RGB565_SWAPPED, which is picogame's transfer byte order, so
# picogame draws their memory directly.
preview = displayio.Bitmap(WIDTH, HEIGHT, 65536)  # camera image
shown = displayio.Bitmap(WIDTH, HEIGHT, 65536)  # dithered preview or photo
photo = displayio.Bitmap(CAMERA_WIDTH, CAMERA_HEIGHT, 65536)  # full size photo
print_source = displayio.Bitmap(PRINT_WIDTH, PRINT_HEIGHT, 65536)
# Dithering into a 2-color bitmap crashes (see dither_bug.md), so dither into a
# 65536-color bitmap holding 0 and 65535, and pack the rows with ulab.
print_dithered = displayio.Bitmap(PRINT_WIDTH, PRINT_HEIGHT, 65536)
BIT_WEIGHTS = np.array([1, 2, 4, 8, 16, 32, 64, 128], dtype=np.uint8)
ROW_BYTES = PRINT_WIDTH // 8


def picogame_bitmap(bitmap):
    return picogame.Bitmap(bitmap, bitmap.width, bitmap.height)


preview_sprite_bitmap = picogame_bitmap(preview)
shown_sprite_bitmap = picogame_bitmap(shown)
image_sprite = picogame.Sprite(shown_sprite_bitmap, x=0, y=0)
status_bar = picogame.Canvas(WIDTH, 14)
status_bar.move(0, HEIGHT - 14)
layers = [image_sprite, status_bar]


def refresh():
    picogame.render(target, layers, None, 0, 0, WIDTH, HEIGHT)


def status(text):
    print(text)
    status_bar.clear(STATUS_BG)
    status_bar.text(3, 1, text, WHITE, terminalio.FONT)
    refresh()


def read_input():
    """Return the button that was pressed (0, 1 or 2) or None."""
    event = buttons.events.get()
    if event and event.pressed:
        return event.key_number
    if supervisor.runtime.serial_bytes_available:
        _key = sys.stdin.read(1)
        if _key in "123":
            return ord(_key) - ord("1")
    return None


# ---- camera ----

camera = None
decoder = jpegio.JpegDecoder()


def open_camera():
    global camera  # noqa: PLW0603
    camera = None
    while camera is None:
        try:
            # Finds the camera among the attached devices (a keyboard, a mouse...)
            camera = adafruit_usb_host_camera.UVCCamera()
        except ValueError:
            status("Plug in a USB camera")
            time.sleep(1)
    camera.start(camera.find_mode(CAMERA_WIDTH, CAMERA_HEIGHT))


def power_cycle_camera():
    """Some cameras stop sending image data after a while; switching the USB
    host port off and on again brings them back."""
    status("Camera stalled, restarting it")
    power = digitalio.DigitalInOut(board.USB_HOST_5V_POWER)
    power.switch_to_output(True)
    power.value = False
    time.sleep(1.5)
    power.value = True
    power.deinit()
    time.sleep(3)
    open_camera()


timeouts = 0


def capture_jpeg():
    """Return the newest camera frame as a JPEG, or None if none came in time."""
    global timeouts  # noqa: PLW0603
    try:
        frame = camera.capture()
    except RuntimeError:
        timeouts += 1
        if timeouts >= 5:
            timeouts = 0
            power_cycle_camera()
        return None
    timeouts = 0
    return camera.add_huffman_tables(frame)


# ---- image processing ----

lightness = 0


def lighten(bitmap):
    gamma = LIGHTNESS[lightness][1]
    if gamma != 1.0:
        bitmapfilter.lookup(bitmap, lambda v: v**gamma)


def dither(dest, source):
    bitmaptools.dither(
        dest,
        source,
        displayio.Colorspace.RGB565_SWAPPED,
        bitmaptools.DitherAlgorithm.FloydStenberg,
    )


def show_dithered_preview():
    lighten(preview)
    dither(shown, preview)


def render_photo():
    """Scale, lighten and dither `photo` for the printer and for the screen."""
    bitmaptools.rotozoom(print_source, photo, scale=PRINT_WIDTH / CAMERA_WIDTH)
    lighten(print_source)
    dither(print_dithered, print_source)
    bitmaptools.rotozoom(preview, photo, scale=WIDTH / CAMERA_WIDTH)
    lighten(preview)
    dither(shown, preview)


def packed_rows():
    """The dithered print image as 1 bit per pixel, 1 = black, with the
    leftmost pixel of each byte in the lowest bit."""
    pixels = np.frombuffer(print_dithered, dtype=np.uint16)
    black = np.array(pixels.reshape((PRINT_HEIGHT * ROW_BYTES, 8)) == 0, dtype=np.uint8)
    return np.array(np.dot(black, BIT_WEIGHTS), dtype=np.uint8).tobytes()


# ---- printer ----

ble = None
connection = None
printer = None


def start_ble():
    global ble  # noqa: PLW0603
    if ble is None:
        status("Starting Bluetooth")
        ble = BLERadio(fruitjam_ble.start_bluetooth())


def is_printer(adv):
    name = adv.complete_name or adv.short_name
    if name:
        print("saw", name, adv.address, adv.rssi)
        if name.startswith(PRINTER_NAMES + MXW01_NAMES):
            return True
    return is_mxw01(adv) or (
        isinstance(adv, ProvideServicesAdvertisement) and CatPrinter in adv.services
    )


def is_mxw01(adv):
    name = adv.complete_name or adv.short_name
    if name and name.startswith(MXW01_NAMES):
        return True
    return (
        isinstance(adv, ProvideServicesAdvertisement)
        and MXW01Printer.advertised_uuid in adv.services
    )


def connect_printer():
    """Find and connect to the printer, unless still connected."""
    global connection, printer  # noqa: PLW0603
    if connection is not None and connection.connected:
        return
    connection = printer = None
    start_ble()
    status("Looking for the printer...")
    found = None
    for adv in ble.start_scan(ProvideServicesAdvertisement, Advertisement, timeout=15):
        if is_printer(adv):
            found = adv
            break
    ble.stop_scan()
    if found is None:
        raise RuntimeError("No printer found. Is it on?")
    status("Connecting to " + (found.complete_name or "printer"))
    connection = ble.connect(found, timeout=10)
    if CatPrinter not in connection:
        connection.disconnect()
        connection = None
        raise RuntimeError("That is not a cat printer")
    # Both kinds of printer have the same service UUID but different protocols
    printer = connection[MXW01Printer if is_mxw01(found) else CatPrinter]


def print_photo():
    rows = packed_rows()
    connect_printer()
    blank = bytes(ROW_BYTES)
    if isinstance(printer, MXW01Printer):
        printer.print_bitmap(
            rows + blank * FEED_ROWS,
            progress=lambda done: status("Printing %d%%" % (100 * done)),
        )
        return
    for y in range(PRINT_HEIGHT):
        printer.print_bitmap_row(
            rows[y * ROW_BYTES : (y + 1) * ROW_BYTES], reverse_bits=False
        )
        if y % 32 == 0:
            status("Printing %d%%" % (100 * y // PRINT_HEIGHT))
    status("Feeding paper")
    for _ in range(FEED_ROWS):
        printer.print_bitmap_row(blank, reverse_bits=False)


# ---- main loop ----


def live_help():
    status(
        "1:photo 2:%s 3:%s"
        % ("color" if dithered else "dither", LIGHTNESS[lightness][0])
    )


def photo_help():
    status("1:print 2:retake 3:%s" % LIGHTNESS[lightness][0])


open_camera()
dithered = True
frozen = False
live_help()
last_poll = time.monotonic()
while True:
    key = read_input()
    if key == 2:
        lightness = (lightness + 1) % len(LIGHTNESS)
        if frozen:
            render_photo()
            photo_help()
        else:
            live_help()
    elif frozen:
        if key == 0:
            try:
                print_photo()
                photo_help()
            except Exception as e:  # pylint: disable=broad-except
                # keep the booth running
                print("Print failed:", repr(e))
                status("Print failed. 1:retry 2:retake")
        elif key == 1:
            frozen = False
            live_help()
    elif key == 0:
        status("Taking photo...")
        jpeg = None
        while jpeg is None:
            jpeg = capture_jpeg()
        decoder.open(jpeg)
        decoder.decode(photo)
        render_photo()
        image_sprite.bitmap = shown_sprite_bitmap
        frozen = True
        photo_help()
    elif key == 1:
        dithered = not dithered
        live_help()

    if not frozen:
        jpeg = capture_jpeg()
        if jpeg is not None:
            decoder.open(jpeg)
            decoder.decode(preview, scale=1)
            if dithered:
                show_dithered_preview()
                image_sprite.bitmap = shown_sprite_bitmap
            else:
                image_sprite.bitmap = preview_sprite_bitmap
    refresh()

    # The Bluetooth code only handles events when asked, so check on the
    # printer now and then to notice when it goes away.
    if connection is not None and time.monotonic() - last_poll > 1:
        last_poll = time.monotonic()
        if not connection.connected:
            connection = printer = None
