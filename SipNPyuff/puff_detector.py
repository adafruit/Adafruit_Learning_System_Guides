import time

PRINT_FLOOR = 5
CONSOLE = True
DEBUG = True


class PuffDetector:
    def __init__(self, min_pressure=8, high_pressure=20):
        self.high_pressure = high_pressure
        self.min_pressure = min_pressure

        self.start_polarity = 0
        self.peak_level = 0
        self.counter = 0
        self.duration = 0
        self.puff_start = 0

    @classmethod
    def rolling_average(cls, measurements, window_size=3):
        # print("measurements", measurements)
        window = measurements[-window_size:]

        return sum(window) / window_size

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
        puff_polarity = None
        puff_peak_level = None
        puff_duration = None
        #######################
        polarity, level = self.catagorize_pressure(current_pressure)

        # if (polarity != 0) or (level != 0):
        if abs(current_pressure) > PRINT_FLOOR:
            if self.counter % 4 == 0:
                if DEBUG and CONSOLE:
                    print("\t\t\tpressure:", current_pressure)

        if level != 0 and self.start_polarity == 0:  ###
            self.start_polarity = polarity
            self.puff_start = time.monotonic()
            puff_polarity = self.start_polarity

        if self.start_polarity != 0:
            if level > self.peak_level:
                self.peak_level = level

        if (level == 0) and (self.start_polarity != 0):
            self.duration = time.monotonic() - self.puff_start

            puff_polarity = self.start_polarity
            puff_peak_level = self.peak_level
            puff_duration = self.duration

            self.start_polarity = 0
            self.peak_level = 0
            self.duration = 0
        self.counter += 1
        return (puff_polarity, puff_peak_level, puff_duration)
        ##############################################


# pylint:disable=pointless-string-statement
"""
pressure_list = []
    prev_pressure_type = tuple()
prev_polarity = None
current_level = 0
prev_level = 0

    def old_detect(self):
        if pressure_type != prev_pressure_type:
        puff_end = time.monotonic()
        puff_duration = puff_end - puff_start
        puff_start = puff_end
        if DEBUG and CONSOLE: print("\tpressure type:", pressure_type)
        if DEBUG and CONSOLE: print("duration:", puff_duration)
        if CONSOLE: print("polarity:", polarity, "level:", level)

        # hack to handle triggering twice on the way up or down
        if (polarity == 1) and (prev_level > level):
            if CONSOLE: print("Down")
            puff_duration += prev_duration
            level = prev_level
        if (polarity == -1) and (prev_level < level):
            if CONSOLE: print("Up")
            puff_duration += prev_duration
            level = prev_level

        if DEBUG and CONSOLE: print("polarity:", polarity, "level:", level)
        if puff_duration > 0.2:
            if CONSOLE: print("polarity:", polarity, "level:", level)

            if CONSOLE: print("\tduration:", puff_duration)
            if DEBUG and CONSOLE: print(current_pressure)
            label = detector.pressure_string((polarity, level))
            label = detector.pressure_string(pressure_type)
            if CONSOLE: print("\t\t\t\t", label)
            if CONSOLE: print("____________________")
        prev_pressure_type = pressure_type
        prev_duration = puff_duration
    prev_level = level
    prev_level = level
"""
