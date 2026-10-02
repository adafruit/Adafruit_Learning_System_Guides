# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Derived from works:
# Original copyright (C) 2012-2014 Steve Markgraf; 2012 Dimitri Stolnikov;
# (C) 2013 Mauro Carvalho Chehab and Steve Markgraf (R82xx).
"""Minimal experimental RTL2832U/R820T(2)/R860 FM receive driver.

No USB discovery or configuration is performed automatically. Pass an already
configured usb.core.Device. FM-only tuning is intentional. All reads use caller
provided buffers as required by CircuitPython. No claim of lossless capture is
made: transport must separately sustain 2 * sample_rate bytes/second.
"""
import time

# pylint: disable=import-outside-toplevel, unused-variable

_INIT = bytes(
    (
        0x83,
        0x32,
        0x75,
        0xC0,
        0x40,
        0xD6,
        0x6C,
        0xF5,
        0x63,
        0x75,
        0x68,
        0x6C,
        0x83,
        0x80,
        0x00,
        0x0F,
        0x00,
        0xC0,
        0x30,
        0x48,
        0xCC,
        0x60,
        0x00,
        0x54,
        0xAE,
        0x4A,
        0xC0,
        0x00,
        0x00,
        0x00,
    )
)
_FIR = (-54, -36, -41, -40, -32, -14, 14, 53, 101, 156, 215, 273, 327, 372, 404, 421)
_LNA = (0, 9, 13, 40, 38, 13, 31, 22, 26, 31, 26, 14, 19, 5, 35, 13)
_MIX = (0, 5, 10, 10, 19, 9, 10, 25, 17, 10, 8, 16, 13, 6, 3, -8)


def reverse8(n):
    n = ((n & 0x55) << 1) | ((n >> 1) & 0x55)
    n = ((n & 0x33) << 2) | ((n >> 2) & 0x33)
    return ((n & 15) << 4) | (n >> 4)


