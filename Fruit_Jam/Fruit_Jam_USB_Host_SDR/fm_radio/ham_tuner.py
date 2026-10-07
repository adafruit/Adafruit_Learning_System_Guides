# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# R82xx Derived from works:
# Original copyright (C) 2012-2014 Steve Markgraf; 2012 Dimitri Stolnikov;
# (C) 2013 Mauro Carvalho Chehab and Steve Markgraf (R82xx).
#
# FC0013 Derived from works:
# Original copyright (C) 2012 Hans-Frieder Vogt;
# partially based on driver code from Fitipower,
# (C) 2010 Fitipower Integrated Technology Inc;
# modified for use in librtlsdr (C) 2012 Steve Markgraf.

"""RTL2832U receiver drivers for the ham radio example.

* R82xx (NESDR SMArt v5): 25.6 MHz - 1.76 GHz through the tuner, using the
  full librtlsdr frequency-range table (tracking filter, RF mux, open drain).
  Below that, the RTL2832U samples the antenna directly ("direct sampling",
  0.1 - 25 MHz on the SMArt v5) and the tuner is put in standby.
* FC0013: 22 MHz - 1.1 GHz. No HF.

open_ham_receiver() probes the dongle and returns the matching driver.
tune() takes the hardware centre frequency. The demodulator is told
`conjugate` because some paths deliver an inverted spectrum.

No USB discovery or configuration is performed automatically. Pass an already
configured usb.core.Device. All reads use caller provided buffers as required
by CircuitPython. No claim of lossless capture is made: transport must
separately sustain 2 * sample_rate bytes/second.
"""

# pylint: disable=too-many-lines, import-outside-toplevel, unused-variable, too-many-locals, too-many-branches,
# pylint: disable=too-many-statements, protected-access

import time

CRYSTAL = 28800000

# RTL2832U baseband FIR filter coefficients.
_FIR = (-54, -36, -41, -40, -32, -14, 14, 53, 101, 156, 215, 273, 327, 372, 404, 421)

# -- R82xx tables ----------------------------------------------------------

