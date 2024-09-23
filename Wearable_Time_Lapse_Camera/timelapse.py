# SPDX-FileCopyrightText: 2024 Melissa leBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3

import os
import re
import time
import board
import digitalio

# Timelapse script, because timelapse options in raspistill don't power
# down the camera between captures. Script also provides a camera busy LED
# (v2 cameras don't include one) and a system halt button.
# Limitations: if DEST is FAT32 filesystem, max of 65535 files in directory;
# if DEST is ext4 filesystem, may have performance issues above 10K files.
# For intervals <2 sec, better just to use raspistill's timelapse feature.

# Configurable stuff...
INTERVAL = 15  # Time between captures, in seconds
WIDTH = 1280  # Image width in pixels
HEIGHT = 720  # Image height in pixels
QUALITY = 51  # JPEG image quality (0-100)
DEST = "/boot/timelapse"  # Destination directory (MUST NOT CONTAIN NUMBERS)
PREFIX = "img"  # Image prefix (MUST NOT CONTAIN NUMBERS)
HALT_PIN = board.D21  # Halt button GPIO pin (other end to GND)
LED_PIN = board.D5  # Status LED pin (v2 Pi cam lacks built-in LED)
COMMAND = "libcamera-still -n --width {width} --height {height} -q {quality} --thumb none -t 250 -o {outfile}" # pylint: disable=line-too-long
# COMMAND = "raspistill -n -w {width -h {height} -q {quality} -th none -t 250 -o {outfile}"

def main():
    prevtime = 0  # Time of last capture (0 = do 1st image immediately)
    halt = digitalio.DigitalInOut(HALT_PIN)
    halt.switch_to_input(pull=digitalio.Pull.UP)
    led = digitalio.DigitalInOut(LED_PIN)
    led.switch_to_output()

    # Create destination directory (if not present)
    os.makedirs(DEST, exist_ok=True)

    # Find index of last image (if any) in directory, start at this + 1
    files = os.listdir(DEST)
    numbers = [
        int(re.search(r"\d+", f).group())
        for f in files
        if f.startswith(PREFIX) and re.search(r"\d+", f)
    ]
    numbers.sort()
    frame = numbers[-1] + 1 if numbers else 1
    currenttime = time.monotonic()

    while True:
        while time.monotonic() < prevtime + INTERVAL:  # Until next image capture time
            currenttime = time.monotonic()
            # Check for halt button -- hold >= 2 sec
            while not halt.value:
                if time.monotonic() >= currenttime + 2:
                    led.value = True
                    os.system("shutdown -h now")
        outfile = f"{DEST}/{PREFIX}{frame:05}.jpg"
        # echo $OUTFILE
        led.value = True
        os.system(
            COMMAND.format(width=WIDTH, height=HEIGHT, quality=QUALITY, outfile=outfile)
        )
        led.value = False
        frame += 1  # Increment image counter
        prevtime = currenttime  # Save image cap time


if __name__ == "__main__":
    main()
