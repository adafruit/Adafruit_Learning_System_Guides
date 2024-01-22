# SPDX-FileCopyrightText: 2023 Jeff Epler & John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
''' Wireless remote for MEMENTO camera with TouchOSC'''

import time
import os
import bitmaptools
import displayio
import gifio
import ulab.numpy as np
import adafruit_pycamera
import wifi
import socketpool
import microosc

UDP_HOST = ""
UDP_PORT = 8000
ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
print("connecting to WiFi", ssid)
wifi.radio.connect(ssid, password)
print("my ip address:", wifi.radio.ipv4_address)
socket_pool = socketpool.SocketPool(wifi.radio)

pycam = adafruit_pycamera.PyCamera()
pycam.autofocus_init()

settings = (None, "resolution", "effect", "mode", "led_level", "led_color")
curr_setting = 0

print("Starting!")
last_frame = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
onionskin = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)

pycam.tone(800, 0.1)
pycam.tone(1200, 0.05)

def snap_jpeg():
    pycam.tone(600, 0.1)
    try:
        pycam.display_message("Snap!", color=0x0000FF)
        pycam.capture_jpeg()
        pycam.live_preview_mode()
    # pylint: disable=unused-variable
    except TypeError as e:
        pycam.display_message("Failed", color=0xFF0000)
        time.sleep(0.5)
        pycam.live_preview_mode()
    except RuntimeError as e:
        pycam.display_message("Error\nNo SD Card", color=0xFF0000)
        time.sleep(0.5)

def snap_gboy():
    pycam.tone(600, 0.1)
    try:
        f = pycam.open_next_image("gif")
        pycam.display_message("Snap!", color=0x00ff44)
    # pylint: disable=unused-variable
    except RuntimeError as e:
        pycam.display_message("Error\nNo SD Card", color=0xFF0000)
        time.sleep(0.5)

    with gifio.GifWriter(
        f,
        pycam.camera.width,
        pycam.camera.height,
        displayio.Colorspace.RGB565_SWAPPED,
        dither=True,
    ) as g:
        g.add_frame(last_frame, 1)

def snap_gif():
    pycam.tone(600, 0.1)
    try:
        f = pycam.open_next_image("gif")
    # pylint: disable=unused-variable
    except RuntimeError as e:
        pycam.display_message("Error\nNo SD Card", color=0xFF0000)
        time.sleep(0.5)
    i = 0
    ft = []
    pycam._mode_label.text = "RECORDING"  # pylint: disable=protected-access

    pycam.display.refresh()
    with gifio.GifWriter(
        f,
        pycam.camera.width,
        pycam.camera.height,
        displayio.Colorspace.RGB565_SWAPPED,
        dither=True,
    ) as g:
        t00 = t0 = time.monotonic()
        while (i < 15) or not pycam.shutter_button.value:
            i += 1
            _gifframe = pycam.continuous_capture()
            g.add_frame(_gifframe, 0.12)
            pycam.blit(_gifframe)
            t1 = time.monotonic()
            ft.append(1 / (t1 - t0))
            print(end=".")
            t0 = t1
    pycam._mode_label.text = "GIF"  # pylint: disable=protected-access
    print(f"\nfinal size {f.tell()} for {i} frames")
    print(f"average framerate {i/(t1-t00)}fps")
    print(f"best {max(ft)} worst {min(ft)} std. deviation {np.std(ft)}")
    f.close()
    pycam.display.refresh()
    pycam.tone(1200, 0.15)

def snap_stop():
    pycam.tone(600, 0.1)
    pycam.capture_into_bitmap(last_frame)
    pycam.stop_motion_frame += 1
    try:
        pycam.display_message("Snap!", color=0x0000FF)
        pycam.capture_jpeg()
    # pylint: disable=unused-variable
    except TypeError as e:
        pycam.display_message("Failed", color=0xFF0000)
        time.sleep(0.5)
    except RuntimeError as e:
        pycam.display_message("Error\nNo SD Card", color=0xFF0000)
        time.sleep(0.5)
    pycam.live_preview_mode()

def toggle_handler(msg):
    addr = msg.addr
    tog_num = int(addr.replace('/1/toggle',''))
    if msg.args[0] == 1.0:
        print(tog_num, "is ON")
    else:
        print(tog_num, "is off")

def fader_handler(msg):  # faders
    """Used to handle 'fader' OscMsgs, printing it as a '*' text progress bar
    :param OscMsg msg: message with one required float32 value
    """
    osc_addr = msg.addr.split('/')  # chop up the address into parts
    # page_num = osc_addr[1]
    fader_num = int(osc_addr[2].replace('fader', ''))  # get the number only
    if fader_num == 1:  # led level
        led_val = int(msg.args[0] * 5)
        pycam.led_level = led_val

