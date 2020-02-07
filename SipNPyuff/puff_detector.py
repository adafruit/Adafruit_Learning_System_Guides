import time
import os
import json

CONSOLE = False
DEBUG = True

MIN_PRESSURE = 8
HIGH_PRESSURE = 40
WAITING = 0
STARTED = 1
DETECTED = 2


class PuffDetector:
    def __init__(
            self,
            min_pressure=MIN_PRESSURE,
            high_pressure=HIGH_PRESSURE,
            config_filename="settings.json",
            display_timeout=1,
    ):
        self.high_pressure = high_pressure
        self.min_pressure = min_pressure

        self.start_polarity = 0
        self.peak_level = 0
        self.counter = 0
        self.duration = 0
        self.puff_start = 0
        self.state = WAITING
        self.settings_dict = {}

        self.display_timeout = display_timeout

        self._config_filename = config_filename
        self._load_config()
        if self.settings_dict:
            self.min_pressure = self.settings_dict["min_pressure"]
            self.high_pressure = self.settings_dict["high_pressure"]
            if "display_timeout" in self.settings_dict.keys():
                self.display_timeout = self.settings_dict["display_timeout"]

    def _load_config(self):
        if not self._config_filename in os.listdir("/"):
            return
        try:
            with open(self._config_filename, "r") as file:
                self.settings_dict = json.load(file)
        except (ValueError, OSError) as error:
            print("Error loading config file")
            print(type(error))

    def catagorize_pressure(self, pressure):
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

    @staticmethod
    def pressure_string(pressure_type):
        polarity, level = pressure_type  # pylint:disable=unused-variable
        pressure_str = "HIGH"
        if level == 0 or polarity == 0:
            return ""
        # print("pressure level:", level)
        if level == 1:
            pressure_str = "LOW"
        elif level == 2:
            pressure_str = "HIGH"

        if polarity == 1:
            pressure_str += "PUFF"
        elif polarity == -1:
            pressure_str += "SIP"
        return pressure_str

    def check_for_puff(self, current_pressure):
        """Updates the internal state to detect if a sip/puff has been started or stopped"""
        puff_peak_level = None
        puff_duration = None
        polarity, level = self.catagorize_pressure(current_pressure)

        if self.state == DETECTED:
            # if polarity == 0 and level == 0:
            self.state = WAITING

            self.start_polarity = 0
            self.peak_level = 0
            self.duration = 0
        if level != 0 and self.start_polarity == 0:
            self.state = STARTED
            self.start_polarity = polarity
            self.puff_start = time.monotonic()

        if self.state == STARTED:
            # if self.start_polarity != 0:
            if level > self.peak_level:
                self.peak_level = level

        # if (level == 0) and (self.start_polarity != 0):
        if (level == 0) and (self.state == STARTED):
            self.state = DETECTED
            self.duration = time.monotonic() - self.puff_start

            puff_peak_level = self.peak_level
            puff_duration = self.duration

        self.counter += 1
        return (self.start_polarity, puff_peak_level, puff_duration)
