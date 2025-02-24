# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# The MIT License (MIT)
#
# Copyright (c) 2020 Kevin J. Walters
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import os

import unittest
from unittest.mock import Mock, MagicMock, PropertyMock

verbose = int(os.getenv('TESTVERBOSE', '2'))

# Mocking libraries which are about to be import'd by Plotter
sys.modules['analogio'] = MagicMock()

# Borrowing the dhalbert/tannewt technique from adafruit/Adafruit_CircuitPython_Motor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import what we are testing or will test in future
# pylint: disable=unused-import,wrong-import-position
from plot_source import PlotSource, TemperaturePlotSource, PressurePlotSource, \
                        HumidityPlotSource, ColorPlotSource, ProximityPlotSource, \
                        IlluminatedColorPlotSource, VolumePlotSource, \
                        AccelerometerPlotSource, GyroPlotSource, \
                        MagnetometerPlotSource, PinPlotSource


# pylint: disable=protected-access
class Test_TemperaturePlotSource(unittest.TestCase):

    SENSOR_DATA = (20, 21.3, 22.0, 0.0, -40, 85)

    def test_celsius(self):
        """Create the source in Celsius mode and test with some values."""

        # Emulate the clue's temperature sensor by
        # returning a temperature from a small tuple
        # of test data
        mocked_clue = Mock()
        expected_data = self.SENSOR_DATA
        type(mocked_clue).temperature = PropertyMock(side_effect=self.SENSOR_DATA)

        source = TemperaturePlotSource(mocked_clue,
                                       mode="Celsius")

        for expected_value in expected_data:
            self.assertAlmostEqual(source.data(),
                                   expected_value,
                                   msg="Checking converted temperature is correct")

    def test_fahrenheit(self):
        """Create the source in Fahrenheit mode and test with some values."""
        # Emulate the clue's temperature sensor by
        # returning a temperature from a small tuple
        # of test data
        mocked_clue = Mock()
        expected_data = (68, 70.34, 71.6,
                         32.0, -40, 185)
        type(mocked_clue).temperature = PropertyMock(side_effect=self.SENSOR_DATA)

        source = TemperaturePlotSource(mocked_clue,
                                       mode="Fahrenheit")

        for expected_value in expected_data:
            self.assertAlmostEqual(source.data(),
                                   expected_value,
                                   msg="Checking converted temperature is correct")

    def test_kelvin(self):
        """Create the source in Kelvin mode and test with some values."""
        # Emulate the clue's temperature sensor by
        # returning a temperature from a small tuple
        # of test data
        mocked_clue = Mock()
        expected_data = (293.15, 294.45, 295.15,
                         273.15, 233.15, 358.15)
        type(mocked_clue).temperature = PropertyMock(side_effect=self.SENSOR_DATA)

        source = TemperaturePlotSource(mocked_clue,
                                       mode="Kelvin")

        for expected_value in expected_data:
            data = source.data()
            # self.assertEqual(data,
            #                 expected_value,
            #                 msg="An inappropriate check for floating-point")
            self.assertAlmostEqual(data,
                                   expected_value,
                                   msg="Checking converted temperature is correct")


if __name__ == '__main__':
    unittest.main(verbosity=verbose)
