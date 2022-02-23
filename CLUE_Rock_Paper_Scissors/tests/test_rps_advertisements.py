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
from unittest.mock import MagicMock

verbose = int(os.getenv('TESTVERBOSE', '2'))

# PYTHONPATH needs to be set to find adafruit_ble

# Mocking library used by adafruit_ble
sys.modules['_bleio'] = MagicMock()

# Borrowing the dhalbert/tannewt technique from adafruit/Adafruit_CircuitPython_Motor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import what we are testing or will test in future
# pylint: disable=unused-import,wrong-import-position
from rps_advertisements import JoinGameAdvertisement, \
                               RpsEncDataAdvertisement, \
                               RpsKeyDataAdvertisement, \
                               RpsRoundEndAdvertisement

# pylint: disable=line-too-long

class Test_RpsEncDataAdvertisement(unittest.TestCase):

    def test_bytes_order(self):
        """Testing the order of data inside the manufacturer's field to ensure it follows the
           fields are set in. This is new behaviour to benefit prefix matching."""

        rpsedad1 = RpsEncDataAdvertisement(enc_data=b"FIRST", round_no=33, sequence_number=17)

        # This checks value is not the old incorrect order
        self.assertNotEqual(bytes(rpsedad1),
                            b"\x16\xff\x22\x08\x03\x03\x00\x11\nA\xfeFIRST\x00\x00\x00\x03C\xfe\x21",
                            msg="Checking order of serialised data for"
                                " ackless RpsEncDataAdvertisement does"
                                " not follow previous incorrect order")

        # This check for correct order
        self.assertEqual(bytes(rpsedad1),
                         b"\x16\xff\x22\x08\x0a\x41\xfeFIRST\x00\x00\x00\x03C\xfe\x21\x03\x03\x00\x11",
                         msg="Checking order of serialised data for"
                             " ackless RpsEncDataAdvertisement")

        rpsedad1.ack = 29
        self.assertEqual(bytes(rpsedad1),
                         b"\x1a\xff\x22\x08\nA\xfeFIRST\x00\x00\x00\x03C\xfe!\x03\x03\x00\x11\x03Q\xfe\x1d",
                         msg="Checking order of serialised data for"
                             " RpsEncDataAdvertisement with ack set post construction")


class Test_RpsKeyDataAdvertisement(unittest.TestCase):

    def test_bytes_order(self):
        """Testing the order of data inside the manufacturer's field to ensure it follows the
           fields are set in. This is new behaviour to benefit prefix matching."""

        rpskdad1 = RpsKeyDataAdvertisement(key_data=b"FIRST", round_no=33, sequence_number=17)

        # This checks value is not the old incorrect order
        self.assertNotEqual(bytes(rpskdad1),
                            b"\x16\xff\x22\x08\x03\x03\x00\x11\nB\xfeFIRST\x00\x00\x00\x03C\xfe\x21",
                            msg="Checking order of serialised data for"
                                " ackless RpsKeyDataAdvertisement does"
                                " not follow previous incorrect order")

        # This check for correct order
        self.assertEqual(bytes(rpskdad1),
                         b"\x16\xff\x22\x08\x0a\x42\xfeFIRST\x00\x00\x00\x03C\xfe\x21\x03\x03\x00\x11",
                         msg="Checking order of serialised data for"
                             " ackless RpsKeyDataAdvertisement")

        rpskdad1.ack = 29
        self.assertEqual(bytes(rpskdad1),
                         b"\x1a\xff\x22\x08\nB\xfeFIRST\x00\x00\x00\x03C\xfe!\x03\x03\x00\x11\x03Q\xfe\x1d",
                         msg="Checking order of serialised data for"
                             " RpsKeyDataAdvertisement with ack set post construction")


class Test_RpsRoundEndAdvertisement(unittest.TestCase):

    def test_bytes_order(self):
        """Testing the order of data inside the manufacturer's field to ensure it follows the
           fields are set in. This is new behaviour to benefit prefix matching."""

        rpsread1 = RpsRoundEndAdvertisement(round_no=133, sequence_number=201)

        # This checks value is not the old incorrect order
        self.assertNotEqual(bytes(rpsread1),
                            b"\x0b\xff\x22\x08\x03\x03\x00\xc9\x03C\xfe\x85",
                            msg="Checking order of serialised data for"
                                " ackless RpsRoundEndAdvertisement does"
                                " not follow previous incorrect order")

        # This check for correct order
        self.assertEqual(bytes(rpsread1),
                         b"\x0b\xff\x22\x08\x03C\xfe\x85\x03\x03\x00\xc9",
                         msg="Checking order of serialised data for"
                             " ackless RpsRoundEndAdvertisement")

        rpsread1.ack = 200
        self.assertEqual(bytes(rpsread1),
                         b"\x0f" b"\xff\x22\x08\x03C\xfe\x85\x03\x03\x00\xc9" b"\x03Q\xfe\xc8",
                         msg="Checking order of serialised data for"
                             " RpsRoundEndAdvertisement with ack set post construction")


if __name__ == '__main__':
    unittest.main(verbosity=verbose)