_R82XX_INIT = bytes(
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
_R82XX_LNA = (0, 9, 13, 40, 38, 13, 31, 22, 26, 31, 26, 14, 19, 5, 35, 13)
_R82XX_MIX = (0, 5, 10, 10, 19, 9, 10, 25, 17, 10, 8, 16, 13, 6, 3, -8)

# tuner_r82xx.c freq_ranges: (start MHz, open_d, rf_mux_ploy, tf_c). The
# xtal_cap columns are not needed: this driver runs the crystal at 0 pF.
_R82XX_RANGES = (
    (0, 0x08, 0x02, 0xDF),
    (50, 0x08, 0x02, 0xBE),
    (55, 0x08, 0x02, 0x8B),
    (60, 0x08, 0x02, 0x7B),
    (65, 0x08, 0x02, 0x69),
    (70, 0x08, 0x02, 0x58),
    (75, 0x00, 0x02, 0x44),
    (80, 0x00, 0x02, 0x44),
    (90, 0x00, 0x02, 0x34),
    (100, 0x00, 0x02, 0x34),
    (110, 0x00, 0x02, 0x24),
    (120, 0x00, 0x02, 0x24),
    (140, 0x00, 0x02, 0x14),
    (180, 0x00, 0x02, 0x13),
    (220, 0x00, 0x02, 0x13),
    (250, 0x00, 0x02, 0x11),
    (280, 0x00, 0x02, 0x00),
    (310, 0x00, 0x41, 0x00),
    (450, 0x00, 0x41, 0x00),
    (588, 0x00, 0x40, 0x00),
    (650, 0x00, 0x40, 0x00),
)

# r82xx_standby register writes, in order.
_R82XX_STANDBY = (
    (0x06, 0xB1),
    (0x05, 0xA0),
    (0x07, 0x3A),
    (0x08, 0x40),
    (0x09, 0xC0),
    (0x0A, 0x36),
    (0x0C, 0x35),
    (0x0F, 0x68),
    (0x11, 0x03),
    (0x17, 0xF4),
    (0x19, 0x0C),
)

# -- FC0013 tables ---------------------------------------------------------

_FC0013_INIT = (
    0x00,  # 0x00: dummy
    0x09,  # 0x01
    0x16,  # 0x02
    0x00,  # 0x03
    0x00,  # 0x04
    0x17,  # 0x05
    0x02,  # 0x06: LPF bandwidth
    0x0A,  # 0x07: CHECK, |= 0x20 for a 27 or 28.8 MHz crystal
    0xFF,  # 0x08: AGC clock /256, AGC gain 1/256, loop bw 1/8
    0x6E,  # 0x09: disable LoopThrough
    0xB8,  # 0x0a: disable LO test buffer
    0x82,  # 0x0b: CHECK
    0xFC,  # 0x0c: |= 0x02 for dual master
    0x01,  # 0x0d: AGC not forcing, LNA forcing
    0x00,  # 0x0e
    0x00,  # 0x0f
    0x00,  # 0x10
    0x00,  # 0x11
    0x00,  # 0x12
    0x00,  # 0x13
    0x50,  # 0x14: DVB-T high gain, UHF
    0x01,
)  # 0x15

# tuner_fc0013.c fc0013_lna_gains, tenths of a dB paired with register value.
_FC0013_LNA_GAINS = (
    (-99, 0x02),
    (-73, 0x03),
    (-65, 0x05),
    (-63, 0x04),
    (-63, 0x00),
    (-60, 0x07),
    (-58, 0x01),
    (-54, 0x06),
    (58, 0x0F),
    (61, 0x0E),
    (63, 0x0D),
    (65, 0x0C),
    (67, 0x0B),
    (68, 0x0A),
    (70, 0x09),
    (71, 0x08),
    (179, 0x17),
    (181, 0x16),
    (182, 0x15),
    (184, 0x14),
    (186, 0x13),
    (188, 0x12),
    (191, 0x11),
    (197, 0x10),
)

# Frequency divider selection from fc0013_set_params, ordered by upper bound.
# Each entry is (exclusive upper bound in Hz, multiplier, reg5, reg6).
_FC0013_DIVIDERS = (
    (37084000, 96, 0x82, 0x00),
    (55625000, 64, 0x02, 0x02),
    (74167000, 48, 0x42, 0x00),
    (111250000, 32, 0x82, 0x02),
    (148334000, 24, 0x22, 0x00),
    (222500000, 16, 0x42, 0x02),
    (296667000, 12, 0x12, 0x00),
    (445000000, 8, 0x22, 0x02),
    (593334000, 6, 0x0A, 0x00),
    (950000000, 4, 0x12, 0x02),
    (None, 2, 0x0A, 0x02),
)

# VHF track selection from fc0013_set_vhf_track, ordered by inclusive upper
# bound. Upstream's last VHF case is a strict < 300 MHz and is handled in code.
_FC0013_VHF_TRACK = (
    (177500000, 0x1C),
    (184500000, 0x18),
    (191500000, 0x14),
    (198500000, 0x10),
    (205500000, 0x0C),
    (219500000, 0x08),
)

# -- tuner identification and frequency limits -----------------------------

FC0013_I2C_ADDR = 0xC6
FC0013_CHECK_ADDR = 0x00
FC0013_CHECK_VAL = 0xA3
R82XX_I2C_ADDR = 0x34
R82XX_CHECK_VAL = 0x69

# Lowest centre the R82xx PLL reaches: LO = RF + 2.125 MHz IF must be at
# least 1.77 GHz / 64.
R82XX_MIN = 25600000
R82XX_MAX = 1760000000
DIRECT_MIN = 100000
FC0013_MIN = 22000000
FC0013_MAX = 1100000000


def reverse8(n):
    n = ((n & 0x55) << 1) | ((n >> 1) & 0x55)
    n = ((n & 0x33) << 2) | ((n >> 2) & 0x33)
    return ((n & 15) << 4) | (n >> 4)


def sample_ratio(rate, crystal=CRYSTAL):
    if rate <= 225000 or rate > 3200000 or 300000 < rate <= 900000:
        raise ValueError("unsupported RTL2832 sample rate")
    ratio = ((crystal << 22) // rate) & 0x0FFFFFFC
    real_ratio = ratio | ((ratio & 0x08000000) << 1)
    return ratio, (crystal << 22) / real_ratio


def pll_values(freq, fine=2, crystal=CRYSTAL):
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


class RTL2832:
    """RTL2832U USB transport and demodulator, shared by both tuner drivers.

    On its own it has no tuner layer; detect_tuner() uses it to probe.
    """

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

    def _init_baseband(self):
        """rtlsdr_init_baseband plus the USB endpoint setup."""
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

    def _if(self, frequency):
        value = -((frequency << 22) // CRYSTAL)
        for reg, val in (
            (0x19, (value >> 16) & 0x3F),
            (0x1A, (value >> 8) & 255),
            (0x1B, value & 255),
        ):
            self.demod(1, reg, val)

    def _set_bandwidth(self):
        """Set the tuner's analog bandwidth and self.if_freq to match."""
        raise NotImplementedError

    def set_sample_rate(self, rate):
        # The narrow-band analog filter paths are deliberately limited to low rates.
        if not 225000 < rate <= 300000:
            raise ValueError("sample rate must be 225001..300000 samples/s")
        ratio, exact = sample_ratio(rate)
        self._set_bandwidth()
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


class R82xxHam(RTL2832):
    """RTL2832U with an R820T(2)/R860 tuner: wide-range tuning and HF direct
    sampling.

    direct_input selects the ADC used for direct sampling: 'Q' (the
    RTL-SDR convention, librtlsdr direct_sampling=2) or 'I'.
    """

    tuner_name = "R82xx"
    min_frequency = DIRECT_MIN
    max_frequency = R82XX_MAX

    def __init__(self, device, direct_input="Q", **kwargs):
        super().__init__(device, **kwargs)
        self.direct = False
        self.direct_input = direct_input
        self.conjugate = False
        self._gain = None
        self._rate = 256000

    # -- tuner I2C -------------------------------------------------------

    def _i2c_write(self, data):
        self._control(0x40, R82XX_I2C_ADDR, 0x610, data)

    def _tread(self, length, reverse=True):
        self._i2c_write(bytes((0,)))
        data = self._control(0xC0, R82XX_I2C_ADDR, 0x600, bytearray(length))
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

    # -- tuner bring-up --------------------------------------------------

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
        self._twrite(5, _R82XX_INIT)
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

    def _set_bandwidth(self):
        self.repeater(True)
        try:
            self._tmask(0x0A, 0, 0x10)
            self._tmask(0x0B, 0xE6, 0xEF)  # 350 kHz minimum analog bandwidth.
            self.if_freq = 2125000
        finally:
            self.repeater(False)

    def _enter_direct(self):
        # rtlsdr_set_direct_sampling(dev, on)
        self.repeater(True)
        try:
            for register, value in _R82XX_STANDBY:
                self._twrite(register, bytes((value,)))
        finally:
            self.repeater(False)
        self.demod(1, 0xB1, 0x1A)  # disable zero-IF mode
        self.demod(1, 0x15, 0x00)  # no spectrum inversion
        self.demod(0, 0x08, 0x4D)  # one ADC input only
        self.demod(0, 0x06, 0x90 if self.direct_input == "Q" else 0x80)
        # The RTL2832U's own AGC helps the 8-bit ADC with weak HF signals.
        self.demod(0, 0x19, 0x25)
        self.direct = True

    # -- public interface ------------------------------------------------

    def initialize(self, frequency, sample_rate=256000, gain=280):
        """Initialize already-configured device. Gain is tenths of a dB or None for AGC."""
        # A full bring-up also leaves direct sampling: it restores the I-only
        # low-IF demodulator settings and re-initializes the tuner.
        self.direct = False
        self.frequency = 0
        self._gain = gain
        self._rate = sample_rate  # the int request; self.sample_rate is the exact float
        # The tuner is brought up within its own range; HF switches to direct
        # sampling afterwards.
        start = frequency if frequency >= R82XX_MIN else 100000000
        self._init_baseband()
        self.repeater(True)
        try:
            self.tuner_id = self._tread(1, False)[0]
            if self.tuner_id != R82XX_CHECK_VAL:
                raise RuntimeError(
                    "R82xx tuner probe got 0x%02x, expected 0x%02x"
                    % (self.tuner_id, R82XX_CHECK_VAL)
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
        self.tune(start)
        self.reset_buffer()
        if self.log:
            self.log(
                "R82xx ready",
                self.frequency,
                self.sample_rate,
                "cal",
                self.calibration,
                "lock",
                self.locked,
            )
        if frequency != start:
            self.tune(frequency)

    def set_gain(self, gain=None):
        """Gain is tenths of a dB, or None for tuner AGC. Remembered, but not
        applied, while direct sampling bypasses the tuner."""
        self._gain = gain
        if self.direct:
            return
        self.repeater(True)
        try:
            if gain is None:
                for r, v, m in ((5, 0, 0x10), (7, 0x10, 0x10), (0x0C, 0x0B, 0x9F)):
                    self._tmask(r, v, m)
            else:
                for r, v, m in ((5, 0x10, 0x10), (7, 0, 0x10), (0x0C, 8, 0x9F)):
                    self._tmask(r, v, m)
                total = lna = mix = 0
                for i in range(15):
                    if total >= gain:
                        break
                    lna += 1
                    total += _R82XX_LNA[lna]
                    if total >= gain:
                        break
                    mix += 1
                    total += _R82XX_MIX[mix]
                self._tmask(5, lna, 15)
                self._tmask(7, mix, 15)
        finally:
            self.repeater(False)

    def tune(self, frequency):
        if not self.min_frequency <= frequency <= self.max_frequency:
            raise ValueError("R82xx receiver tunes 0.1 MHz - 1760 MHz")
        if frequency < R82XX_MIN:
            if not self.direct:
                self._enter_direct()
            # The ADC samples at 28.8 MHz. Above 14.4 MHz the signal is in the
            # second Nyquist zone and arrives mirrored at 28.8 MHz - f.
            if frequency <= CRYSTAL // 2:
                self._if(frequency)
                self.conjugate = False
            else:
                self._if(CRYSTAL - frequency)
                self.conjugate = True
            self.frequency = frequency
            return
        if self.direct:
            # Leaving HF: full re-initialization, as librtlsdr does.
            self.initialize(frequency, self._rate, self._gain)
            return
        lo = frequency + self.if_freq
        mhz = lo // 1000000
        entry = _R82XX_RANGES[0]
        for candidate in _R82XX_RANGES:
            if mhz < candidate[0]:
                break
            entry = candidate
        _, open_d, rf_mux, tf_c = entry
        self.repeater(True)
        try:
            # r82xx_set_mux, then r82xx_set_pll.
            for r, v, m in (
                (0x17, open_d, 0x08),
                (0x1A, rf_mux, 0xC3),
                (0x1B, tf_c, 255),
                (0x10, 0, 0x0B),
                (8, 0, 0x3F),
                (9, 0, 0x3F),
            ):
                self._tmask(r, v, m)
            self._pll(lo)
        finally:
            self.repeater(False)
        self.conjugate = False
        self.frequency = frequency


class FC0013Ham(RTL2832):
    """RTL2832U with a Fitipower FC0013 tuner, zero-IF, 22 MHz - 1.1 GHz.

    Direct sampling is not wired on FC0013 dongles, so there is no HF. The
    FC0013 differs from the R82xx in three independent ways:

    * it answers at I2C address 0xc6, not 0x34, and register reads are not
      bit-reversed;
    * it is a zero-IF tuner, so the RTL2832U keeps its baseband defaults
      (en_bbin set, no spectrum inversion, IF frequency 0) and takes I+Q ADC
      input instead of I-only at a low IF;
    * it has no tunable narrow IF filter and no PLL lock flag.
    """

    tuner_name = "FC0013"
    min_frequency = FC0013_MIN
    max_frequency = FC0013_MAX
    direct = False
    conjugate = False

    def __init__(
        self, device, timeout=1000, log=print, max_packet=64, bandwidth=6000000
    ):
        super().__init__(device, timeout=timeout, log=log, max_packet=max_packet)
        self.bandwidth = bandwidth
        self.vco_calibration = None
        # The FC0013 exposes no PLL lock flag through this register interface.
        self.locked = None

    # -- tuner I2C -------------------------------------------------------
    # Plain register-address-then-data access, no bit reversal.

    def _i2c_write(self, data):
        self._control(0x40, FC0013_I2C_ADDR, 0x610, data)

    def _treg_read(self, register):
        self._i2c_write(bytes((register,)))
        return self._control(0xC0, FC0013_I2C_ADDR, 0x600, bytearray(1))[0]

    def _treg_write(self, register, value):
        value &= 255
        self._i2c_write(bytes((register, value)))
        self.shadow[register] = value

    # -- tuner bring-up --------------------------------------------------

    def _tuner_init(self):
        registers = list(_FC0013_INIT)
        registers[0x07] |= 0x20  # 27 MHz or 28.8 MHz crystal
        registers[0x0C] |= 0x02  # dual master
        for register in range(1, len(registers)):
            self._treg_write(register, registers[register])

    def _set_vhf_track(self, frequency):
        value = self._treg_read(0x1D) & 0xE3
        bits = 0x1C  # UHF and GPS, and the >= 300 MHz fallback
        for bound, candidate in _FC0013_VHF_TRACK:
            if frequency <= bound:
                bits = candidate
                break
        else:
            if frequency < 300000000:
                bits = 0x04
        self._treg_write(0x1D, value | bits)

    def _set_params(self, frequency, bandwidth):
        """Port of fc0013_set_params. C integer widths are reproduced exactly."""
        half_crystal = CRYSTAL // 2
        self._set_vhf_track(frequency)
        if frequency < 300000000:
            self._treg_write(0x07, self._treg_read(0x07) | 0x10)  # enable VHF filter
            self._treg_write(0x14, self._treg_read(0x14) & 0x1F)  # disable UHF and GPS
        else:
            self._treg_write(0x07, self._treg_read(0x07) & 0xEF)  # disable VHF filter
            self._treg_write(0x14, (self._treg_read(0x14) & 0x1F) | 0x40)

        reg = [0] * 7
        for bound, multi, reg5, reg6 in _FC0013_DIVIDERS:
            if bound is None or frequency < bound:
                break
        reg[5], reg[6] = reg5, reg6

        vco = frequency * multi
        vco_select = 0
        if vco >= 3060000000:
            reg[6] |= 0x08
            vco_select = 1

        quotient = vco // half_crystal
        xdiv = quotient & 0xFFFF
        if (vco - xdiv * half_crystal) >= (half_crystal // 2):
            xdiv = (xdiv + 1) & 0xFFFF

        pm = (xdiv // 8) & 255
        am = (xdiv - 8 * pm) & 255
        if am < 2:
            am += 8
            pm -= 1
        if pm > 31:
            reg[1] = (am + 8 * (pm - 31)) & 255
            reg[2] = 31
        else:
            reg[1] = am
            reg[2] = pm
        if reg[1] > 15 or reg[2] < 0x0B:
            raise ValueError("no valid FC0013 PLL combination for %d Hz" % frequency)

        reg[6] |= 0x20  # fix clock out

        # Fractional part of the delta-sigma PLL. Upstream reuses one uint16_t.
        xin = ((vco - quotient * half_crystal) // 1000) & 0xFFFF
        xin = ((xin << 15) // (half_crystal // 1000)) & 0xFFFF
        if xin >= 16384:
            xin = (xin + 32768) & 0xFFFF
        reg[3] = xin >> 8
        reg[4] = xin & 0xFF

        reg[6] &= 0x3F  # bits 6 and 7 select the analog bandwidth
        if bandwidth == 6000000:
            reg[6] |= 0x80
        elif bandwidth == 7000000:
            reg[6] |= 0x40

        reg[5] |= 0x07  # modified for the Realtek demodulator

        for register in range(1, 7):
            self._treg_write(register, reg[register])

        value = self._treg_read(0x11)
        self._treg_write(0x11, value | 0x04 if multi == 64 else value & 0xFB)

        self._treg_write(0x0E, 0x80)  # VCO calibration
        self._treg_write(0x0E, 0x00)
        self._treg_write(0x0E, 0x00)  # re-calibrate if needed
        # Upstream leaves its 10 ms settling delay commented out. Real hardware
        # needs it; it changes timing only, never register state.
        time.sleep(0.01)
        calibration = self._treg_read(0x0E) & 0x3F
        self.vco_calibration = calibration

        # Retry once on the far side of the selected VCO range.
        if vco_select:
            retry = calibration > 0x3C
            reg[6] &= ~0x08 & 0xFF
        else:
            retry = calibration < 0x02
            reg[6] |= 0x08
        if retry:
            self._treg_write(0x06, reg[6])
            self._treg_write(0x0E, 0x80)
            self._treg_write(0x0E, 0x00)

    def _set_bandwidth(self):
        # The FC0013 analog filter does not narrow below a DVB-T channel, so
        # adjacent-channel rejection relies on the RTL2832U decimation chain.
        self.if_freq = 0

    # -- public interface ------------------------------------------------

    def initialize(self, frequency, sample_rate=256000, gain=280):
        """Initialize already-configured device. Gain is tenths of a dB or None for AGC."""
        self._init_baseband()
        self.repeater(True)
        try:
            self.tuner_id = self._treg_read(FC0013_CHECK_ADDR)
            if self.tuner_id != FC0013_CHECK_VAL:
                raise RuntimeError(
                    "FC0013 tuner probe got 0x%02x, expected 0x%02x"
                    % (self.tuner_id, FC0013_CHECK_VAL)
                )
            # Zero-IF tuner: keep the baseband defaults and take both ADC
            # inputs. These are written explicitly because the R82xx path
            # leaves I-only mode and a 3.57 MHz IF behind in the same chip.
            self.if_freq = 0
            self._if(0)
            self.demod(0, 8, 0xCD)  # in-phase + quadrature ADC input
            self.demod(1, 0xB1, 0x1B)  # zero-IF mode
            self.demod(1, 0x15, 0)  # no spectrum inversion
            self._tuner_init()
        finally:
            self.repeater(False)
        self.set_sample_rate(sample_rate)
        self.set_gain(gain)
        self.tune(frequency)
        self.reset_buffer()
        if self.log:
            self.log(
                "FC0013 ready",
                self.frequency,
                self.sample_rate,
                "vco_cal",
                self.vco_calibration,
            )

    def set_gain(self, gain=None):
        """Gain is tenths of a dB, or None for tuner AGC.

        The FC0013 tops out at 19.7 dB, far below the R82xx. A larger request
        selects maximum gain rather than failing.
        """
        self.repeater(True)
        try:
            value = self._treg_read(0x0D)
            value = value | 0x08 if gain is not None else value & ~0x08 & 0xFF
            self._treg_write(0x0D, value)
            self._treg_write(0x13, 0x0A)  # fixed IF gain
            if gain is not None:
                value = self._treg_read(0x14) & 0xE0
                for index, (step, bits) in enumerate(_FC0013_LNA_GAINS):
                    if step >= gain or index + 1 == len(_FC0013_LNA_GAINS):
                        value |= bits
                        break
                self._treg_write(0x14, value)
        finally:
            self.repeater(False)

    def tune(self, frequency):
        if not self.min_frequency <= frequency <= self.max_frequency:
            raise ValueError("FC0013 receiver tunes 22 MHz - 1100 MHz")
        # Zero-IF: the tuner is driven to the carrier, with no IF offset.
        self.repeater(True)
        try:
            self._set_params(frequency, self.bandwidth)
        finally:
            self.repeater(False)
        self.frequency = frequency


def detect_tuner(device, log=None, max_packet=64, timeout=1000):
    """Bring up the RTL2832U and report which supported tuner is fitted.

    Returns "FC0013", "R82xx", or None. Probe order follows librtlsdr.
    """
    probe = RTL2832(device, timeout=timeout, log=None, max_packet=max_packet)
    probe._init_baseband()

    def identify(address, register):
        probe._control(0x40, address, 0x610, bytes((register,)))
        return probe._control(0xC0, address, 0x600, bytearray(1))[0]

    probe.repeater(True)
    try:
        for address, register, expected, name in (
            (FC0013_I2C_ADDR, FC0013_CHECK_ADDR, FC0013_CHECK_VAL, "FC0013"),
            (R82XX_I2C_ADDR, 0, R82XX_CHECK_VAL, "R82xx"),
        ):
            try:
                # A missing tuner STALLs rather than answering; that is not fatal
                # here, it only means this address is not the one fitted.
                if identify(address, register) == expected:
                    return name
            except OSError:
                continue
    finally:
        probe.repeater(False)
        if log:
            log("tuner probe complete")
    return None


def open_ham_receiver(device, log=print, max_packet=64, timeout=1000, direct_input="Q"):
    """Return a driver instance for the tuner actually fitted."""
    found = detect_tuner(device, log=None, max_packet=max_packet, timeout=timeout)
    if log:
        log("tuner detected", found)
    if found == "FC0013":
        return FC0013Ham(device, timeout=timeout, log=log, max_packet=max_packet)
    if found == "R82xx":
        return R82xxHam(
            device,
            direct_input=direct_input,
            timeout=timeout,
            log=log,
            max_packet=max_packet,
        )
    raise RuntimeError("no supported tuner found (expected FC0013 or R82xx)")
