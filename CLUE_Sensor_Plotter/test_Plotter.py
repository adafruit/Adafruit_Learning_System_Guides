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
import time
import array
import os

import unittest
from unittest.mock import Mock, MagicMock, patch

import numpy

verbose = int(os.getenv('TESTVERBOSE', '2'))

# Mocking libraries which are about to be import'd by Plotter
sys.modules['board'] = MagicMock()
sys.modules['displayio'] = MagicMock()
sys.modules['terminalio'] = MagicMock()
sys.modules['adafruit_display_text.label'] = MagicMock()

# Replicate CircuitPython's time.monotonic_ns() pre 3.5
if not hasattr(time, "monotonic_ns"):
    time.monotonic_ns = lambda: int(time.monotonic() * 1e9)


# Borrowing the dhalbert/tannewt technique from adafruit/Adafruit_CircuitPython_Motor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pylint: disable=wrong-import-position
# import what we are testing
from plotter import Plotter

import terminalio  # mocked
terminalio.FONT = Mock()
terminalio.FONT.get_bounding_box = Mock(return_value=(6, 14))


# TODO use setup() and tearDown()
# - https://docs.python.org/3/library/unittest.html#unittest.TestCase.tearDown


# pylint: disable=protected-access, no-self-use, too-many-locals
class Test_Plotter(unittest.TestCase):
    """Tests for Plotter.
       Very useful but code needs a good tidy particulary around widths,
       lots of 200 hard-coded numbers.
       Would benefit from testing different widths too."""
    # These were the original dimensions of the Bitmap
    # Current clue-plotter uses 192 for width and
    # scrolling is set to 50
    _PLOT_WIDTH = 200
    _PLOT_HEIGHT = 201
    _SCROLL_PX = 25

    def count_nz_rows(self, bitmap):
        nz_rows = []
        for y_pos in range(self._PLOT_HEIGHT):
            count = 0
            for x_pos in range(self._PLOT_WIDTH):
                if bitmap[x_pos, y_pos] != 0:
                    count += 1
            if count > 0:
                nz_rows.append(y_pos)
        return nz_rows

    def aprint_plot(self, bitmap):
        for y in range(self._PLOT_HEIGHT):
            for x in range(self._PLOT_WIDTH):
                print("X" if bitmap[x][y] else " ", end="")
            print()

    def make_a_Plotter(self, style, mode, scale_mode=None):
        mocked_display = Mock()

        plotter = Plotter(mocked_display,
                          style=style,
                          mode=mode,
                          scale_mode=scale_mode,
                          scroll_px=self._SCROLL_PX,
                          plot_width=self._PLOT_WIDTH,
                          plot_height=self._PLOT_HEIGHT,
                          title="Debugging",
                          max_title_len=99,
                          mu_output=False,
                          debug=0)

        return plotter

    def ready_plot_source(self, plttr, source):
        #source_name = str(source)

        plttr.clear_all()
        #plttr.title = source_name
        #plttr.y_axis_lab = source.units()
        plttr.y_range = (source.initial_min(), source.initial_max())
        plttr.y_full_range = (source.min(), source.max())
        plttr.y_min_range = source.range_min()
        channels_from_source = source.values()
        plttr.channels = channels_from_source
        plttr.channel_colidx = (1, 2, 3)
        source.start()
        return (source, channels_from_source)

    def make_a_PlotSource(self, channels = 1):
        ps = Mock()
        ps.initial_min = Mock(return_value=-100.0)
        ps.initial_max = Mock(return_value=100.0)
        ps.min = Mock(return_value=-100.0)
        ps.max = Mock(return_value=100.0)
        ps.range_min = Mock(return_value=5.0)
        if channels == 1:
            ps.values = Mock(return_value=channels)
            ps.data = Mock(side_effect=list(range(10,90)) * 100)
        elif channels == 3:
            ps.values = Mock(return_value=channels)
            ps.data = Mock(side_effect=list(zip(list(range(10,90)),
                                                list(range(15,95)),
                                                list(range(40,60)) * 4)) * 100)
        return ps


    def make_a_PlotSource_narrowrange(self):
        ps = Mock()
        ps.initial_min = Mock(return_value=0.0)
        ps.initial_max = Mock(return_value=500.0)
        ps.min = Mock(return_value=0.0)
        ps.max = Mock(return_value=500.0)
        ps.range_min = Mock(return_value=5.0)

        ps.values = Mock(return_value=1)
        # 24 elements repeated 13 times ranging between 237 and 253
        # 5 elements repeated 6000 times
        ps.data = Mock(side_effect=(list(range(237, 260 + 1)) * 13
                                    + list(range(100, 400 + 1, 75)) * 6000))
        return ps


    def make_a_PlotSource_onespike(self):
        ps = Mock()
        ps.initial_min = Mock(return_value=-100.0)
        ps.initial_max = Mock(return_value=100.0)
        ps.min = Mock(return_value=-100.0)
        ps.max = Mock(return_value=100.0)
        ps.range_min = Mock(return_value=5.0)

        ps.values = Mock(return_value=1)
        ps.data = Mock(side_effect=([0]*95 + [5,10,20,50,80,90,70,30,20,10]
                                    + [0] * 95 + [1] * 1000))

        return ps

    def make_a_PlotSource_bilevel(self, first_v=60, second_v=700):
        ps = Mock()
        ps.initial_min = Mock(return_value=-100.0)
        ps.initial_max = Mock(return_value=100.0)
        ps.min = Mock(return_value=-1000.0)
        ps.max = Mock(return_value=1000.0)
        ps.range_min = Mock(return_value=10.0)

        ps.values = Mock(return_value=1)
        ps.data = Mock(side_effect=[first_v] * 199 + [second_v] * 1001)

        return ps


    def test_spike_after_wrap_and_overwrite_one_channel(self):
        """A specific test to check that a spike that appears in wrap mode is
           correctly cleared by subsequent flat data."""
        plotter = self.make_a_Plotter("lines", "wrap")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_source1 = self.make_a_PlotSource_onespike()
        self.ready_plot_source(plotter, test_source1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Fill screen
        for _ in range(200):
            plotter.data_add((test_source1.data(),))

        unique2, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique2 == [0, 1]),
                        "Checking pixels are now a mix of 0 and 1")

        # Rewrite whole screen with new data as we are in wrap mode
        for _ in range(190):
            plotter.data_add((test_source1.data(),))

        non_zero_rows = self.count_nz_rows(plot)

        if verbose >= 4:
            print("y=99", plot[:, 99])
            print("y=100", plot[:, 100])

        self.assertTrue(9 not in non_zero_rows,
                        "Check nothing is just above 90 which plots at 10")
        self.assertEqual(non_zero_rows, [99, 100],
                         "Only pixels left plotted should be from"
                         + "values 0 and 1 being plotted at 99 and 100")
        self.assertTrue(numpy.alltrue(plot[:, 99] == [1] * 190 + [0] * 10),
                        "Checking row 99 precisely")
        self.assertTrue(numpy.alltrue(plot[:, 100] == [0] * 190 + [1] * 10),
                        "Checking row 100 precisely")

        plotter.display_off()


    def test_clearmode_from_lines_wrap_to_dots_scroll(self):
        """A specific test to check that a spike that appears in lines wrap mode is
           correctly cleared by a change to dots scroll."""
        plotter = self.make_a_Plotter("lines", "wrap")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_source1 = self.make_a_PlotSource_onespike()
        self.ready_plot_source(plotter, test_source1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Fill screen then wrap to write another 20 values
        for _ in range(200 + 20):
            plotter.data_add((test_source1.data(),))

        unique2, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique2 == [0, 1]),
                        "Checking pixels are now a mix of 0 and 1")

        plotter.change_stylemode("dots", "scroll")
        unique3, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique3 == [0]),
                        "Checking all pixels are now 0 after change_stylemode")

        plotter.display_off()


    def test_clear_after_scrolling_one_channel(self):
        """A specific test to check screen clears after a scroll to help
           investigate a bug with that failing to happen in most cases."""
        plotter = self.make_a_Plotter("lines", "scroll")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_source1 = self.make_a_PlotSource()
        self.ready_plot_source(plotter, test_source1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Fill screen
        for _ in range(200):
            plotter.data_add((test_source1.data(),))

        unique2, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique2 == [0, 1]),
                        "Checking pixels are now a mix of 0 and 1")
        self.assertEqual(plotter._values, 200)
        self.assertEqual(plotter._data_values, 200)

        # Force a single scroll of the data
        for _ in range(10):
            plotter.data_add((test_source1.data(),))

        self.assertEqual(plotter._values, 200 + 10)
        self.assertEqual(plotter._data_values, 200 + 10 - self._SCROLL_PX)

        # This should clear all data and the screen
        if verbose >= 3:
            print("change_stylemode() to a new mode which will clear screen")
        plotter.change_stylemode("dots", "wrap")
        unique3, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique3 == [0]),
                        "Checking all pixels are now 0")

        plotter.display_off()

    def test_check_internal_data_three_channels(self):
        width = self._PLOT_WIDTH
        plotter = self.make_a_Plotter("lines", "scroll")
        (tg, plot) = (Mock(), numpy.zeros((width, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_triplesource1 = self.make_a_PlotSource(channels=3)

        self.ready_plot_source(plotter, test_triplesource1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Three data samples
        all_data = []
        for d_idx in range(3):
            all_data.append(test_triplesource1.data())
            plotter.data_add(all_data[-1])

        # all_data is now [(10, 15, 40), (11, 16, 41), (12, 17, 42)]
        self.assertEqual(plotter._data_y_pos[0][0:3],
                         array.array('i', [90, 89, 88]),
                         "channel 0 plotted y positions")
        self.assertEqual(plotter._data_y_pos[1][0:3],
                         array.array('i', [85, 84, 83]),
                         "channel 1 plotted y positions")
        self.assertEqual(plotter._data_y_pos[2][0:3],
                         array.array('i', [60, 59, 58]),
                         "channel 2 plotted y positions")

        # Fill rest of screen
        for d_idx in range(197):
            all_data.append(test_triplesource1.data())
            plotter.data_add(all_data[-1])

        # Three values more values to force a scroll
        for d_idx in range(3):
            all_data.append(test_triplesource1.data())
            plotter.data_add(all_data[-1])

        # all_data[-4] is (49, 54, 59)
        # all_data[-3:0] is [(50, 55, 40) (51, 56, 41) (52, 57, 42)]
        expected_data_size = width - self._SCROLL_PX + 3
        st_x_pos = width - self._SCROLL_PX
        d_idx = plotter._data_idx - 3

        self.assertTrue(self._SCROLL_PX > 3,
                        "Ensure no scrolling occurred from recent 3 values")
        # the data_idx here is 2 because the size is now plot_width + 1
        self.assertEqual(plotter._data_idx, 2)
        self.assertEqual(plotter._x_pos, st_x_pos + 3)
        self.assertEqual(plotter._data_values, expected_data_size)
        self.assertEqual(plotter._values, len(all_data))

        if verbose >= 4:
            print("YP",d_idx, plotter._data_y_pos[0][d_idx:d_idx+3])
            print("Y POS", [str(plotter._data_y_pos[ch_idx][d_idx:d_idx+3])
                            for ch_idx in [0, 1, 2]])
        ch0_ypos = [50, 49, 48]
        self.assertEqual([plotter._data_y_pos[0][idx] for idx in range(d_idx, d_idx + 3)],
                         ch0_ypos,
                         "channel 0 plotted y positions")
        ch1_ypos = [45, 44, 43]
        self.assertEqual([plotter._data_y_pos[1][idx] for idx in range(d_idx, d_idx + 3)],
                         ch1_ypos,
                         "channel 1 plotted y positions")
        ch2_ypos = [60, 59, 58]
        self.assertEqual([plotter._data_y_pos[2][idx] for idx in range(d_idx, d_idx + 3)],
                         ch2_ypos,
                         "channel 2 plotted y positions")

        # Check for plot points - fortunately none overlap
        total_pixel_matches = 0
        for ch_idx, ch_ypos in enumerate((ch0_ypos, ch1_ypos, ch2_ypos)):
            expected = plotter.channel_colidx[ch_idx]
            for idx, y_pos in enumerate(ch_ypos):
                actual = plot[st_x_pos+idx, y_pos]
                if actual == expected:
                    total_pixel_matches += 1
                else:
                    if verbose >= 4:
                        print("Pixel value for channel",
                              "{:d}, naive expectation {:d},".format(ch_idx,
                                                                     expected),
                              "actual {:d} at {:d}, {:d}, {:d}".format(idx,
                                                                       actual,
                                                                       st_x_pos + idx,
                                                                       y_pos))
        # Only 7 out of 9 will match because channel 2 put a vertical
        # line at x position 175 over-writing ch0 and ch1
        self.assertEqual(total_pixel_matches, 7, "plotted pixels check")
        # Check for that line from pixel positions 42 to 60
        for y_pos in range(42, 60 + 1):
            self.assertEqual(plot[st_x_pos, y_pos],
                             plotter.channel_colidx[2],
                             "channel 2 (over-writing) vertical line")

        plotter.display_off()

    def test_clear_after_scrolling_three_channels(self):
        """A specific test to check screen clears after a scroll with
           multiple channels being plotted (three) to help
           investigate a bug with that failing to happen in most cases
           for the second and third channels."""
        plotter = self.make_a_Plotter("lines", "scroll")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_triplesource1 = self.make_a_PlotSource(channels=3)

        self.ready_plot_source(plotter, test_triplesource1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Fill screen
        for _ in range(200):
            plotter.data_add(test_triplesource1.data())

        unique2, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique2 == [0, 1, 2, 3]),
                        "Checking pixels are now a mix of 0, 1, 2, 3")
        # Force a single scroll of the data
        for _ in range(10):
            plotter.data_add(test_triplesource1.data())

        # This should clear all data and the screen
        if verbose >= 3:
            print("change_stylemode() to a new mode which will clear screen")
        plotter.change_stylemode("dots", "wrap")
        unique3, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique3 == [0]),
                        "Checking all pixels are now 0")

        plotter.display_off()

    def test_auto_rescale_wrap_mode(self):
        """Ensure the auto-scaling is working and not leaving any remnants of previous plot."""
        plotter = self.make_a_Plotter("lines", "wrap")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_source1 = self.make_a_PlotSource_bilevel(first_v=60, second_v=900)

        self.ready_plot_source(plotter, test_source1)

        unique1, _ = numpy.unique(plot, return_counts=True)
        self.assertTrue(numpy.alltrue(unique1 == [0]),
                        "Checking all pixels start as 0")

        # Fill screen with first 200
        for _ in range(200):
            plotter.data_add((test_source1.data(),))

        non_zero_rows1 = self.count_nz_rows(plot)
        self.assertEqual(non_zero_rows1, list(range(0, 40 + 1)),
                         "From value 60 being plotted at 40 but also upward line at end")

        # Rewrite screen with next 200 but these should force an internal
        # rescaling of y axis
        for _ in range(200):
            plotter.data_add((test_source1.data(),))

        self.assertEqual(plotter.y_range, (-108.0, 1000.0),
                         "Check rescaled y range")

        non_zero_rows2 = self.count_nz_rows(plot)
        self.assertEqual(non_zero_rows2, [18],
                         "Only pixels now should be from value 900 being plotted at 18")

        plotter.display_off()

    def test_rescale_zoom_in_minequalsmax(self):
        """Test y_range adjusts any attempt to set the effective range to 0."""
        plotter = self.make_a_Plotter("lines", "wrap")
        (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
        plotter.display_on(tg_and_plot=(tg, plot))
        test_source1 = self.make_a_PlotSource_bilevel(first_v=20, second_v=20)

        self.ready_plot_source(plotter, test_source1)
        # Set y_range to a value which will cause a range of 0 with
        # the potential dire consequence of divide by zero
        plotter.y_range = (20, 20)

        plotter.data_add((test_source1.data(),))
        y_min, y_max = plotter.y_range
        self.assertTrue(y_max - y_min > 0,
                        "Range is not zero and implicitly"
                        + "ZeroDivisionError exception has not occurred.")

        plotter.display_off()

    def test_rescale_zoom_in_narrowrangedata(self):
        """Test y_range adjusts on data from a narrow range with unusual per pixel scaling mode."""
        # There was a bug which was visually obvious in pixel scale_mode
        # test this to ensure bug was squashed

        # time.monotonic_ns.return_value = lambda: global_time_ns

        local_time_ns = time.monotonic_ns()
        with patch('time.monotonic_ns', create=True,
                   side_effect=lambda: local_time_ns) as _:
            plotter = self.make_a_Plotter("lines", "wrap", scale_mode="pixel")
            (tg, plot) = (Mock(), numpy.zeros((self._PLOT_WIDTH, self._PLOT_HEIGHT), numpy.uint8))
            plotter.display_on(tg_and_plot=(tg, plot))
            test_source1 = self.make_a_PlotSource_narrowrange()

            self.ready_plot_source(plotter, test_source1)

            # About 11 seconds worth - will have zoomed in during this time
            for _ in range(300):
                val = test_source1.data()
                plotter.data_add((val,))
                local_time_ns += round(1/27 * 1e9)  # emulation of time.sleep(1/27)

            y_min1, y_max1 = plotter.y_range
            self.assertAlmostEqual(y_min1, 232.4)
            self.assertAlmostEqual(y_max1, 264.6)

            unique, counts = numpy.unique(plotter._data_y_pos[0],
                                          return_counts=True)
            self.assertEqual(min(unique), 29)
            self.assertEqual(max(unique), 171)
            self.assertEqual(len(unique), 24)
            self.assertLessEqual(max(counts) - min(counts), 1)

            # Another 14 seconds and now data is in narrow range so another zoom is due
            # Why does this take so long?
            for _ in range(400):
                val = test_source1.data()
                plotter.data_add((val,))
                local_time_ns += round(1/27 * 1e9)  # emulation of time.sleep(1/27)

            y_min2, y_max2 = plotter.y_range
            self.assertAlmostEqual(y_min2, 40.0)
            self.assertAlmostEqual(y_max2, 460.0)

            #unique2, counts2 = numpy.unique(plotter._data_y_pos[0],
            #                                return_counts=True)
            #self.assertEqual(list(unique2), [29, 100, 171])
            #self.assertLessEqual(max(counts2) - min(counts2), 1)

            if verbose >= 3:
                self.aprint_plot(plot)
            # Look for a specific bug which leaves some previous pixels
            # set on screen at column 24
            # Checking either side as this will be timing sensitive but the time
            # functions are now precisely controlled in this test so should not vary
            # with test execution duration vs wall clock
            for offset in range(-15, 15 + 5, 5):
                self.assertEqual(list(plot[24 + offset][136:172]), [0] * 36,
                                 "Checking for erased pixels at various columns")

            plotter.display_off()


if __name__ == '__main__':
    unittest.main(verbosity=verbose)
