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

import struct

from adafruit_ble.advertising import Advertisement, LazyObjectField
from adafruit_ble.advertising.standard import ManufacturerData, ManufacturerDataField

# These message should really include version numbers for the
# the protocol and a descriptor for the encryption type

# From adafruit_ble.advertising
# 0xFF is "Manufacturer Specific Data" as per list of types in
# https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile/
MANUFACTURING_DATA_ADT = 0xFF
ADAFRUIT_COMPANY_ID = 0x0822

# pylint: disable=line-too-long
# From https://github.com/adafruit/Adafruit_CircuitPython_BLE_BroadcastNet/blob/c6328d5c7edf8a99ff719c3b1798cb4111bab397/adafruit_ble_broadcastnet.py#L84-L85
ADAFRUIT_SEQ_ID = 0x0003

# According to https://github.com/adafruit/Adafruit_CircuitPython_BLE/blob/master/adafruit_ble/advertising/adafruit.py
# 0xf000 (to 0xffff) is for range for Adafruit customers

# These four are used as part of prefix matching
RPS_ENC_DATA_ID = 0xfe41
RPS_KEY_DATA_ID = 0xfe42
RPS_ROUND_ID = 0xfe43
GM_JOIN_ID = 0xfe44

RPS_ACK_ID = 0xfe51

# Data formats for shared fields
_DATA_FMT_ROUND = "B"
_DATA_FMT_ACK = "B"
_SEQ_FMT = "B"


class RpsEncDataAdvertisement(Advertisement):
    """An RPS (broadcast) message.
       This sends the encrypted choice of the player.
       This is not connectable and does not elicit a scan response
       based on defaults in Advertisement parent class.
       """
    flags = None

    _PREFIX_FMT = "<BHBH"
    _DATA_FMT_ENC_DATA = "8s"

    # match_prefixes tuple replaces deprecated prefix
    # comma for 1 element is very important!
    match_prefixes = (
        struct.pack(
            _PREFIX_FMT,
            MANUFACTURING_DATA_ADT,
            ADAFRUIT_COMPANY_ID,
            struct.calcsize("<H" + _DATA_FMT_ENC_DATA),
            RPS_ENC_DATA_ID
        ),
    )
    manufacturer_data = LazyObjectField(
        ManufacturerData,
        "manufacturer_data",
        advertising_data_type=MANUFACTURING_DATA_ADT,
        company_id=ADAFRUIT_COMPANY_ID,
        key_encoding="<H"
    )

    enc_data = ManufacturerDataField(RPS_ENC_DATA_ID, "<" + _DATA_FMT_ENC_DATA)
    round_no = ManufacturerDataField(RPS_ROUND_ID, "<" + _DATA_FMT_ROUND)
    sequence_number = ManufacturerDataField(ADAFRUIT_SEQ_ID, "<" + _SEQ_FMT)
    """Sequence number of the data. Used in acknowledgements."""
    ack = ManufacturerDataField(RPS_ACK_ID, "<" + _DATA_FMT_ACK)
    """Round number starting at 1."""

    def __init__(self, *, enc_data=None, round_no=None, sequence_number=None, ack=None):
        """enc_data must be either set here in the constructor or set first."""
        super().__init__()
        if enc_data is not None:
            self.enc_data = enc_data
        if round_no is not None:
            self.round_no = round_no
        if sequence_number is not None:
            self.sequence_number = sequence_number
        if ack is not None:
            self.ack = ack


