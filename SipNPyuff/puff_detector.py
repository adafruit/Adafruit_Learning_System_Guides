class PuffDetector:
    def __init__(self, min_pressure=8, high_pressure=20):
        self.high_pressure = high_pressure
        self.min_pressure = min_pressure

    @classmethod
    def rolling_average(cls, measurements, window_size=3):
        # print("measurements", measurements)
        window = measurements[-window_size:]

        return sum(window) / window_size

    @classmethod
    def slope(cls, a, b):

        if a > b:
            return 1
        elif a < b:
            return -1
        else:
            return 0

    @classmethod
    def direction(cls, measurements):  # requires 6 measurements
        average = cls.rolling_average(measurements)
        prev_average = cls.rolling_average(measurements[-6:-3])
        # print()
        # print("measurements:", measurements)
        # print("prev_average", prev_average)
        # print("average:", average)
        current_slope = cls.slope(average, prev_average)
        # print("slope:", current_slope)
        return current_slope

    @classmethod
    def direction_changed(cls, measurements, prev_direction):
        direction = cls.direction(measurements)
        return prev_direction != direction

    def catagorize_pressure(self, pressure, prev_pressure):
        """determine the strength and polarity of the pressure reading"""
        level = 0
        direction = 0
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

        if pressure > prev_pressure:
            direction = 1
        if pressure < prev_pressure:
            direction = -1

        return (polarity, level, direction)

    @staticmethod
    def pressure_string(pressure_type):
        polarity, level, direction = pressure_type  # pylint:disable=unused-variable
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


# pylint:disable=pointless-string-statement
"""
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
"""
