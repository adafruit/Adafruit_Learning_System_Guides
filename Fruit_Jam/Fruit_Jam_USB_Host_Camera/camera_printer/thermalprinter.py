# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Protocol information from Thermal_Printer Arduino library
# https://github.com/bitbank2/Thermal_Printer/
import time

from adafruit_ble.uuid import StandardUUID
from adafruit_ble.services import Service
from adafruit_ble.characteristics import Characteristic
from adafruit_ble.characteristics.stream import StreamIn, StreamOut

# Switch the printing mode to bitmap
printimage = b"Qx\xbe\x00\x01\x00\x00\x00\xff"
# Switch the printing mode to text
printtext = b"Qx\xbe\x00\x01\x00\x01\x07\xff"
# Command to feed paper
paperfeed = b"Qx\xa1\x00\x02\x00\x1eZ\xff\xff"

# this table helps compute the checksum of transmitted data
# it is crc-8-ccitt
checksumtable = (
    b"\x00\x07\x0e\t\x1c\x1b\x12\x158?61$#*-"
    b"pw~ylkbeHOFATSZ]"
    b"\xe0\xe7\xee\xe9\xfc\xfb\xf2\xf5\xd8\xdf\xd6\xd1\xc4\xc3\xca\xcd"
    b"\x90\x97\x9e\x99\x8c\x8b\x82\x85\xa8\xaf\xa6\xa1\xb4\xb3\xba\xbd"
    b"\xc7\xc0\xc9\xce\xdb\xdc\xd5\xd2\xff\xf8\xf1\xf6\xe3\xe4\xed\xea"
    b"\xb7\xb0\xb9\xbe\xab\xac\xa5\xa2\x8f\x88\x81\x86\x93\x94\x9d\x9a"
    b"' ).;<52\x1f\x18\x11\x16\x03\x04\r\n"
    b"WPY^KLEBohafst}z"
    b"\x89\x8e\x87\x80\x95\x92\x9b\x9c\xb1\xb6\xbf\xb8\xad\xaa\xa3\xa4"
    b"\xf9\xfe\xf7\xf0\xe5\xe2\xeb\xec\xc1\xc6\xcf\xc8\xdd\xda\xd3\xd4"
    b"ing`ur{|QV_XMJCD"
    b"\x19\x1e\x17\x10\x05\x02\x0b\x0c!&/(=:34"
    b"NI@GRU\\[vqx\x7fjmdc"
    b'>907"%,+\x06\x01\x08\x0f\x1a\x1d\x14\x13'
    b"\xae\xa9\xa0\xa7\xb2\xb5\xbc\xbb\x96\x91\x98\x9f\x8a\x8d\x84\x83"
    b"\xde\xd9\xd0\xd7\xc2\xc5\xcc\xcb\xe6\xe1\xe8\xef\xfa\xfd\xf4\xf3"
)

# mirrortable[i] is the bit reversed version of the byte i
mirrortable = (
    b"\x00\x80@\xc0 \xa0`\xe0\x10\x90P\xd00\xb0p\xf0"
    b"\x08\x88H\xc8(\xa8h\xe8\x18\x98X\xd88\xb8x\xf8"
    b"\x04\x84D\xc4$\xa4d\xe4\x14\x94T\xd44\xb4t\xf4"
    b"\x0c\x8cL\xcc,\xacl\xec\x1c\x9c\\\xdc<\xbc|\xfc"
    b'\x02\x82B\xc2"\xa2b\xe2\x12\x92R\xd22\xb2r\xf2'
    b"\n\x8aJ\xca*\xaaj\xea\x1a\x9aZ\xda:\xbaz\xfa"
    b"\x06\x86F\xc6&\xa6f\xe6\x16\x96V\xd66\xb6v\xf6"
    b"\x0e\x8eN\xce.\xaen\xee\x1e\x9e^\xde>\xbe~\xfe"
    b"\x01\x81A\xc1!\xa1a\xe1\x11\x91Q\xd11\xb1q\xf1"
    b"\t\x89I\xc9)\xa9i\xe9\x19\x99Y\xd99\xb9y\xf9"
    b"\x05\x85E\xc5%\xa5e\xe5\x15\x95U\xd55\xb5u\xf5"
    b"\r\x8dM\xcd-\xadm\xed\x1d\x9d]\xdd=\xbd}\xfd"
    b"\x03\x83C\xc3#\xa3c\xe3\x13\x93S\xd33\xb3s\xf3"
    b"\x0b\x8bK\xcb+\xabk\xeb\x1b\x9b[\xdb;\xbb{\xfb"
    b"\x07\x87G\xc7'\xa7g\xe7\x17\x97W\xd77\xb7w\xf7"
    b"\x0f\x8fO\xcf/\xafo\xef\x1f\x9f_\xdf?\xbf\x7f\xff"
)


def checksum(data, start, count):
    cs = 0
    for i in range(start, start + count):
        cs = checksumtable[cs ^ data[i]]
    return cs