class RpsKeyDataAdvertisement(Advertisement):
    """An RPS (broadcast) message.
       This sends the key to decrypt the previous encrypted choice of the player.
       This is not connectable and does not elicit a scan response
       based on defaults in Advertisement parent class.
       """
    flags = None

    _PREFIX_FMT = "<BHBH"
    _DATA_FMT_KEY_DATA = "8s"

    # match_prefixes tuple replaces deprecated prefix
    # comma for 1 element is very important!
    match_prefixes = (
        struct.pack(
            _PREFIX_FMT,
            MANUFACTURING_DATA_ADT,
            ADAFRUIT_COMPANY_ID,
            struct.calcsize("<H" + _DATA_FMT_KEY_DATA),
            RPS_KEY_DATA_ID
        ),
    )
    manufacturer_data = LazyObjectField(
        ManufacturerData,
        "manufacturer_data",
        advertising_data_type=MANUFACTURING_DATA_ADT,
        company_id=ADAFRUIT_COMPANY_ID,
        key_encoding="<H"
    )

    key_data = ManufacturerDataField(RPS_KEY_DATA_ID, "<" + _DATA_FMT_KEY_DATA)
    round_no = ManufacturerDataField(RPS_ROUND_ID, "<" + _DATA_FMT_ROUND)
    sequence_number = ManufacturerDataField(ADAFRUIT_SEQ_ID, "<" + _SEQ_FMT)
    """Sequence number of the data. Used in acknowledgements."""
    ack = ManufacturerDataField(RPS_ACK_ID, "<" + _DATA_FMT_ACK)
    """Round number starting at 1."""

    def __init__(self, *, key_data=None, round_no=None, sequence_number=None, ack=None):
        """key_data must be either set here in the constructor or set first."""
        super().__init__()
        if key_data is not None:
            self.key_data = key_data
        if round_no is not None:
            self.round_no = round_no
        if sequence_number is not None:
            self.sequence_number = sequence_number
        if ack is not None:
            self.ack = ack


class RpsRoundEndAdvertisement(Advertisement):
    """An RPS (broadcast) message.
       This informs other players the round_no is complete.
       An important side-effect is acknowledgement of previous message.
       This is not connectable and does not elicit a scan response
       based on defaults in Advertisement parent class.
       """
    flags = None

    _PREFIX_FMT = "<BHBH"

    # match_prefixes tuple replaces deprecated prefix
    # comma for 1 element is very important!
    match_prefixes = (
        struct.pack(
            _PREFIX_FMT,
            MANUFACTURING_DATA_ADT,
            ADAFRUIT_COMPANY_ID,
            struct.calcsize("<H" + _DATA_FMT_ROUND),
            RPS_ROUND_ID
        ),
    )
    manufacturer_data = LazyObjectField(
        ManufacturerData,
        "manufacturer_data",
        advertising_data_type=MANUFACTURING_DATA_ADT,
        company_id=ADAFRUIT_COMPANY_ID,
        key_encoding="<H"
    )

    round_no = ManufacturerDataField(RPS_ROUND_ID, "<" + _DATA_FMT_ROUND)
    sequence_number = ManufacturerDataField(ADAFRUIT_SEQ_ID, "<" + _SEQ_FMT)
    """Sequence number of the data. Used in acknowledgements."""
    ack = ManufacturerDataField(RPS_ACK_ID, "<" + _DATA_FMT_ACK)
    """Round number starting at 1."""

    def __init__(self, *, round_no=None, sequence_number=None, ack=None):
        """round_no must be either set here in the constructor or set first."""
        super().__init__()
        if round_no is not None:
            self.round_no = round_no
        if sequence_number is not None:
            self.sequence_number = sequence_number
        if ack is not None:
            self.ack = ack


class JoinGameAdvertisement(Advertisement):
    """A join game (broadcast) message used as the first message to work out who is playing.
       This is not connectable and does not elicit a scan response
       based on defaults in Advertisement parent class.
       """
    flags = None

    _PREFIX_FMT = "<BHBH"
    _DATA_FMT = "8s"  # this NUL pads for 8s if necessary

    # match_prefixes tuple replaces deprecated prefix
    # comma for 1 element is very important!
    match_prefixes = (
        struct.pack(
            _PREFIX_FMT,
            MANUFACTURING_DATA_ADT,
            ADAFRUIT_COMPANY_ID,
            struct.calcsize("<H" + _DATA_FMT),
            GM_JOIN_ID
        ),
    )
    manufacturer_data = LazyObjectField(
        ManufacturerData,
        "manufacturer_data",
        advertising_data_type=MANUFACTURING_DATA_ADT,
        company_id=ADAFRUIT_COMPANY_ID,
        key_encoding="<H"
    )

    game = ManufacturerDataField(GM_JOIN_ID, "<" + _DATA_FMT)
    """The name of the game, limited to eight characters."""

    def __init__(self, *, game=None):
        super().__init__()
        if game is not None:
            self.game = game