def sample_ratio(rate, crystal=28800000):
    if rate <= 225000 or rate > 3200000 or 300000 < rate <= 900000:
        raise ValueError("unsupported RTL2832 sample rate")
    ratio = ((crystal << 22) // rate) & 0x0FFFFFFC
    real_ratio = ratio | ((ratio & 0x08000000) << 1)
    return ratio, (crystal << 22) / real_ratio


def pll_values(freq, fine=2, crystal=28800000):
    khz = (freq + 500) // 1000
    divider = 2
    div_num = 0
    while divider <= 64:
        if 1770000 <= khz * divider < 3540000:
            break
        divider *= 2
        div_num += 1
    if divider > 64:
        raise ValueError("frequency outside R82xx PLL range")
    if fine > 2:
        div_num -= 1
    elif fine < 2:
        div_num += 1
    vco_div = (crystal + 65536 * freq * divider) // (2 * crystal)
    nint, sdm = vco_div // 65536, vco_div % 65536
    if not 13 <= nint <= 63 or not 0 <= div_num <= 7:
        raise ValueError("invalid R82xx PLL values")
    ni = (nint - 13) // 4
    si = nint - 4 * ni - 13
    return divider, div_num, ni + (si << 6), sdm


class RTL2832FM:
    def __init__(self, device, timeout=1000, log=print, max_packet=64):
        if max_packet not in (64, 512):
            raise ValueError("max_packet must match 64-byte FS or 512-byte HS endpoint")
        self.max_packet = max_packet
        self.dev = device
        self.timeout = timeout
        self.log = log
        self.shadow = bytearray(35)
        self.if_freq = 3570000
        self.frequency = 0
        self.sample_rate = 0
        self.locked = False
        self.calibration = None
        self.tuner_id = None
        self.control_stalls = 0
        self.control_retries = 0
        self.demod_read_stalls = 0
        self.demod_read_retries = 0

    def _control(self, direction, value, index, data):
        # Only absolute register operations used by this driver are supported.
        # Retry one STALLed transfer, never its successful neighboring transfer.
        is_dummy = direction == 0xC0 and value == 0x0120 and index == 0x0A
        for attempt in range(3):
            try:
                n = self.dev.ctrl_transfer(
                    direction, 0, value, index, data, self.timeout
                )
            except OSError as error:
                # CircuitPython USBError subclasses OSError. Do not replay
                # timeouts, short transfers, or unspecified transport failures.
                if str(error) != "Pipe error":
                    raise
                self.control_stalls += 1
                # I2C reads may have advanced the tuner register pointer.
                if direction == 0xC0 and index == 0x600:
                    raise
                if is_dummy:
                    self.demod_read_stalls += 1
                if attempt == 2:
                    raise
                self.control_retries += 1
                if is_dummy:
                    self.demod_read_retries += 1
                if self.log:
                    self.log(
                        "RTL control retry",
                        attempt + 1,
                        "type",
                        direction,
                        "value",
                        value,
                        "index",
                        index,
                        "total",
                        self.control_retries,
                    )
                time.sleep(0.002)
                continue
            if n != len(data):
                raise OSError("short RTL control transfer %d/%d" % (n, len(data)))
            return data

    def write_reg(self, block, address, value, length=1):
        data = (
            bytes((value & 255,))
            if length == 1
            else bytes(((value >> 8) & 255, value & 255))
        )
        self._control(0x40, address, (block << 8) | 0x10, data)

    def read_reg(self, block, address, length=1):
        data = self._control(0xC0, address, block << 8, bytearray(length))
        return data[0] if length == 1 else data[0] | (data[1] << 8)

    def demod(self, page, address, value, length=1):
        data = (
            bytes((value & 255,))
            if length == 1
            else bytes(((value >> 8) & 255, value & 255))
        )
        self._control(0x40, (address << 8) | 0x20, 0x10 | page, data)
        self._control(0xC0, 0x0120, 0x0A, bytearray(1))

    def repeater(self, enabled):
        self.demod(1, 1, 0x18 if enabled else 0x10)

    def _i2c_write(self, data):
        self._control(0x40, 0x34, 0x610, data)

    def _tread(self, length, reverse=True):
        self._i2c_write(bytes((0,)))
        data = self._control(0xC0, 0x34, 0x600, bytearray(length))
        if reverse:
            for i in range(length):
                data[i] = reverse8(data[i])
        return data

    def _twrite(self, register, data):
        for start in range(0, len(data), 7):
            part = data[start : start + 7]
            self._i2c_write(bytes((register + start,)) + bytes(part))
            self.shadow[register + start : register + start + len(part)] = part

    def _tmask(self, register, value, mask=255):
        value = (self.shadow[register] & ~mask) | (value & mask)
        self._twrite(register, bytes((value,)))

    def _pll(self, freq):
        self._tmask(0x1A, 0, 0x0C)
        fine = (self._tread(5)[4] & 0x30) >> 4
        _, div_num, ni_si, sdm = pll_values(freq, fine)
        regs = bytearray(self.shadow[0x10:0x17])
        regs[0] = (regs[0] & ~0xF0) | (div_num << 5)
        regs[2] = (regs[2] & ~0xE8) | 0x80 | (0x08 if sdm == 0 else 0)
        regs[4], regs[5], regs[6] = ni_si, sdm & 255, sdm >> 8
        self._twrite(0x10, regs)
        self.locked = False
        for attempt in range(2):
            time.sleep(0.01)
            if self._tread(3)[2] & 0x40:
                self.locked = True
                break
            if attempt == 0:
                self._tmask(0x12, 0x60, 0xE0)
        if not self.locked:
            raise RuntimeError("R82xx PLL unlocked at %d Hz" % freq)
        self._tmask(0x1A, 8, 8)

    def _tuner_init(self):
        self._twrite(5, _INIT)
        for reg, val, mask in ((0x0C, 0, 15), (0x13, 49, 0x3F), (0x1D, 0, 0x38)):
            self._tmask(reg, val, mask)
        cal = 0
        for attempt in range(2):
            self._tmask(0x0B, 0x6B, 0x60)
            self._tmask(0x0F, 4, 4)
            self._tmask(0x10, 0, 3)
            self._pll(56000000)
            self._tmask(0x0B, 0x10, 0x10)
            time.sleep(0.002)
            self._tmask(0x0B, 0, 0x10)
            self._tmask(0x0F, 0, 4)
            cal = self._tread(5)[4] & 15
            if cal and cal != 15:
                break
        if cal == 15:
            cal = 0
        self.calibration = cal
        for reg, val, mask in (
            (0x0A, 0x10 | cal, 0x1F),
            (0x0B, 0x6B, 0xEF),
            (7, 0, 0x80),
            (6, 0x10, 0x30),
            (0x1E, 0x60, 0x60),
            (5, 1, 0x80),
            (0x1F, 0, 0x80),
            (0x0F, 0, 0x80),
            (0x19, 0x60, 0x60),
            (0x1D, 0xE5, 0xC7),
            (0x1C, 0x24, 0xF8),
            (0x0D, 0x53, 255),
            (0x0E, 0x75, 255),
            (5, 0, 0x60),
            (6, 0, 8),
            (0x11, 0x38, 0x38),
            (0x17, 0x30, 0x30),
            (0x0A, 0x40, 0x60),
            (0x1D, 0, 0x38),
            (0x1C, 0, 4),
            (6, 0, 0x40),
            (0x1A, 0x30, 0x30),
            (0x1D, 0x18, 0x38),
            (0x1C, 0x24, 4),
            (0x1E, 14, 0x1F),
            (0x1A, 0x20, 0x30),
        ):
            self._tmask(reg, val, mask)

    def _if(self, frequency):
        value = -((frequency << 22) // 28800000)
        for reg, val in (
            (0x19, (value >> 16) & 0x3F),
            (0x1A, (value >> 8) & 255),
            (0x1B, value & 255),
        ):
            self.demod(1, reg, val)

    def initialize(self, frequency=100100000, sample_rate=240000, gain=280):
        """Initialize already-configured device. Gain is tenths of a dB or None for AGC."""
        self.write_reg(1, 0x2000, 9)
        # EPA register is little endian, while write_reg emits big endian.
        self.write_reg(
            1, 0x2158, ((self.max_packet & 255) << 8) | (self.max_packet >> 8), 2
        )
        self.write_reg(1, 0x2148, 0x1002, 2)
        self.write_reg(2, 0x300B, 0x22)
        self.write_reg(2, 0x3000, 0xE8)
        for args in ((1, 1, 0x14), (1, 1, 0x10), (1, 0x15, 0), (1, 0x16, 0, 2)):
            self.demod(*args)
        for i in range(6):
            self.demod(1, 0x16 + i, 0)
        fir = bytearray(x & 255 for x in _FIR[:8])
        for i in range(8, 16, 2):
            a, b = _FIR[i], _FIR[i + 1]
            fir.extend(((a >> 4) & 255, ((a << 4) | ((b >> 8) & 15)) & 255, b & 255))
        for i, value in enumerate(fir):
            self.demod(1, 0x1C + i, value)
        for args in (
            (0, 0x19, 5),
            (1, 0x93, 0xF0),
            (1, 0x94, 15),
            (1, 0x11, 0),
            (1, 4, 0),
            (0, 0x61, 0x60),
            (0, 6, 0x80),
            (1, 0xB1, 0x1B),
            (0, 0x0D, 0x83),
        ):
            self.demod(*args)
        self.repeater(True)
        try:
            self.tuner_id = self._tread(1, False)[0]
            if self.tuner_id != 0x69:
                raise RuntimeError(
                    "R82xx tuner probe got 0x%02x, expected 0x69" % self.tuner_id
                )
            self.demod(1, 0xB1, 0x1A)
            self.demod(0, 8, 0x4D)
            self._if(3570000)
            self.demod(1, 0x15, 1)
            self._tuner_init()
        finally:
            self.repeater(False)
        self.set_sample_rate(sample_rate)
        self.set_gain(gain)
        self.tune(frequency)
        self.reset_buffer()
        if self.log:
            self.log(
                "RTL ready",
                self.frequency,
                self.sample_rate,
                "cal",
                self.calibration,
                "lock",
                self.locked,
            )

    def set_sample_rate(self, rate):
        # This narrow-band analog filter path is deliberately limited to low rates.
        if not 225000 < rate <= 300000:
            raise ValueError("FM driver accepts 225001..300000 samples/s")
        ratio, exact = sample_ratio(rate)
        self.repeater(True)
        try:
            self._tmask(0x0A, 0, 0x10)
            self._tmask(0x0B, 0xE6, 0xEF)  # 350 kHz minimum analog bandwidth.
            self.if_freq = 2125000
        finally:
            self.repeater(False)
        self._if(self.if_freq)
        self.demod(1, 0x9F, ratio >> 16, 2)
        self.demod(1, 0xA1, ratio & 65535, 2)
        self.demod(1, 0x3F, 0)
        self.demod(1, 0x3E, 0)
        self.demod(1, 1, 0x14)
        self.demod(1, 1, 0x10)
        self.sample_rate = exact
        if self.frequency:
            self.tune(self.frequency)

    def set_gain(self, gain=None):
        self.repeater(True)
        try:
            if gain is None:
                for r, v, m in ((5, 0, 0x10), (7, 0x10, 0x10), (0x0C, 0x0B, 0x9F)):
                    self._tmask(r, v, m)
            else:
                for r, v, m in ((5, 0x10, 0x10), (7, 0, 0x10), (0x0C, 8, 0x9F)):
                    self._tmask(r, v, m)
                total = lna = mix = 0
                for _ in range(15):
                    if total >= gain:
                        break
                    lna += 1
                    total += _LNA[lna]
                    if total >= gain:
                        break
                    mix += 1
                    total += _MIX[mix]
                self._tmask(5, lna, 15)
                self._tmask(7, mix, 15)
        finally:
            self.repeater(False)

    def tune(self, frequency):
        if not 87500000 <= frequency <= 108000000:
            raise ValueError("FM-only driver accepts 87.5..108 MHz")
        lo = frequency + self.if_freq
        tf = 0x44 if lo < 90000000 else (0x34 if lo < 110000000 else 0x24)
        self.repeater(True)
        try:
            for r, v, m in (
                (0x17, 0, 8),
                (0x1A, 2, 0xC3),
                (0x1B, tf, 255),
                (0x10, 0, 0x0B),
                (8, 0, 0x3F),
                (9, 0, 0x3F),
            ):
                self._tmask(r, v, m)
            self._pll(lo)
        finally:
            self.repeater(False)
        self.frequency = frequency

    def hold_buffer(self):
        """Hold EPA FIFO reset while host capture is stopped for reconfiguration.

        This receiver stalls tuner controls if its running sample FIFO fills
        after the host stops reading. Release using reset_buffer before reads.
        """
        self.write_reg(1, 0x2148, 0x1002, 2)

    def reset_buffer(self):
        self.write_reg(1, 0x2148, 0x1002, 2)
        self.write_reg(1, 0x2148, 0, 2)

    def set_test_mode(self, enabled):
        """RTL counter pattern for measuring missing bytes, not RF capture."""
        self.demod(0, 0x19, 3 if enabled else 5)

    def readinto(self, buffer, timeout=1000):
        if len(buffer) % 64:
            raise ValueError("read buffer length must be a multiple of 64")
        return self.dev.read(0x81, buffer, timeout)

    def open_stream(self, buffer_size=32768):
        """Start continuous capture and return a usb_host_bulk.InStream.

        Reads never block: readinto() returns None while nothing is waiting
        and 0 once the stream has ended (STALL or unplug). deinit() it, or
        use it in a with block, before calling hold_buffer() or retuning.
        """
        import usb_host_bulk

        self.reset_buffer()
        return usb_host_bulk.InStream(self.dev, 0x81, buffer_size=buffer_size)

    def stream(self, chunk, buffer_size=32768):
        """Async iterator over full chunks of I/Q bytes, like pyrtlsdr's
        RtlSdrAio.stream(). Every item is `chunk` itself, refilled:

            with radio.stream(bytearray(8192)) as chunks:
                async for iq in chunks:
                    process(iq)

        Iteration ends when the stream does (STALL or unplug). Leaving the
        with block, or stop(), ends the capture. Needs asyncio.
        """
        return _ChunkStream(self, chunk, buffer_size)


class _ChunkStream:
    def __init__(self, radio, chunk, buffer_size):
        # asyncio loads its stream module on first use. Do it before the
        # capture starts: loading it later can overflow the ring.
        from asyncio import StreamReader

        self._reader_type = StreamReader
        self._radio = radio
        self._chunk = chunk
        self._view = memoryview(chunk)
        self._buffer_size = buffer_size
        self._stream = None
        self._reader = None
        self._stopped = False
        self._stream_ended = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    def __aiter__(self):
        if self._stream is None:
            self._stream = self._radio.open_stream(self._buffer_size)
            self._reader = self._reader_type(self._stream)
        return self

    async def __anext__(self):
        filled = 0
        while filled < len(self._chunk):
            n = await self._reader.readinto(self._view[filled:])
            if not n:
                # Unplugged or stalled: the device may not answer control
                # transfers any more, so stop() skips hold_buffer().
                self._stream_ended = True
                self.stop()
                raise StopAsyncIteration
            filled += n
        return self._chunk

    @property
    def lost_packets(self):
        return self._stream.lost_packets if self._stream is not None else 0

    def stop(self):
        if self._stream is None or self._stopped:
            return
        self._stopped = True
        self._stream.deinit()
        if not self._stream_ended:
            self._radio.hold_buffer()
