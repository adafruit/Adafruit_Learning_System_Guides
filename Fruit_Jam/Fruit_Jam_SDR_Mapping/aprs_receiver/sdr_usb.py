# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The NESDR on the board's USB host port: finding it, and its I/Q stream.

On the Fruit Jam the supervisor starts the USB host port (full speed) and
usb_host_bulk reads the stream into a ring in the background:
InStream.readinto() never blocks, and the ring holds 64-128 ms while the
receiver does other work.

The Metro ESP32-P4's USB-A port is high speed (the P4's own PHY). The
supervisor does not start it: start_host() switches its 5 V on
(board.USB_HOST_POWER, active high: without it nothing enumerates) and
starts usb_host.Port. The RTL2832U's packets are 512 bytes there
(max_packet()). Now and then a control write to it never completes (a
timeout) while the same write sent again goes through at once:
ResendWrites sends them again.

There is no usb_host_bulk on the P4: HostStream stands in for InStream
with the blocking Device.read(). While the receiver works between two
reads nothing reads, and the stream waits in the RTL2832U's FIFO
(~3.7 KB: ~7 ms at 256 kS/s); what does not fit is lost. Back to back,
the reads are contiguous. When the FIFO overflows it keeps its oldest
bytes: the next read returns them, then jumps to the current ones.
HostStream keeps the stream's timeline: when the reads fall further
behind the radio than the FIFO holds, the lost bytes are filled in with
silence after that read, so that a block is still 16 ms of air (FT8's
waterfall stays whole and its slot edges stay put).

On the Metro a 16 ms block takes ~4 ms of DSP and decoding (APRS) or
~2.5 ms (FT8), leaving a few ms for the receiver's other work before
the FIFO overflows; a status row on the TFT takes ~14 ms.
"""

import time

import supervisor
import usb.core
try:
    import usb_host_bulk
except ImportError:
    usb_host_bulk = None

# pylint: disable=global-statement, import-outside-toplevel

PACKET = 64                 # bytes per lost_packets count (a full-speed USB packet)
FIFO = 3760                 # bytes the RTL2832U's FIFO holds (20 x 188)
SLACK = FIFO + 1024         # bytes the reads may be behind before a gap is filled
_host_port = None
_host_power = None


def start_host():
    """Boards whose USB host port is not started by the supervisor (the
    Metro ESP32-P4): switch its 5 V on and start it from here."""
    global _host_port, _host_power
    if _host_port is not None:
        return
    import board
    if hasattr(board, 'USB_HOST_DP'):
        import usb_host
        if hasattr(board, 'USB_HOST_POWER'):
            import digitalio
            _host_power = digitalio.DigitalInOut(board.USB_HOST_POWER)
            _host_power.switch_to_output(True)
        _host_port = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)


def find_device(tries=20):
    """The NESDR on the USB host port, configured."""
    start_host()
    for _ in range(tries):
        d = usb.core.find(idVendor=0x0BDA, idProduct=0x2838)
        if d:
            time.sleep(0.5)
            d.set_configuration()
            return d
        time.sleep(0.1)
    raise RuntimeError('No RTL-SDR receiver found on the USB host port')


def max_packet(device):
    """The RTL2832U's USB packet size for this port: 512 on a high-speed
    one (at 64 every read would end early)."""
    return 512 if device.speed == 3 else 64


def control(device):
    """The device for the tuner driver's control transfers."""
    return ResendWrites(device) if device.speed == 3 else device


class ResendWrites:
    """The device, with control writes sent again when they time out (the
    Metro ESP32-P4's high-speed host). A register write can be sent
    again; reads are not (an I2C read moves the tuner's register
    pointer)."""

    def __init__(self, device, timeout_ms=50, tries=5):
        self.device = device
        self.timeout_ms = timeout_ms
        self.tries = tries
        self.resent = 0

    def ctrl_transfer(self, request_type, request, value=0, index=0, data=None, timeout=0):
        if request_type & 0x80:
            return self.device.ctrl_transfer(request_type, request, value, index, data, timeout)
        for attempt in range(self.tries):
            try:
                return self.device.ctrl_transfer(request_type, request, value, index, data,
                                                 self.timeout_ms)
            except usb.core.USBTimeoutError:
                if attempt == self.tries - 1:
                    raise
                self.resent += 1
        return None

    def __getattr__(self, name):
        return getattr(self.device, name)


