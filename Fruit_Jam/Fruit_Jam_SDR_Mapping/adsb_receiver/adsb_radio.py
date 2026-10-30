# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The NESDR at 1090 MHz, 2 MS/s, read in snapshots (or, on a high-speed
USB host, in long stretches of the stream).

ADS-B needs about 2 MS/s: 4 MB/s of I/Q. The Fruit Jam's USB host is full
speed and carries about 0.9 MB/s. Run that fast, the RTL2832U's USB FIFO
overflows and keeps only isolated 188-byte blocks (47 us each: too short
for a 120 us message). But the FIFO (USB_EPA_FIFO_CFG = 20 blocks of 188
bytes) fills from empty with contiguous samples after a reset. So each
snapshot is: reset the FIFO (USB_EPA_CTL bit 1), release it, read the first
3760 bytes (1880 samples, 940 us at 2 MS/s, all contiguous). With
ctrl_transfer() a cycle takes about 12 ms (two control transfers of ~4 ms,
and ~4 ms to read the bytes): about 8 % of the air time is heard. Firmware
with InStream.control_out() does both writes in one USB frame.

On the Metro ESP32-P4 the SDR is on a high-speed USB host port, which
carries the whole stream (~4.2 MB/s measured): no snapshots there. Each
read() is STREAM_CHUNK bytes with Device.read() (it blocks; there is no
usb_host_bulk), 9.2 ms of air. While the last one is decoded nobody reads
and the FIFO fills: a read starts with the FIFO's 3760 bytes, then a jump,
then the rest is contiguous. ~69 reads a second (decoding and the rest
take ~5 ms a read): about 64 % of the air time is heard, against ~11 %
with snapshots. (Reads are multiples of 512 bytes: the device sends whole
512-byte packets, and a read that ends inside one overruns the buffer and
crashes the board.)
"""

import time

import usb.core
try:
    import usb_host_bulk
except ImportError:
    usb_host_bulk = None

import ham_tuner

# pylint: disable=global-statement, import-outside-toplevel, protected-access

FREQUENCY = 1090000000
RATE = 2000000
FIFO_BLOCKS = 20            # USB_EPA_FIFO_CFG: 5 bits; above ~21 the data is corrupted
SNAPSHOT = FIFO_BLOCKS * 188
# a read on a high-speed host: 72 x 512-byte packets, five decoder pieces
STREAM_CHUNK = 36864

_EPA_CTL = 0x2148
_EPA_FIFO_CFG = 0x2160

# write_reg(1, _EPA_CTL, 2, 2) then (..., 0, 2): wIndex = (block 1 << 8) | 0x10,
# data big endian. control_out() is in newer firmware only.
_FIFO_RESTART = ((0x40, 0, _EPA_CTL, 0x0110, b'\x00\x02'),
                 (0x40, 0, _EPA_CTL, 0x0110, b'\x00\x00'))
_FAST = usb_host_bulk is not None and hasattr(usb_host_bulk.InStream, 'control_out')
_host_port = None
_host_power = None


def _start_host():
    """Boards whose USB host port is not started by the supervisor (the
    Metro ESP32-P4): switch its 5 V on (USB_HOST_POWER, active high) and
    start it from here."""
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


class _ResendWrites:
    """The device, with control writes sent again when they time out.

    On the Metro ESP32-P4's high-speed host, now and then a control write
    to the tuner's I2C never completes (a USBTimeoutError after the whole
    timeout) while the same write sent again goes through at once. A
    register write can be sent again; reads are not (an I2C read moves the
    tuner's register pointer)."""

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


def find_device(tries=20):
    _start_host()
    for _ in range(tries):
        d = usb.core.find(idVendor=0x0BDA, idProduct=0x2838)
        if d:
            return d
        time.sleep(0.1)
    raise RuntimeError("No RTL-SDR receiver found on the USB host port")


class AdsbRadio:
    """The receiver set up for 1090 MHz snapshots.

    gain: tenths of a dB, or None for the tuner's AGC (the most sensitive
    here: the R820T's fixed VGA setting leaves the noise at ~1.5 counts).
    streaming: a high-speed host (the Metro ESP32-P4), or no usb_host_bulk.
    snapshot: the bytes a read() wants, SNAPSHOT or STREAM_CHUNK.
    """

    def __init__(self, gain=None, frequency=FREQUENCY, log=print):
        self.log = log
        self.device = find_device()
        time.sleep(0.5)
        self.device.set_configuration()
        self.streaming = usb_host_bulk is None or self.device.speed == 3
        if self.streaming and self.device.speed != 3:
            raise RuntimeError("ADS-B needs usb_host_bulk or a high-speed USB host")
        self.snapshot = STREAM_CHUNK if self.streaming else SNAPSHOT
        # USB_EPA_MAXPKT: 512 on a high-speed port, where 64-byte packets would be short ones
        self.radio = ham_tuner.open_ham_receiver(
            _ResendWrites(self.device) if self.streaming else self.device, log=None,
            max_packet=512 if self.device.speed == 3 else 64)
        if self.radio.tuner_name != "R82xx":
            raise RuntimeError("ADS-B needs the R820T tuner (1090 MHz)")
        self.radio.initialize(frequency, 256000, gain)
        self._wide(frequency)
        self.radio.write_reg(1, _EPA_FIFO_CFG, FIFO_BLOCKS << 8, 2)  # little endian
        self.gain = gain
        self.frequency = frequency
        self.stream = None
        self.snapshots = 0
        self.ended = 0

    def _wide(self, frequency):
        """2 MS/s, the R820T's wide IF filter (librtlsdr's > 2.4 MHz setting)."""
        r = self.radio
        ratio, exact = ham_tuner.sample_ratio(RATE)
        r.repeater(True)
        try:
            r._tmask(0x0A, 0x10, 0x10)
            r._tmask(0x0B, 0x6B, 0xEF)
            r.if_freq = 3570000
        finally:
            r.repeater(False)
        r._if(r.if_freq)
        r.demod(1, 0x9F, ratio >> 16, 2)
        r.demod(1, 0xA1, ratio & 65535, 2)
        r.demod(1, 0x3F, 0)
        r.demod(1, 0x3E, 0)
        r.demod(1, 1, 0x14)
        r.demod(1, 1, 0x10)
        r.sample_rate = exact
        r.tune(frequency)

    def start(self, ring=8192):
        self.radio.reset_buffer()
        if self.streaming:
            self.stream = True       # read with Device.read()
        else:
            self.stream = usb_host_bulk.InStream(self.device, 0x81, buffer_size=ring)

    def stop(self):
        if self.stream is not None:
            if self.stream is not True:
                self.stream.deinit()
            self.stream = None
            self.radio.hold_buffer()

    def set_gain(self, gain):
        """Only while stopped (tuner I2C stalls while the FIFO overflows)."""
        self.radio.set_gain(gain)
        self.gain = gain

    def restart_fifo(self):
        """Empty the FIFO and let it fill again from now (streaming: nothing
        to do, the reads follow the stream)."""
        if self.streaming:
            return
        if _FAST:
            # Both writes in one USB frame (~1 ms instead of ~8.6 ms); the
            # ring is flushed right after the reset took effect.
            self.stream.control_out(_FIFO_RESTART, flush_after=0)
            return
        self.radio.write_reg(1, _EPA_CTL, 2, 2)
        self.stream.reset_input_buffer()
        self.radio.write_reg(1, _EPA_CTL, 0, 2)

    def read(self, view, idle=None, timeout_ms=200):
        """Fill view (self.snapshot bytes) with what came since restart_fifo().
        idle() is called while waiting (it must be short). False on timeout."""
        stream = self.stream
        if stream is True:
            # streaming (no idle(): the read blocks)
            try:
                n = self.device.read(0x81, view, timeout_ms)
            except usb.core.USBTimeoutError:
                return False
            if n < len(view):
                return False
            self.snapshots += 1
            return True
        filled = 0
        size = len(view)
        deadline = time.monotonic_ns() + timeout_ms * 1000000
        while filled < size:
            n = stream.readinto(view[filled:])
            if n:
                filled += n
                continue
            if n == 0:
                raise OSError("USB stream ended")
            if idle is not None:
                idle()
            if time.monotonic_ns() > deadline:
                return False
        self.snapshots += 1
        return True
