# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import gc
import microcontroller
import digitalio
import sdcardio
import storage
import board
import busio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import displayio
from adafruit_neokey.neokey1x4 import NeoKey1x4
import adafruit_st7789
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_ov5640

gc.collect()
# Release any resources currently in use for the displays
displayio.release_displays()
gc.collect()
print("Initializing SD card")
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
sd_cs = board.GP17
sdcard = sdcardio.SDCard(spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")
gc.collect()
i2c = busio.I2C(board.GP5, board.GP4)
tft_cs = board.GP21
tft_dc = board.GP20
display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=None)
display = adafruit_st7789.ST7789(display_bus, width=240, height=240, rowstart=80, rotation=0)

gc.collect()
splash = displayio.Group()
display.root_group = splash

gc.collect()
font = bitmap_font.load_font("Helvetica-Bold-16.pcf")
t2 = label.Label(font, text="Start?", color=(255, 255, 255))
t2.anchor_point = (0.5, 0.0)
t2.anchored_position = (display.width / 2, 0)
splash.append(t2)
t1 = label.Label(font, text="Interval: 3s", color=(255, 255, 255))
t1.anchor_point = (0.5, 1.0)
t1.anchored_position = (display.width / 2, display.height)
splash.append(t1)

print("construct camera")
gc.collect()
reset = digitalio.DigitalInOut(board.GP14)
cam = adafruit_ov5640.OV5640(
    i2c,
    data_pins=(
        board.GP6,
        board.GP7,
        board.GP8,
        board.GP9,
        board.GP10,
        board.GP11,
        board.GP12,
        board.GP13,
    ),
    clock=board.GP3,
    vsync=board.GP0,
    href=board.GP2,
    mclk=None,
    shutdown=None,
    reset=reset,
    size=adafruit_ov5640.OV5640_SIZE_QCIF,
)
print("print chip id")
print(cam.chip_id)
gc.collect()
cam.quality = 3
gc.collect()

def exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError as _:
        return False

_image_counter = 0

def open_next_image():
    global _image_counter  # pylint: disable=global-statement
    while True:
        filename = f"/sd/img{_image_counter:04d}.jpg"
        _image_counter += 1
        if exists(filename):
            continue
        print("# writing to", filename)
        return open(filename, "wb")

cam.colorspace = adafruit_ov5640.OV5640_COLOR_RGB
gc.collect()

bitmap = displayio.Bitmap(cam.width, cam.height, 65535)
if bitmap is None:
    raise SystemExit("Could not allocate a bitmap")

tg = displayio.TileGrid(bitmap,
    pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED),
    x=int((display.width - bitmap.width) / 2), y=int((display.height - bitmap.height) / 2)
)
splash.append(tg)
gc.collect()

# Create a NeoKey object
neokey = NeoKey1x4(i2c, addr=0x30)
#  states for key presses
key_0_state = False
key_1_state = False
key_2_state = False
key_3_state = False

tm0 = time.monotonic_ns()
display.auto_refresh = False
mode = 0
intervals = [3, 5, 10, 30, 60]
index = 0
clock = ticks_ms()
count = 0
b = bytearray()
while True:
    if mode == 0: # preview
        cam.capture(bitmap)
        bitmap.dirty()
        display.refresh(minimum_frames_per_second=0)
        tm1 = time.monotonic_ns()
        # print("fps", 1e9 / (t1 - t0))
        tm0 = tm1
    if mode == 1: # timelapse
        if ticks_diff(ticks_ms(), clock) >= intervals[index]*1000:
            gc.collect()
            time.sleep(0.01)
            jpeg = cam.capture(b)
            # print(f"Captured {len(jpeg)} bytes of jpeg data")
            print(f" (had allocated {cam.capture_buffer_size} bytes")
            print(f"Resolution {cam.width}x{cam.height}")
            try:
                with open_next_image() as f:
                    f.write(jpeg)
                print("# Wrote image")
            except OSError as e:
                print(e)
            count += 1
            t2.text = f"Timelapsing! {count} photos taken"
            display.refresh(minimum_frames_per_second=0)
            clock = ticks_add(clock, intervals[index]*1000)
    if not neokey[0] and key_0_state:
        key_0_state = False
        neokey.pixels[0] = 0x0
    if not neokey[1] and key_1_state:
        key_1_state = False
        neokey.pixels[1] = 0x0
    if not neokey[2] and key_2_state:
        key_2_state = False
        neokey.pixels[2] = 0x0
    if not neokey[3] and key_3_state:
        key_3_state = False
        neokey.pixels[3] = 0x0
    #  if 1st neokey is pressed...
    if neokey[0] and not key_0_state:
        mode = 1
        print("Button A")
        #  turn on NeoPixel
        neokey.pixels[0] = 0xFF0000
        time.sleep(.2)
        try:
            del bitmap
            del tg
        except KeyError:
            continue
        gc.collect()
        #cam.size=adafruit_ov5640.OV5640_SIZE_VGA
        cam.colorspace = adafruit_ov5640.OV5640_COLOR_JPEG
        b = bytearray(cam.capture_buffer_size)
        t1.text=f"Taking photos every {intervals[index]}s"
        clock = ticks_ms()
        key_0_state = True

    #  if 2nd neokey is pressed...change interval
    if neokey[1] and not key_1_state:
        print("Button B")
        #  turn on NeoPixel
        neokey.pixels[1] = 0xFFFF00
        time.sleep(.2)
        index = (index + 1) % len(intervals)
        t1.text=f"Interval: {intervals[index]}s"
        key_1_state = True

    #  if 3rd neokey is pressed...autofocus
    if neokey[2] and not key_2_state:
        print("Button C")
        #  turn on NeoPixel
        neokey.pixels[2] = 0x00FF00
        time.sleep(.2)
        t2.text = "Autofocusing.."
        try:
            display.refresh(minimum_frames_per_second=0)
            cam.autofocus()
        except AttributeError:
            print("This camera module does not have autofocus..")
            continue
        key_2_state = True

    #  if 4th neokey is pressed...stop timelapse & reboot
    if neokey[3] and not key_3_state:
        print("Button D")
        #  turn on NeoPixel
        neokey.pixels[3] = 0x00FFFF
        time.sleep(.2)
        gc.collect()
        del b
        gc.collect()
        t2.text = "Ending timelapse.."
        t1.text = f"Took {count} photos"
        display.refresh(minimum_frames_per_second=0)
        print("resetting..")
        time.sleep(5)
        del t1
        del t2
        gc.collect()
        neokey.pixels[3] = 0x000000
        microcontroller.reset()
        key_3_state = True
