# SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
from PIL import Image, ImageOps

# pylint: disable=too-few-public-methods
class Frame:
    def __init__(self, duration=0):
        self.duration = duration
        self.image = None


# pylint: enable=too-few-public-methods


class AnimatedGif:
    def __init__(self, display, include_delays=True, folder=None):
        self._frame_count = 0
        self._loop = 0
        self._index = 0
        self._duration = 0
        self._gif_files = []
        self._frames = []
        self._running = True
        self.display = display
        self.include_delays = include_delays
        if folder is not None:
            self.load_files(folder)
            self.run()

    def advance(self):
        self._index = (self._index + 1) % len(self._gif_files)

    def back(self):
        self._index = (self._index - 1 + len(self._gif_files)) % len(self._gif_files)

    def load_files(self, folder):
        gif_files = [f for f in os.listdir(folder) if f.endswith(".gif")]
        gif_folder = folder
        if gif_folder[:-1] != "/":
            gif_folder += "/"
        for gif_file in gif_files:
            image = Image.open(gif_folder + gif_file)
            # Only add animated Gifs
            if image.is_animated:
                self._gif_files.append(gif_folder + gif_file)

        print("Found", self._gif_files)
        if not self._gif_files:
            print("No Gif files found in current folder")
            exit()  # pylint: disable=consider-using-sys-exit

    def preload(self):
        image = Image.open(self._gif_files[self._index])
        print("Loading {}...".format(self._gif_files[self._index]))
        if "duration" in image.info:
            self._duration = image.info["duration"]
        else:
            self._duration = 0
        if "loop" in image.info:
            self._loop = image.info["loop"]
        else:
            self._loop = 1
        self._frame_count = image.n_frames
        self._frames.clear()
        for frame in range(self._frame_count):
            image.seek(frame)
            # Create blank image for drawing.
            # Make sure to create image with mode 'RGB' for full color.
            frame_object = Frame(duration=self._duration)
            if "duration" in image.info:
                frame_object.duration = image.info["duration"]
            frame_object.image = ImageOps.pad(  # pylint: disable=no-member
                image.convert("RGB"),
                (self._width, self._height),
                method=Image.NEAREST,
                color=(0, 0, 0),
                centering=(0.5, 0.5),
            )
            self._frames.append(frame_object)

    def play(self):
        self.preload()
        current_frame = 0
        last_action = None
        # Check if we have loaded any files first
        if not self._gif_files:
            print("There are no Gif Images loaded to Play")
            return False
        self.update_display(self._frames[current_frame].image)
        while self._running:
            action = self.get_next_value()
            if action:
                if not last_action:
                    last_action = action
                if action == "click":
                    self.advance()
                    return False
                elif int(action) < int(last_action):
                    current_frame -= 1
                else:
                    current_frame += 1
                current_frame %= self._frame_count
                frame_object = self._frames[current_frame]
                start_time = time.monotonic()
                self.update_display(frame_object.image)
                if self.include_delays:
                    remaining_delay = frame_object.duration / 1000 - (
                        time.monotonic() - start_time
                    )
                    if remaining_delay > 0:
                        time.sleep(remaining_delay)
                last_action = action
                if self._loop == 1:
                    return True
                if self._loop > 0:
                    self._loop -= 1

    def run(self):
        while self._running:
            auto_advance = self.play()
            if auto_advance:
                self.advance()
