# SPDX-FileCopyrightText: 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import json
import board
import terminalio
from adafruit_display_text import label
from displayio import Group
import displayio
import i2cdisplaybus
import adafruit_displayio_ssd1306
import adafruit_lps35hw

CONSOLE = False
DEBUG = True

MIN_PRESSURE = 8
HIGH_PRESSURE = 40
WAITING = 0
STARTED = 1
DETECTED = 2

SOFT_SIP = 0
HARD_SIP = 1
SOFT_PUFF = 2
HARD_PUFF = 3

SOFT = 1
STRONG = 2

COLOR = 0xFFFFFF
FONT = terminalio.FONT

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
Y_OFFSET = 3
TEXT_HEIGHT = 8
BOTTOM_ROW = DISPLAY_HEIGHT - TEXT_HEIGHT
BANNER_STRING = "ST LPS33HW Sip & Puff"
pressure_string = " "
input_type_string = " "
# pylint:disable=too-many-locals,exec-used,eval-used


class PuffDetector:
    def __init__(
        self,
        min_pressure=MIN_PRESSURE,
        high_pressure=HIGH_PRESSURE,
        config_filename="settings.json",
        display_timeout=1,
    ):
        # misc detection state
        self.current_pressure = 0
        self.current_polarity = 0
        self.current_time = time.monotonic()
        self.start_polarity = 0
        self.peak_level = 0
        self.puff_start = 0
        self.duration = 0
        self.state = WAITING
        self.prev_state = self.state

        # settings
        self.settings_dict = {}
        self.high_pressure = high_pressure
        self.min_pressure = min_pressure
        self._config_filename = config_filename
        self._load_config()

        # callbacks
        self._on_sip_callbacks = []
        self._on_puff_callbacks = []

        # display and display state
        self.display = None
        self.state_display_start = self.current_time
        self.detection_result_str = " "
        self.duration_str = " "
        self.min_press_str = " "
        self.high_press_str = " "
        self.state_str = " "
        self.press_str = " "
        self.display_timeout = display_timeout
        self._init_stuff()

    def _init_stuff(self):

        # decouple display
        self.state_display_timeout = 1.0
        self.state_display_start = 0
        displayio.release_displays()
        i2c = board.I2C()

        display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3D)
        self.display = adafruit_displayio_ssd1306.SSD1306(
            display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT
        )

        self.min_press_str = "min: %d" % self.min_pressure
        self.high_press_str = "hi: %d" % self.high_pressure

        self.pressure_sensor = adafruit_lps35hw.LPS35HW(i2c)
        self.pressure_sensor.zero_pressure()
        self.pressure_sensor.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ

        self.pressure_sensor.filter_enabled = True
        self.pressure_sensor.filter_config = True

    def _load_config(self):
        if not self._config_filename in os.listdir("/"):
            return
        try:
            with open(self._config_filename, "r") as file:
                self.settings_dict = json.load(file)
        except (ValueError, OSError) as error:
            print("Error loading config file")
            print(type(error))

        if self.settings_dict:
            if "MIN_PRESSURE" in self.settings_dict.keys():
                self.min_pressure = self.settings_dict["MIN_PRESSURE"]
            if "HIGH_PRESSURE" in self.settings_dict.keys():
                self.high_pressure = self.settings_dict["HIGH_PRESSURE"]
            if "DISPLAY_TIMEOUT" in self.settings_dict.keys():
                self.display_timeout = self.settings_dict["DISPLAY_TIMEOUT"]

    def check_for_events(self):
        self.current_time = time.monotonic()
        self.current_pressure = self.pressure_sensor.pressure
        self._update_state()
        self._notify_callbacks()
        self._update_display()

    def run(self):
        while True:
            self.check_for_events()

    def _categorize_pressure(self, pressure):
        """determine the strength and polarity of the pressure reading"""
        level = 0
        polarity = 0
        abs_pressure = abs(pressure)

        if abs_pressure > self.min_pressure:
            level = 1
        if abs_pressure > self.high_pressure:
            level = 2

        if level != 0:
            if pressure > 0:
                polarity = 1
            else:
                polarity = -1

        return (polarity, level)

    def on_sip(self, func):
        self.add_on_sip(func)
        return func

    def on_puff(self, func):
        self.add_on_puff(func)
        return func

    def add_on_sip(self, new_callback):
        self._on_sip_callbacks.append(new_callback)

    def add_on_puff(self, new_callback):
        self._on_puff_callbacks.append(new_callback)

    def _update_state(self):
        """Updates the internal state to detect if a sip/puff has been started or stopped"""

        self.current_polarity, level = self._categorize_pressure(self.current_pressure)

        if self.state == DETECTED:
            self.state = WAITING

            self.start_polarity = 0
            self.peak_level = 0
            self.duration = 0

        if (self.state == WAITING) and level != 0 and (self.start_polarity == 0):
            self.state = STARTED
            self.start_polarity = self.current_polarity
            self.puff_start = time.monotonic()

        if self.state == STARTED:
            if level > self.peak_level:
                self.peak_level = level

            if level == 0:
                self.state = DETECTED
                self.duration = time.monotonic() - self.puff_start

    def _notify_callbacks(self):
        state_changed = self.prev_state != self.state
        self.prev_state = self.state
        if not state_changed:
            return

        if self.state == DETECTED:

            # if this is a sip
            if self.start_polarity == -1:
                for on_sip_callback in self._on_sip_callbacks:
                    on_sip_callback(self.peak_level, self.duration)

            # if this is a sip
            if self.start_polarity == 1:
                for on_puff_callback in self._on_puff_callbacks:
                    on_puff_callback(self.peak_level, self.duration)

    def _update_display_strings(self):

        self.press_str = "Press: %0.3f" % self.current_pressure

        if self.state == DETECTED:
            self.duration_str = "Duration: %0.2f" % self.duration

            self.state_str = "DETECTED:"
            if self.start_polarity == -1:
                if self.peak_level == STRONG:
                    self.detection_result_str = "STRONG SIP"
                if self.peak_level == SOFT:
                    self.detection_result_str = "SOFT SIP"

            if self.start_polarity == 1:
                if self.peak_level == STRONG:
                    self.detection_result_str = "STRONG PUFF"
                if self.peak_level == SOFT:
                    self.detection_result_str = "SOFT PUFF"

            self.state_display_start = self.current_time

        elif self.state == WAITING:
            display_elapsed = self.current_time - self.state_display_start
            if display_elapsed > self.display_timeout:
                self.detection_result_str = " "
                self.duration_str = " "
                self.detection_result_str = " "
                self.state_str = "WAITING FOR INPUT"
        elif self.state == STARTED:
            if self.start_polarity == -1:
                self.state_str = "SIP STARTED..."

            if self.start_polarity == 1:
                self.state_str = "PUFF STARTED..."

    def _update_display(self):
        self._update_display_strings()
        banner = label.Label(FONT, text=BANNER_STRING, color=COLOR)
        state = label.Label(FONT, text=self.state_str, color=COLOR)
        detector_result = label.Label(FONT, text=self.detection_result_str, color=COLOR)
        duration = label.Label(FONT, text=self.duration_str, color=COLOR)
        min_pressure_label = label.Label(FONT, text=self.min_press_str, color=COLOR)
        high_pressure_label = label.Label(FONT, text=self.high_press_str, color=COLOR)
        pressure_label = label.Label(FONT, text=self.press_str, color=COLOR)

        banner.x = 0
        banner.y = 0 + Y_OFFSET

        state.x = 10
        state.y = 10 + Y_OFFSET

        detector_result.x = 10
        detector_result.y = 20 + Y_OFFSET

        duration.x = 10
        duration.y = 30 + Y_OFFSET

        min_pressure_label.x = 0
        min_pressure_label.y = BOTTOM_ROW - 10

        pressure_label.x = DISPLAY_WIDTH - pressure_label.bounding_box[2]
        pressure_label.y = BOTTOM_ROW

        high_pressure_label.x = 0
        high_pressure_label.y = BOTTOM_ROW

        splash = Group()
        splash.append(banner)
        splash.append(state)
        splash.append(detector_result)
        splash.append(duration)
        splash.append(min_pressure_label)
        splash.append(high_pressure_label)
        splash.append(pressure_label)

        self.display.root_group = splash
