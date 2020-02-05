class PuffDetector:
    @classmethod
    def rolling_average(self, measurements):
        measurement_sum = 0
        window_size = 3
        # print("measurements", measurements)
        window = measurements[-window_size:]

        return sum(window) / window_size

    @classmethod
    def slope(self, a, b):

        if a > b:
            return 1
        elif a < b:
            return -1
        else:
            return 0

    @classmethod
    def direction(self, measurements):  # requires 6 measurements
        average = self.rolling_average(measurements)
        prev_average = self.rolling_average(measurements[-6:-3])
        # print()
        # print("measurements:", measurements)
        # print("prev_average", prev_average)
        # print("average:", average)
        current_slope = self.slope(average, prev_average)
        # print("slope:", current_slope)
        return current_slope

    @classmethod
    def direction_changed(self, measurements, prev_direction):
        direction = self.direction(measurements)
        return prev_direction != direction
