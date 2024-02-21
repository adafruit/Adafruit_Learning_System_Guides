# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
# SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

'''
Focus stacking example. Set FOCUS_STEPS (5-10 is a good range) for 0-255 range
Set STACK to True, or set to False to have JPEG mode take snapshots as usual.
'''

import time
import bitmaptools
import displayio
import gifio
import ulab.numpy as np

import adafruit_pycamera

pycam = adafruit_pycamera.PyCamera()
# pycam.live_preview_mode()

settings = (
    None,
    "resolution",
    "effect",
    "mode",
    "led_level",
    "led_color",
    "timelapse_rate"
)
curr_setting = 0

print("Starting!")
pycam.tone(440, 0.1)
last_frame = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
onionskin = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
timelapse_remaining = None
timelapse_timestamp = None

STACK = True  # mode placeholder
FOCUS_STEPS = 20  # number of focus steps to increment during bracket from 0-255
FOCUS_START = 30  # optionally, start the focus closer
focus_stacking = False

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
    elif pycam.mode_text == "LAPS":
        if timelapse_remaining is None:
            pycam.timelapsestatus_label.text = "STOP"
        else:
            timelapse_remaining = timelapse_timestamp - time.time()
            pycam.timelapsestatus_label.text = f"{timelapse_remaining}s /    "
        # Manually updating the label text a second time ensures that the label
        # is re-painted over the blitted preview.
        pycam.timelapse_rate_label.text = pycam.timelapse_rate_label.text
        pycam.timelapse_submode_label.text = pycam.timelapse_submode_label.text

        # only in high power mode do we continuously preview
        if (timelapse_remaining is None) or (
            pycam.timelapse_submode_label.text == "HiPwr"
        ):
            pycam.blit(pycam.continuous_capture())
        if pycam.timelapse_submode_label.text == "LowPwr" and (
            timelapse_remaining is not None
        ):
            pycam.display.brightness = 0.05
        else:
            pycam.display.brightness = 1
        pycam.display.refresh()

        if timelapse_remaining is not None and timelapse_remaining <= 0:
            # no matter what, show what was just on the camera
            pycam.blit(pycam.continuous_capture())
            # pycam.tone(200, 0.1) # uncomment to add a beep when a photo is taken
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
            pycam.display.refresh()
            pycam.blit(pycam.continuous_capture())
            timelapse_timestamp = (
                time.time() + pycam.timelapse_rates[pycam.timelapse_rate] + 1
            )
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
            if STACK:
                focus_stacking = True
                print("Start focus stack!")
                pycam.autofocus_vcm_step = FOCUS_START
                saved_settings = pycam.get_camera_autosettings()
                pycam.set_camera_exposure(saved_settings["exposure"])
                pycam.set_camera_gain(saved_settings["gain"])
                pycam.set_camera_wb(saved_settings["wb"])

            else:
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

    if focus_stacking:
        vcm_step = pycam.autofocus_vcm_step
        vcm_step = min(255, vcm_step + FOCUS_STEPS)
        if vcm_step < 255:
            pycam.capture_jpeg()
            pycam.tone(1600 + (vcm_step*10), 0.05)
            pycam.autofocus_vcm_step = vcm_step
            pycam.display_message(str(vcm_step), color=0xFF00FF)
            pycam.live_preview_mode()
            print("Now at focus", pycam.autofocus_vcm_step)

        else:
            focus_stacking = False
            print("Done stacking!")
            pycam.autofocus_vcm_step = FOCUS_START
            pycam.camera.exposure_ctrl = True
            pycam.set_camera_gain(None)  # go back to autogain
            pycam.set_camera_wb(None)  # go back to autobalance
            pycam.set_camera_exposure(None)  # go back to auto shutter
            pycam.live_preview_mode()
        time.sleep(0.01)



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
            print("getting", key, getattr(pycam, key))
            setattr(pycam, key, getattr(pycam, key) + 1)
    if pycam.down.fell:
        print("DN")
        key = settings[curr_setting]
        if key:
            setattr(pycam, key, getattr(pycam, key) - 1)
    if pycam.right.fell:
        print("RT")
        curr_setting = (curr_setting + 1) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelapse_rate":
            curr_setting = (curr_setting + 1) % len(settings)
        print(settings[curr_setting])
        # new_res = min(len(pycam.resolutions)-1, pycam.get_resolution()+1)
        # pycam.set_resolution(pycam.resolutions[new_res])
        pycam.select_setting(settings[curr_setting])
    if pycam.left.fell:
        print("LF")
        curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelaps_rate":
            curr_setting = (curr_setting + 1) % len(settings)
        print(settings[curr_setting])
        pycam.select_setting(settings[curr_setting])
        # new_res = max(1, pycam.get_resolution()-1)
        # pycam.set_resolution(pycam.resolutions[new_res])
    if pycam.select.fell:
        print("SEL")
        if pycam.mode_text == "LAPS":
            pycam.timelapse_submode += 1
            pycam.display.refresh()
    if pycam.ok.fell:
        print("OK")
        if pycam.mode_text == "LAPS":
            if timelapse_remaining is None:  # stopped
                print("Starting timelapse")
                timelapse_remaining = pycam.timelapse_rates[pycam.timelapse_rate]
                timelapse_timestamp = time.time() + timelapse_remaining + 1
                # dont let the camera take over auto-settings
                saved_settings = pycam.get_camera_autosettings()
                # print(f"Current exposure {saved_settings=}")
                pycam.set_camera_exposure(saved_settings["exposure"])
                pycam.set_camera_gain(saved_settings["gain"])
                pycam.set_camera_wb(saved_settings["wb"])
            else:  # is running, turn off
                print("Stopping timelapse")

                timelapse_remaining = None
                pycam.camera.exposure_ctrl = True
                pycam.set_camera_gain(None)  # go back to autogain
                pycam.set_camera_wb(None)  # go back to autobalance
                pycam.set_camera_exposure(None)  # go back to auto shutter