class HostStream:
    """What the receivers use of usb_host_bulk.InStream, with the blocking
    Device.read() (no usb_host_bulk: the Metro ESP32-P4).

    readinto(view) reads len(view) bytes (whole 512-byte packets: a read
    that ends inside one overruns the buffer and crashes the board), and
    the call after a read returns None, as InStream does when nothing is
    waiting: then the receiver does one piece of its other work while the
    FIFO holds the stream. rate: I/Q samples a second.

    The bytes due from the radio are counted from the time: when a read
    starts more than SLACK behind, the FIFO overflowed while the receiver
    worked. That read returns the FIFO's bytes and the current ones; the
    next calls fill in the bytes lost between them with silence (I/Q at
    the centre) before reading again. lost_packets counts them, as
    InStream counts the packets it lost; fills_gaps says that they are in
    the stream (as silence), not missing from it."""
    fills_gaps = True

    def __init__(self, device, rate, endpoint=0x81, timeout_ms=500):
        self.device = device
        self.endpoint = endpoint
        self.timeout_ms = timeout_ms
        self.byte_rate = int(2 * rate)
        self.behind = 0              # bytes due from the radio and not read yet
        self.filled = 0              # bytes of silence put in for lost ones
        self.owed = 0                # ... still to put in
        self.timeouts = 0
        self._due = 0                # (byte_rate x ms not counted in behind yet)
        self._ms = supervisor.ticks_ms()
        self._idle = False
        self._pad = None
        self._silence = memoryview(b'\x80' * 8192)

    def readinto(self, view):
        if self._idle:
            self._idle = False
            return None
        t = supervisor.ticks_ms()
        self._due += ((t - self._ms) & 0x1FFFFFFF) * self.byte_rate
        self._ms = t
        self.behind += self._due // 1000
        self._due %= 1000
        size = len(view)
        if self.owed:
            # (no idle call after silence: the FIFO is full, read soon)
            n = min(size, len(self._silence), self.owed)
            view[:n] = self._silence[:n]
            self.owed -= n
            self.filled += n
            self.behind -= n
            return n
        if self.behind > SLACK:
            self.owed = (self.behind - FIFO) & ~511
        try:
            if size & 511 == 0:
                n = self.device.read(self.endpoint, view, self.timeout_ms)
            elif size > 512:
                n = self.device.read(self.endpoint, view[:size & ~511], self.timeout_ms)
            else:
                # (only after a short read) one packet, the rest of it dropped
                if self._pad is None:
                    self._pad = bytearray(512)
                n = min(size, self.device.read(self.endpoint, self._pad, self.timeout_ms))
                view[:n] = memoryview(self._pad)[:n]
        except usb.core.USBTimeoutError:
            self.timeouts += 1
            return None
        self.behind -= n
        self._idle = True
        return n

    @property
    def lost_packets(self):
        """64-byte packets' worth of the stream filled in with silence."""
        return self.filled // PACKET

    def deinit(self):
        pass


def open_stream(device, rate, sizes=(65536, 32768)):
    """The I/Q stream and its ring's size: usb_host_bulk's InStream with
    the largest ring that fits (128 ms of buffering, or 64 ms), or a
    HostStream (ring 0)."""
    if usb_host_bulk is None:
        return HostStream(device, rate), 0
    for size in sizes:
        try:
            return usb_host_bulk.InStream(device, 0x81, buffer_size=size), size
        except MemoryError:
            pass
    raise MemoryError('no SRAM for the USB bulk ring')
