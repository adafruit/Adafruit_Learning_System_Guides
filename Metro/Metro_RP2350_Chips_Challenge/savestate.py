# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
from math import floor
import json
import board
from microcontroller import nvm
from digitalio import DigitalInOut, Pull
import busio
import sdcardio
import storage

SAVESTATE_FILE = "chips.json"

class SaveState:
    def __init__(self):
        self._levels = {}
        self._has_sdcard = self._mount_sd_card()
        if self._has_sdcard:
            print("SD Card detected")
        else:
            print("SD Card not detected. Level data will NOT be saved.")
        self.load()
        self._sdcard = None

    def _mount_sd_card(self):
        self._card_detect = DigitalInOut(board.SD_CARD_DETECT)
        self._card_detect.switch_to_input(pull=Pull.UP)
        if self._card_detect.value:
            return False

        # Attempt to unmount the SD card
        try:
            storage.umount("/sd")
        except OSError:
            pass

        spi = busio.SPI(board.SD_SCK, MOSI=board.SD_MOSI, MISO=board.SD_MISO)

        try:
            sdcard = sdcardio.SDCard(spi, board.SD_CS, baudrate=20_000_000)
            vfs = storage.VfsFat(sdcard)
            storage.mount(vfs, "/sd")
        except OSError:
            return False

        return True

    def save(self):
        if not self._has_sdcard:
            return
        with open("/sd/" + SAVESTATE_FILE, "w") as f:
            json.dump({"levels": self._levels}, f)

    def load(self):
        if not self._has_sdcard:
            return
        # Use try in case the file doesn't exist
        try:
            with open("/sd/" + SAVESTATE_FILE, "r") as f:
                data = json.load(f)
                self._levels = data["levels"]
        except (OSError, ValueError):
            pass

    def set_level_score(self, level, score, time_left):
        level_key = f"level{level}"
        new_high_score = False
        lower_time = False
        if level_key not in self._levels:
            self._levels[level_key] = {}
        if score > self._levels[level_key].get("score", 0):
            new_high_score = True
            self._levels[level_key]["score"] = score
        if time_left > self._levels[level_key].get("time_left", 0):
            lower_time = True
            self._levels[level_key]["time_left"] = time_left

        self.save()
        return new_high_score, lower_time

    def add_level_password(self, level, password):
        nvm[0] = level
        for byte, char in enumerate(password):
            nvm[1 + byte] = ord(char)
        level_key = f"level{level}"
        if level_key not in self._levels:
            self._levels[level_key] = {}
        self._levels[level_key]["password"] = password.upper()
        self.save()

    def find_unlocked_level(self, level_or_password):
        if isinstance(level_or_password, int):
            level_key = f"level{level_or_password}"
            password = None
        else:
            level_key = None
            password = level_or_password

        # Look for level by number
        if level_key in self._levels:
            return level_or_password

        for key, data in self._levels.items():
            if "password" in data and data["password"] == password:
                return int(key[5:])

        return None

    def calculate_score(self, level, time_left, deaths):
        time_bonus = time_left * 10
        level_bonus = floor(level * 500 * 0.8**deaths)
        level_score = time_bonus + level_bonus
        total_score = self.total_score
        return time_bonus, level_bonus, level_score, total_score

    def has_password(self, level, password):
        level_key = f"level{level}"
        if level_key in self._levels:
            return self._levels[level_key]["password"] == password.upper()
        return False

    def level_score(self, level):
        level_key = f"level{level}"
        if (level_key in self._levels and "score" in self._levels[level_key] and
            "time_left" in self._levels[level_key]):
            return self._levels[level_key]["score"], self._levels[level_key]["time_left"]
        return 0, 0

    def is_level_unlocked(self, level):
        level_key = f"level{level}"
        if level_key in self._levels and "password" in self._levels[level_key]:
            return True
        return False

    @property
    def has_sdcard(self):
        return self._has_sdcard

    @property
    def total_score(self):
        total_score = 0
        for data in self._levels.values():
            if "score" in data:
                total_score += data["score"]
        return total_score

    @property
    def total_completed_levels(self):
        completed_levels = 0
        for data in self._levels.values():
            if "score" in data:
                completed_levels += 1
        return completed_levels
