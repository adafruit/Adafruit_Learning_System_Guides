# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import time
import board
import bitmaptools
import displayio
import gifio
import ulab.numpy as np
from adafruit_debouncer import Button
import adafruit_pycamera
from digitalio import DigitalInOut, Direction, Pull

pycam = adafruit_pycamera.PyCamera()
# pycam.live_preview_mode()

settings = (None, "resolution", "effect", "mode", "led_level", "led_color")
curr_setting = 0

pin = DigitalInOut(board.A0)
pin.direction = Direction.INPUT
pin.pull = Pull.UP
ext_button = Button(pin, long_duration_ms=1000)

print("Starting!")
# pycam.tone(200, 0.1)
last_frame = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
onionskin = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
while True:
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
    # print("\t\t", capture_time, blit_time)

    pycam.keys_debounce()
    ext_button.update()
    # test shutter button
    if pycam.shutter.long_press or ext_button.long_press:
        print("FOCUS")
        print(pycam.autofocus_status)
        pycam.autofocus()
        print(pycam.autofocus_status)
    if pycam.shutter.short_count or ext_button.short_count:
        print("Shutter released")
        if pycam.mode_text == "STOP":
            pycam.capture_into_bitmap(last_frame)
            pycam.stop_motion_frame += 1
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
            except TypeError as e:
                pycam.display_message("Failed", color=0xFF0000)
                time.sleep(0.5)
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
            pycam.live_preview_mode()

        if pycam.mode_text == "GBOY":
            try:
                f = pycam.open_next_image("gif")
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
                continue

            with gifio.GifWriter(
                f,
                pycam.camera.width,
                pycam.camera.height,
                displayio.Colorspace.RGB565_SWAPPED,
                dither=True,
            ) as g:
                g.add_frame(last_frame, 1)

        if pycam.mode_text == "GIF":
            try:
                f = pycam.open_next_image("gif")
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
                continue
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

        if pycam.mode_text == "JPEG":
            pycam.tone(200, 0.1)
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
                pycam.live_preview_mode()
            except TypeError as e:
                pycam.display_message("Failed", color=0xFF0000)
                time.sleep(0.5)
                pycam.live_preview_mode()
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
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
        # new_res = min(len(pycam.resolutions)-1, pycam.get_resolution()+1)
        # pycam.set_resolution(pycam.resolutions[new_res])
        pycam.select_setting(settings[curr_setting])
    if pycam.right.fell:
        print("RT")
        curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        print(settings[curr_setting])
        pycam.select_setting(settings[curr_setting])
        # new_res = max(1, pycam.get_resolution()-1)
        # pycam.set_resolution(pycam.resolutions[new_res])
    if pycam.select.fell:
        print("SEL")
    if pycam.ok.fell:
        print("OK")
