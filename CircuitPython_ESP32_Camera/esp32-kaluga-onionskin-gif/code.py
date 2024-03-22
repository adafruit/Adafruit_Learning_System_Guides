# SPDX-FileCopyrightText: Copyright (c) 2022 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Take a 10-frame stop motion GIF image.

This example requires:
 * `Espressif Kaluga v1.3 <https://www.adafruit.com/product/4729>`_ with compatible LCD display
 * `MicroSD card breakout board + <https://www.adafruit.com/product/254>`_ connected as follows:
    * CLK to board.IO18
    * DI to board.IO14
    * DO to board.IO17
    * CS to IO12
    * GND to GND
    * 5V to 5V
 * A compatible SD card inserted in the SD card slot
 * A compatible camera module (such as OV5640) connected to the camera header

To use:

Insert an SD card and power on.

Set up the first frame using the viewfinder. Click the REC button to take a frame.

Set up the next frame using the viewfinder. The previous and current frames are
blended together on the display, which is called an "onionskin".  Click the REC
button to take the next frame.

After 10 frames are recorded, the GIF is complete and you can begin recording another.


About the Kaluga development kit:

The Kaluga development kit comes in two versions (v1.2 and v1.3); this demo is
tested on v1.3.

The audio board must be mounted between the Kaluga and the LCD, it provides the
I2C pull-ups(!)

The v1.3 development kit's LCD can have one of two chips, the ili9341 or
st7789.  Furthermore, there are at least 2 ILI9341 variants, which differ
by rotation.  This example is written for one if the ILI9341 variants,
the one which usually uses rotation=90 to get a landscape display.
"""

import os
import struct

import espcamera
import analogio
import board
import busio
import bitmaptools
import fourwire
import displayio
import sdcardio
import storage
import gifio

V_RECORD = int(2.41 * 65536 / 3.3)
V_FUZZ = 2000

a = analogio.AnalogIn(board.IO6)

def record_pressed():
    value = a.value
    return abs(value - V_RECORD) < V_FUZZ

displayio.release_displays()
spi = busio.SPI(MOSI=board.LCD_MOSI, clock=board.LCD_CLK)
display_bus = fourwire.FourWire(
    spi,
    command=board.LCD_D_C,
    chip_select=board.LCD_CS,
    reset=board.LCD_RST,
    baudrate=80_000_000,
)
_INIT_SEQUENCE = (
    b"\x01\x80\x80"  # Software reset then delay 0x80 (128ms)
    b"\xEF\x03\x03\x80\x02"
    b"\xCF\x03\x00\xC1\x30"
    b"\xED\x04\x64\x03\x12\x81"
    b"\xE8\x03\x85\x00\x78"
    b"\xCB\x05\x39\x2C\x00\x34\x02"
    b"\xF7\x01\x20"
    b"\xEA\x02\x00\x00"
    b"\xc0\x01\x23"  # Power control VRH[5:0]
    b"\xc1\x01\x10"  # Power control SAP[2:0];BT[3:0]
    b"\xc5\x02\x3e\x28"  # VCM control
    b"\xc7\x01\x86"  # VCM control2
    b"\x36\x01\x40"  # Memory Access Control
    b"\x37\x01\x00"  # Vertical scroll zero
    b"\x3a\x01\x55"  # COLMOD: Pixel Format Set
    b"\xb1\x02\x00\x18"  # Frame Rate Control (In Normal Mode/Full Colors)
    b"\xb6\x03\x08\x82\x27"  # Display Function Control
    b"\xF2\x01\x00"  # 3Gamma Function Disable
    b"\x26\x01\x01"  # Gamma curve selected
    b"\xe0\x0f\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00"  # Set Gamma
    b"\xe1\x0f\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F"  # Set Gamma
    b"\x11\x80\x78"  # Exit Sleep then delay 0x78 (120ms)
    b"\x29\x80\x78"  # Display on then delay 0x78 (120ms)
)

display = displayio.Display(display_bus, _INIT_SEQUENCE, width=320, height=240)

sd_spi = busio.SPI(clock=board.IO18, MOSI=board.IO14, MISO=board.IO17)
sd_cs = board.IO12
sdcard = sdcardio.SDCard(sd_spi, sd_cs, baudrate=24_000_000)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

cam = espcamera.Camera(
    data_pins=board.CAMERA_DATA,
    external_clock_pin=board.CAMERA_XCLK,
    pixel_clock_pin=board.CAMERA_PCLK,
    vsync_pin=board.CAMERA_VSYNC,
    href_pin=board.CAMERA_HREF,
    pixel_format=espcamera.PixelFormat.RGB565,
    frame_size=espcamera.FrameSize.QVGA,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    framebuffer_count=2)

def exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError as _:
        return False


_image_counter = 0

def next_filename(extension="jpg"):
    global _image_counter  # pylint: disable=global-statement
    while True:
        filename = f"/sd/img{_image_counter:04d}.{extension}"
        if exists(filename):
            print(f"File exists: {filename}", end='\r')
            _image_counter += 1
            continue
        print()
        return filename

# Pre-cache the next image number
next_filename("gif")

# Blank the whole display
g = displayio.Group()
display.root_group = g
display.auto_refresh = False
display.refresh()

def open_next_image(extension="jpg"):
    global _image_counter  # pylint: disable=global-statement
    while True:
        filename = next_filename(extension)
        print("# writing to", filename)
        return open(filename, "wb")

cam.saturation = 3

old_frame = displayio.Bitmap(cam.width, cam.height, 65536)
# Displayed (onion skinned) frame here
onionskin = displayio.Bitmap(cam.width, cam.height, 65536)

ow = (display.width - onionskin.width) // 2
oh = (display.height - onionskin.height) // 2
display_bus.send(42, struct.pack(">hh", ow, onionskin.width + ow - 1))
display_bus.send(43, struct.pack(">hh", oh, onionskin.height + ow - 1))

def wait_record_pressed_update_display(first_frame, camera):
    while record_pressed():
        pass
    while True:
        frame = camera.take(1)
        print(type(frame))
        if record_pressed():
            return frame

        if first_frame:
            # First frame -- display as-is
            display_bus.send(44, frame)
        else:
            bitmaptools.alphablend(onionskin, old_frame, frame, displayio.Colorspace.RGB565_SWAPPED)
            display_bus.send(44, onionskin)

def take_stop_motion_gif(n_frames=10, replay_frame_time=.3):
    print(f"0/{n_frames}")
    frame = wait_record_pressed_update_display(True, cam)
    with open_next_image("gif") as f, gifio.GifWriter(f, cam.width, cam.height,
                displayio.Colorspace.RGB565_SWAPPED, dither=True) as writer:
        writer.add_frame(frame, replay_frame_time)
        for i in range(1, n_frames):
            print(f"{i}/{n_frames}")
            bitmaptools.blit(old_frame, frame, 0, 0, x1=0, y1=0, x2=cam.width, y2=cam.height)
            frame = wait_record_pressed_update_display(False, cam)
            writer.add_frame(frame, replay_frame_time)
        print("done")

while True:
    take_stop_motion_gif()