MODE_TEXT = "MODE_TEXT"
MODE_BITMAP = "MODE_BITMAP"


class CatPrinter(Service):

    uuid = StandardUUID(0xAE30)

    _tx = StreamIn(uuid=StandardUUID(0xAE01), timeout=1.0, buffer_size=256)

    def _write_data(self, buf):
        self._tx.write(buf)

    @property
    def bitmap_width(self):
        return 384

    def __init__(self, service=None):
        super().__init__(service=service)
        self._mode = None

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        if value == self.mode:
            return

        if value == MODE_TEXT:
            self._write_data(printtext)
        elif value == MODE_BITMAP:
            self._write_data(printimage)
        else:
            raise ValueError("Invalid mode %r" % value)

        self._mode = value

    def feed_lines(self, lines):
        buf = bytearray(paperfeed)
        buf[6] = lines & 0xFF
        buf[7] = lines >> 8
        buf[8] = checksum(buf, 6, 2)
        self._write_data(buf)

    def _print_common(self, text, reverse_bits=True):
        data = memoryview(text)
        while data:
            sz = min(112, len(data))
            sub_data = data[:sz]
            data = data[sz:]
            buf = bytearray(sz + 8)
            buf[0] = 0x51
            buf[1] = 0x78
            buf[2] = 0xA2
            buf[3] = 0x0
            buf[4] = sz
            buf[5] = 0
            if reverse_bits:
                buf[6 : 6 + sz] = bytes(mirrortable[c] for c in sub_data)
            else:
                buf[6 : 6 + sz] = sub_data
            buf[6 + sz] = checksum(buf, 6, len(sub_data))
            buf[6 + sz + 1] = 0xFF

            self._write_data(buf)

    def print_text(self, text):
        self.mode = MODE_TEXT
        self._print_common(text.encode("utf-8"))

    def print_line(self, text):
        self.print_text(text)
        self._print_common(b"\n")

    def print_bitmap_row(self, data, reverse_bits=True):
        self.mode = MODE_BITMAP
        self._print_common(data, reverse_bits)


class MXW01Printer(Service):
    """The MXW01 cat printer. It has the same service UUID as `CatPrinter`
    but a different protocol: commands go to AE01, answers come back as
    notifications on AE02, and the image goes to AE03 in one piece after
    a print request that says how many lines are coming."""

    uuid = StandardUUID(0xAE30)
    # The MXW01 advertises this UUID instead of 0xAE30
    advertised_uuid = StandardUUID(0xAF30)

    _control = Characteristic(
        uuid=StandardUUID(0xAE01), properties=Characteristic.WRITE_NO_RESPONSE
    )
    _notify = StreamOut(uuid=StandardUUID(0xAE02), timeout=0.1, buffer_size=256)
    _data = Characteristic(
        uuid=StandardUUID(0xAE03), properties=Characteristic.WRITE_NO_RESPONSE
    )

    @property
    def bitmap_width(self):
        return 384

    def _command(self, command, payload):
        buf = bytearray(len(payload) + 8)
        buf[0] = 0x22
        buf[1] = 0x21
        buf[2] = command
        buf[4] = len(payload) & 0xFF
        buf[5] = len(payload) >> 8
        buf[6 : 6 + len(payload)] = payload
        buf[-2] = checksum(buf, 6, len(payload))
        buf[-1] = 0xFF
        self._control = buf

    def _response(self, command, timeout):
        """Wait for the printer's answer to `command` and return its payload."""
        header = bytes((0x22, 0x21, command))
        data = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            waiting = self._notify.in_waiting
            if waiting:
                data += self._notify.read(waiting)
                start = data.find(header)
                if start >= 0 and len(data) >= start + 6:
                    size = data[start + 4] | (data[start + 5] << 8)
                    if len(data) >= start + 6 + size:
                        return data[start + 6 : start + 6 + size]
        raise RuntimeError("The printer did not answer")

    def print_bitmap(self, data, *, intensity=0x5D, progress=None):
        """Print `data`, 48 bytes per line, 1 = black, with the leftmost pixel
        of each byte in the lowest bit. ``progress(fraction)`` is called while
        the image is sent. Returns when the printer has finished."""
        row_bytes = self.bitmap_width // 8
        lines = len(data) // row_bytes
        self._notify.reset_input_buffer()
        self._command(0xA2, bytes((intensity,)))
        self._command(0xA9, bytes((lines & 0xFF, lines >> 8, 0x30, 0)))
        answer = self._response(0xA9, 5)
        if answer[0] != 0:
            raise RuntimeError("The printer refused to print (%d)" % answer[0])
        data = memoryview(data)
        chunk = 4 * row_bytes
        for offset in range(0, len(data), chunk):
            self._data = data[offset : offset + chunk]
            if progress and offset % (32 * row_bytes) == 0:
                progress(offset / len(data))
        self._command(0xAD, b"\x00")
        # About 1 second per 40 lines, plus a margin
        self._response(0xAA, 10 + lines / 20)
