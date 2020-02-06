class PuffDetector:

    def __init__(self, min_pressure=8, high_pressure=20):
        self.high_pressure=high_pressure
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

    def catagorize_pressure(self, pressure):
        """determine the strength and polarity of the pressure reading"""
        level = 0
        direction = 0
        abs_pressure = abs(pressure)

        if abs_pressure > self.min_pressure:
            level = 1
        if abs_pressure > self.high_pressure:
            level = 2

        if level != 0:
            if pressure > 0:
                direction = 1
            else:
                direction = -1

        return (direction, level)

    @staticmethod
    def pressure_string(pressure_type):
        direction, level = pressure_type
        pressure_str = "HIGH"
        if level == 0 or direction == 0:
            return ""
        # print("pressure level:", level)
        if level == 1:
            pressure_str = "LOW"
        elif level == 2:
            pressure_str = "HIGH"

        if direction == 1:
            pressure_str += "PUFF"
        elif direction == -1:
            pressure_str += "SIP"
        return pressure_str
