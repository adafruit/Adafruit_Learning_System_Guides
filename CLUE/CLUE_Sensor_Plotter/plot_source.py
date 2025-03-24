# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
`plot_source`
================================================================================
CircuitPython library for the clue-plotter application.

* Author(s): Kevin J. Walters

Implementation Notes
--------------------
**Hardware:**
* Adafruit CLUE <https://www.adafruit.com/product/4500>
**Software and Dependencies:**
* Adafruit's CLUE library: https://github.com/adafruit/Adafruit_CircuitPython_CLUE
"""

import math

import analogio


class PlotSource():
    """An abstract class for a sensor which returns the data from the sensor
       and provides some metadata useful for plotting.
       Sensors returning vector quanities like a 3-axis accelerometer are supported.
       When the source is used start() will be called and when it's not needed stop() will
       be called.

    :param values: Number of values returned by data method, between 1 and 3.
    :param name: Name of the sensor used to title the graph, only 17 characters fit on screen.
    :param units: Units for data used for y axis label.
    :param abs_min: Absolute minimum value for data, defaults to 0.
    :param abs_max: Absolute maximum value for data, defaults to 65535.
    :param initial_min: The initial minimum value suggested for y axis on graph,
           defaults to abs_min.
    :param initial_max: The initial maximum value suggested for y axis on graph,
           defaults to abs_max.
    :param range_min: A suggested minimum range to aid automatic y axis ranging.
    :param rate: The approximate rate in Hz that that data method returns in a tight loop.
    :param colors: A list of the suggested colors for data.
    :param debug: A numerical debug level, defaults to 0.
       """
    DEFAULT_COLORS = (0xffff00, 0x00ffff, 0xff0080)
    RGB_COLORS = (0xff0000, 0x00ff00, 0x0000ff)

    def __init__(self, values, name, units="",
                 abs_min=0, abs_max=65535, initial_min=None, initial_max=None,
                 range_min=None,
                 rate=None, colors=None, debug=0):
        if type(self) == PlotSource:  # pylint: disable=unidiomatic-typecheck
            raise TypeError("PlotSource must be subclassed")
        self._values = values
        self._name = name
        self._units = units
        self._abs_min = abs_min
        self._abs_max = abs_max
        self._initial_min = initial_min if initial_min is not None else abs_min
        self._initial_max = initial_max if initial_max is not None else abs_max
        if range_min is None:
            self._range_min = (abs_max - abs_min) / 100  # 1% of full range
        else:
            self._range_min = range_min
        self._rate = rate
        if colors is not None:
            self._colors = colors
        else:
            self._colors = self.DEFAULT_COLORS[:values]
        self._debug = debug

    def __str__(self):
        return self._name

    def data(self):
        """Data sample from the sensor.

           :return: A single numerical value or an array or tuple for vector values.
           """
        raise NotImplementedError()

    def min(self):
        return self._abs_min

    def max(self):
        return self._abs_max

    def initial_min(self):
        return self._initial_min

    def initial_max(self):
        return self._initial_max

    def range_min(self):
        return self._range_min

    def start(self):
        pass

    def stop(self):
        pass

    def values(self):
        return self._values

    def units(self):
        return self._units

    def rate(self):
        return self._rate

    def colors(self):
        return self._colors


# This over-reads presumably due to electronics warming the board
# It also looks odd on close inspection as it climbs about 0.1C if
# it's read frequently
# Data sheet say operating temperature is -40C to 85C
class TemperaturePlotSource(PlotSource):
    def _convert(self, value):
        return value * self._scale + self._offset

    def __init__(self, my_clue, mode="Celsius"):
        self._clue = my_clue
        range_min = 0.8
        if mode[0].lower() == "f":
            mode_name = "Fahrenheit"
            self._scale = 1.8
            self._offset = 32.0
            range_min = 1.6
        elif mode[0].lower() == "k":
            mode_name = "Kelvin"
            self._scale = 1.0
            self._offset = 273.15
        else:
            mode_name = "Celsius"
            self._scale = 1.0
            self._offset = 0.0
        super().__init__(1, "Temperature",
                         units=mode_name[0],
                         abs_min=self._convert(-40),
                         abs_max=self._convert(85),
                         initial_min=self._convert(10),
                         initial_max=self._convert(40),
                         range_min=range_min,
                         rate=24)

    def data(self):
        return self._convert(self._clue.temperature)


# The 300, 1100 values are in adafruit_bmp280 but are private variables
class PressurePlotSource(PlotSource):
    def _convert(self, value):
        return value * self._scale

    def __init__(self, my_clue, mode="M"):
        self._clue = my_clue
        if mode[0].lower() == "i":
            # 29.92 inches mercury equivalent to 1013.25mb in ISA
            self._scale = 29.92 / 1013.25
            units = "inHg"
            range_min = 0.04
        else:
            self._scale = 1.0
            units = "hPa"  # AKA millibars (mb)
            range_min = 1

        super().__init__(1, "Pressure", units=units,
                         abs_min=self._convert(300), abs_max=self._convert(1100),
                         initial_min=self._convert(980), initial_max=self._convert(1040),
                         range_min=range_min,
                         rate=22)

    def data(self):
        return self._convert(self._clue.pressure)


class ProximityPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(1, "Proximity",
                         abs_min=0, abs_max=255,
                         rate=720)

    def data(self):
        return self._clue.proximity


class HumidityPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(1, "Rel. Humidity", units="%",
                         abs_min=0, abs_max=100, initial_min=20, initial_max=60,
                         rate=54)

    def data(self):
        return self._clue.humidity

# If clue.touch_N has not been used then it doesn't instantiate
# the TouchIn object so there's no problem with creating an AnalogIn...
class PinPlotSource(PlotSource):
    def __init__(self, pin):
        try:
            pins = [p for p in pin]
        except TypeError:
            pins = [pin]

        self._pins = pins
        self._analogin = [analogio.AnalogIn(p) for p in pins]
        # Assumption here that reference_voltage is same for all
        # 3.3V graphs nicely with rounding up to 4.0V
        self._reference_voltage = self._analogin[0].reference_voltage
        self._conversion_factor = self._reference_voltage / (2**16 - 1)
        super().__init__(len(pins),
                         "Pad: " + ", ".join([str(p).split('.')[-1] for p in pins]),
                         units="V",
                         abs_min=0.0, abs_max=math.ceil(self._reference_voltage),
                         rate=10000)

    def data(self):
        if len(self._analogin) == 1:
            return self._analogin[0].value * self._conversion_factor
        else:
            return tuple([ana.value * self._conversion_factor
                          for ana in self._analogin])

    def pins(self):
        return self._pins


class ColorPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(3, "Color: R, G, B",
                         abs_min=0, abs_max=8000,  # 7169 looks like max
                         rate=50,
                         colors=self.RGB_COLORS,
                        )

    def data(self):
        (r, g, b, _) = self._clue.color  # fourth value is clear value
        return (r, g, b)

    def start(self):
        # These values will affect the maximum return value
        # Set APDS9660 to sample every (256 - 249 ) * 2.78 = 19.46ms
        # pylint: disable=protected-access
        self._clue._sensor.integration_time = 249  # 19.46ms, ~ 50Hz
        self._clue._sensor.color_gain = 0x02  # 16x (library default is 4x)


class IlluminatedColorPlotSource(PlotSource):
    def __init__(self, my_clue, mode="Clear"):
        self._clue = my_clue
        col_fl_lc = mode[0].lower()
        if col_fl_lc == "r":
            plot_colour = self.RGB_COLORS[0]
        elif col_fl_lc == "g":
            plot_colour = self.RGB_COLORS[1]
        elif col_fl_lc == "b":
            plot_colour = self.RGB_COLORS[2]
        elif col_fl_lc == "c":
            plot_colour = self.DEFAULT_COLORS[0]
        else:
            raise ValueError("Colour must be Red, Green, Blue or Clear")

        self._channel = col_fl_lc
        super().__init__(1, "Illum. color: " + self._channel.upper(),
                         abs_min=0, abs_max=8000,
                         initial_min=0, initial_max=2000,
                         colors=(plot_colour,),
                         rate=50)

    def data(self):
        (r, g, b, c) = self._clue.color
        if self._channel == "r":
            return r
        elif self._channel == "g":
            return g
        elif self._channel == "b":
            return b
        elif self._channel == "c":
            return c
        else:
            return None  # This should never happen

    def start(self):
        # Set APDS9660 to sample every (256 - 249 ) * 2.78 = 19.46ms
        # pylint: disable=protected-access
        self._clue._sensor.integration_time = 249  # 19.46ms, ~ 50Hz
        self._clue._sensor.color_gain = 0x03  # 64x (library default is 4x)

        self._clue.white_leds = True

    def stop(self):
        self._clue.white_leds = False


class VolumePlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(1, "Volume", units="dB",
                         abs_min=0, abs_max=97+3,   # 97dB is 16bit dynamic range
                         initial_min=10, initial_max=60,
                         rate=41)

    # 20 due to conversion of amplitude of signal
    _LN_CONVERSION_FACTOR = 20 / math.log(10)

    def data(self):
        return (math.log(self._clue.sound_level + 1)
                * self._LN_CONVERSION_FACTOR)


# This appears not to be a blocking read in terms of waiting for a
# a genuinely newvalue from the sensor
# CP standard says this should be radians per second but library
# currently returns degrees per second
# https://circuitpython.readthedocs.io/en/latest/docs/design_guide.html
# https://github.com/adafruit/Adafruit_CircuitPython_LSM6DS/issues/9
class GyroPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(3, "Gyro", units="dps",
                         abs_min=-287-13, abs_max=287+13,  # 286.703 appears to be max
                         initial_min=-100, initial_max=100,
                         colors=self.RGB_COLORS,
                         rate=500)

    def data(self):
        return self._clue.gyro


class AccelerometerPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(3, "Accelerometer", units="ms-2",
                         abs_min=-40, abs_max=40,  # 39.1992 approx max
                         initial_min=-20, initial_max=20,
                         colors=self.RGB_COLORS,
                         rate=500)

    def data(self):
        return self._clue.acceleration


class MagnetometerPlotSource(PlotSource):
    def __init__(self, my_clue):
        self._clue = my_clue
        super().__init__(3, "Magnetometer", units="uT",
                         abs_min=-479-21, abs_max=479+21,  # 478.866 approx max
                         initial_min=-80, initial_max=80,  # Earth around 60uT
                         colors=self.RGB_COLORS,
                         rate=500)

    def data(self):
        return self._clue.magnetic
