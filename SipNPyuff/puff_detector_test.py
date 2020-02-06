import unittest
from puff_detector import PuffDetector


class DirectionChangeTest(unittest.TestCase):
    def test_negative_direction(self):
        reading_list = [-1, -2, -3, -4, -5]
        self.assertEqual(PuffDetector.direction(reading_list), -1)

    def test_positive_direction(self):
        reading_list = [1, 2, 3, 4, 5, 6]

        self.assertEqual(PuffDetector.direction(reading_list), 1)

    def test_flat_direction(self):
        reading_list = [1, 1, 1, 1, 1, 1]

        self.assertEqual(PuffDetector.direction(reading_list), 0)

    def test_decreasing_positive(self):
        reading_list = [6, 5, 4, 3, 2, 1]
        self.assertEqual(PuffDetector.direction(reading_list), -1)

    def test_negative_to_positive(self):
        reading_list = [-1, -2, -3, -4, -4, -3, -2, -1]
        self.assertEqual(PuffDetector.direction_changed(reading_list, -1), True)

    def test_negative_to_negative_er(self):
        reading_list = [-1, -2, -3, -4, -5.0 - 6, -7, -8]
        self.assertEqual(PuffDetector.direction_changed(reading_list, -1), False)

    def test_positive_to_negative(self):
        reading_list = [1, 2, 3, 4, 4, 3, 2, 1]
        self.assertEqual(PuffDetector.direction_changed(reading_list, 1), True)

    def test_positive_to_positive_er(self):
        reading_list = [1, 2, 3, 4, 5, 5, 6, 7]
        print("positive-er")
        self.assertEqual(PuffDetector.direction_changed(reading_list, 1), False)


class RollingAverageTest(unittest.TestCase):
    def test_uniform_measurements(self):
        reading_list = [10, 10, 10, 10]
        self.assertEqual(PuffDetector.rolling_average(reading_list), 10)

    def test_real_average(self):
        reading_list = [10, 5, 5]
        self.assertEqual(PuffDetector.rolling_average(reading_list), 20 / 3)

    def test_rolling_average(self):
        reading_list = [0, 0, 0, 10, 5, 5]
        self.assertEqual(PuffDetector.rolling_average(reading_list), 20 / 3)

    def test_flat_average(self):
        reading_list = [1, 1, 1, 1, 1, 1]
        self.assertEqual(PuffDetector.rolling_average(reading_list), 1)