mode_texts = ("JPEG", "GIF", "GBOY", "STOP")

def radio_handler(msg):  # Radio buttons
    osc_addr = msg.addr.split('/')  # chop up the address into parts
    print(osc_addr)
    page_num = osc_addr[1]
    print("page_num:", page_num)
    rad_num = int(osc_addr[2].replace('radio', ''))  # get the number only
    print("rad_num:", rad_num)
    if rad_num == 1:  # MODE
        print("switched mode to", mode_texts[msg.args[0]])
        pycam.mode = msg.args[0]
    if rad_num == 2:  # resolution
        print("switched resolution")
        pycam.resolution = msg.args[0]
    if rad_num == 3:  # LED color
        print("set color")
        pycam.led_color = msg.args[0]
    if rad_num == 4:  # effects
        print("switched effect")
        pycam.effect = msg.args[0]

def button_handler(msg):  # buttons
    addr = msg.addr
    button_num = int(addr.replace('/1/button',''))
    if msg.args[0] == 1.0:
        print(button_num, "is ON")
        if button_num == 1:
            pycam.tone(1200, 0.05)
            pycam.tone(1600, 0.05)
            if pycam.mode_text == "JPEG":
                snap_jpeg()
            if pycam.mode_text == "GBOY":
                snap_gboy()
            if pycam.mode_text == "GIF":
                snap_gif()
            if pycam.mode_text == "STOP":
                snap_stop()

        if button_num == 2:  # focus
            pycam.tone(1800, 0.05)
            print("FOCUS")
            print(pycam.autofocus_status)
            pycam.autofocus()
            print(pycam.autofocus_status)
            pycam.tone(1400, 0.05)

    else:
        print(button_num, "is off")

dispatch_map = {
    "/": lambda msg: print("msg:", msg.addr, msg.args),  # prints all messages
    "/1/fader": fader_handler,
    "/2/fader": fader_handler,
    "/1/toggle": toggle_handler,
    "/1/button": button_handler,
    "/1/radio": radio_handler,
    "/2/radio": radio_handler
}

osc_server = microosc.OSCServer(socket_pool, UDP_HOST, UDP_PORT, dispatch_map)
print("MicroOSC server started on ", UDP_HOST, UDP_PORT)


while True:
    osc_server.poll()  # check for incoming OSC messages

    if pycam.mode_text == "STOP" and pycam.stop_motion_frame != 0:
        # alpha blend
        new_frame = pycam.continuous_capture()
        bitmaptools.alphablend(
            onionskin, last_frame, new_frame, displayio.Colorspace.RGB565_SWAPPED
        )
        pycam.blit(onionskin)
    elif pycam.mode_text == "GBOY":
        bitmaptools.dither(
            last_frame, pycam.continuous_capture(), displayio.Colorspace.RGB565_SWAPPED
        )
        pycam.blit(last_frame)
    else:
        pycam.blit(pycam.continuous_capture())

    pycam.keys_debounce()

    if pycam.shutter.long_press:
        print("FOCUS")
        print(pycam.autofocus_status)
        pycam.autofocus()
        print(pycam.autofocus_status)

    if pycam.shutter.short_count:
        print("Shutter released")
        if pycam.mode_text == "STOP":
            snap_stop()

        if pycam.mode_text == "GBOY":
            snap_gboy()

        if pycam.mode_text == "GIF":
            snap_gif()

        if pycam.mode_text == "JPEG":
            snap_jpeg()

    if pycam.card_detect.fell:
        print("SD card removed")
        pycam.unmount_sd_card()
        pycam.display.refresh()
    if pycam.card_detect.rose:
        print("SD card inserted")
        pycam.display_message("Mounting\nSD Card", color=0xFFFFFF)
        for _ in range(3):
            try:
                print("Mounting card")
                pycam.mount_sd_card()
                print("Success!")
                break
            except OSError as e:
                print("Retrying!", e)
                time.sleep(0.5)
        else:
            pycam.display_message("SD Card\nFailed!", color=0xFF0000)
            time.sleep(0.5)
        pycam.display.refresh()

    if pycam.up.fell:
        print("UP")
        key = settings[curr_setting]
        if key:
            setattr(pycam, key, getattr(pycam, key) + 1)
    if pycam.down.fell:
        print("DN")
        key = settings[curr_setting]
        if key:
            setattr(pycam, key, getattr(pycam, key) - 1)
    if pycam.left.fell:
        print("LF")
        curr_setting = (curr_setting + 1) % len(settings)
        print(settings[curr_setting])
        pycam.select_setting(settings[curr_setting])
    if pycam.right.fell:
        print("RT")
        curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        print(settings[curr_setting])
        pycam.select_setting(settings[curr_setting])
    if pycam.select.fell:
        print("SEL")
    if pycam.ok.fell:
        print("OK")
