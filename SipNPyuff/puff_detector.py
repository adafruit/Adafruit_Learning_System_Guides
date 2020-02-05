class PuffDetector:
    @classmethod
    def rolling_average(self, measurements):
        sum = 0
        window = 3
        for measurement in measurements[-window:]:
            sum += measurement
        return (sum/window)
    @classmethod
    def slope(self, a, b):

        if a > b:
            return 1
        elif a < b:
            return -1
        else:
            return 0


    @classmethod
    def direction(self, measurements): # requires 6 measurements
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
        direction = self.rolling_average(measurements)
        return  prev_direction != direction

