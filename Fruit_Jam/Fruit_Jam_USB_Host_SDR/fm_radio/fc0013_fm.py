# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Derived from works:
# Original copyright (C) 2012 Hans-Frieder Vogt;
# partially based on driver code from Fitipower,
# (C) 2010 Fitipower Integrated Technology Inc;
# modified for use in librtlsdr (C) 2012 Steve Markgraf.

"""CircuitPython port of the osmocom rtl-sdr Fitipower FC0013 tuner driver.

Minimal experimental RTL2832U/FC0013 FM receive driver.

Companion to `rtl2832_fm.py`. The RTL2832U transport and demodulator layer is
inherited unchanged from `RTL2832FM`; only the tuner layer is replaced, because
the FC0013 differs from the R82xx in three independent ways:

* it answers at I2C address 0xc6, not 0x34, and register reads are not
  bit-reversed;
* it is a zero-IF tuner, so the RTL2832U keeps its baseband defaults
  (en_bbin set, no spectrum inversion, IF frequency 0) and takes I+Q ADC
  input instead of I-only at 3.57 MHz;
* it has no tunable narrow IF filter and no PLL lock flag.

No USB discovery or configuration is performed automatically. Pass an already
configured usb.core.Device. FM-only tuning is intentional. All reads use caller
provided buffers as required by CircuitPython. No claim of lossless capture is
made: transport must separately sustain 2 * sample_rate bytes/second.
"""
import time
from rtl2832_fm import RTL2832FM, sample_ratio, _FIR

# pylint: disable=too-many-locals, too-many-statements, too-many-branches, protected-access

FC0013_I2C_ADDR = 0xC6
FC0013_CHECK_ADDR = 0x00
FC0013_CHECK_VAL = 0xA3
R820T_I2C_ADDR = 0x34
R82XX_CHECK_VAL = 0x69

# registers 0x00..0x15. Index 0 is a dummy and is
# never written. Upstream applies two unconditional modifications after this
# table is declared; they are applied in _tuner_init to keep the correspondence
# with the reference source visible.
_INIT = (
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

# tenths of a dB paired with register value.
_LNA_GAINS = (
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
_DIVIDERS = (
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
_VHF_TRACK = (
    (177500000, 0x1C),
    (184500000, 0x18),
    (191500000, 0x14),
    (198500000, 0x10),
    (205500000, 0x0C),
    (219500000, 0x08),
)


def init_baseband(radio):
    """RTL2832U bring-up shared by tuner probing and FC0013 initialization.

    This is rtlsdr_init_baseband plus the endpoint setup the packaged R82xx
    driver performs in RTL2832FM.initialize.
    """
    radio.write_reg(1, 0x2000, 9)
    # EPA register is little endian, while write_reg emits big endian.
    radio.write_reg(
        1, 0x2158, ((radio.max_packet & 255) << 8) | (radio.max_packet >> 8), 2
    )
    radio.write_reg(1, 0x2148, 0x1002, 2)
    radio.write_reg(2, 0x300B, 0x22)
    radio.write_reg(2, 0x3000, 0xE8)
    for args in ((1, 1, 0x14), (1, 1, 0x10), (1, 0x15, 0), (1, 0x16, 0, 2)):
        radio.demod(*args)
    for i in range(6):
        radio.demod(1, 0x16 + i, 0)
    fir = bytearray(x & 255 for x in _FIR[:8])
    for i in range(8, 16, 2):
        a, b = _FIR[i], _FIR[i + 1]
        fir.extend(((a >> 4) & 255, ((a << 4) | ((b >> 8) & 15)) & 255, b & 255))
    for i, value in enumerate(fir):
        radio.demod(1, 0x1C + i, value)
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
        radio.demod(*args)


class RTL2832FC0013(RTL2832FM):
    """RTL2832U with a Fitipower FC0013 tuner, zero-IF, FM broadcast only."""

    tuner_name = "FC0013"

    def __init__(
        self, device, timeout=1000, log=print, max_packet=64, bandwidth=6000000
    ):
        super().__init__(device, timeout=timeout, log=log, max_packet=max_packet)
        self.bandwidth = bandwidth
        self.vco_calibration = None
        # The FC0013 exposes no PLL lock flag through this register interface.
        self.locked = None

    # -- tuner I2C -------------------------------------------------------
    # The FC0013 uses plain register-address-then-data access at 0xc6 with no
    # bit reversal, so none of the R82xx helpers are reusable.

    def _i2c_write(self, data):
        self._control(0x40, FC0013_I2C_ADDR, 0x610, data)

    def _treg_read(self, register):
        self._i2c_write(bytes((register,)))
        return self._control(0xC0, FC0013_I2C_ADDR, 0x600, bytearray(1))[0]

    def _treg_write(self, register, value):
        value &= 255
        self._i2c_write(bytes((register, value)))
        self.shadow[register] = value

    def _tread(self, length, reverse=True):
        raise NotImplementedError("R82xx burst read is not valid for the FC0013")

    def _twrite(self, register, data):
        raise NotImplementedError("R82xx burst write is not valid for the FC0013")

    def _tmask(self, register, value, mask=255):
        raise NotImplementedError("R82xx shadow mask is not valid for the FC0013")

    def _pll(self, freq):
        raise NotImplementedError("R82xx PLL is not valid for the FC0013")

    # -- tuner bring-up --------------------------------------------------

    def _tuner_init(self):
        registers = list(_INIT)
        registers[0x07] |= 0x20  # 27 MHz or 28.8 MHz crystal
        registers[0x0C] |= 0x02  # dual master
        for register in range(1, len(registers)):
            self._treg_write(register, registers[register])

    def _set_vhf_track(self, frequency):
        value = self._treg_read(0x1D) & 0xE3
        bits = 0x1C  # UHF and GPS, and the >= 300 MHz fallback
        for bound, candidate in _VHF_TRACK:
            if frequency <= bound:
                bits = candidate
                break
        else:
            if frequency < 300000000:
                bits = 0x04
        self._treg_write(0x1D, value | bits)

    def _set_params(self, frequency, bandwidth):
        """Port of fc0013_set_params. C integer widths are reproduced exactly."""
        half_crystal = 28800000 // 2
        self._set_vhf_track(frequency)
        if frequency < 300000000:
            self._treg_write(0x07, self._treg_read(0x07) | 0x10)  # enable VHF filter
            self._treg_write(0x14, self._treg_read(0x14) & 0x1F)  # disable UHF and GPS
        else:
            self._treg_write(0x07, self._treg_read(0x07) & 0xEF)  # disable VHF filter
            self._treg_write(0x14, (self._treg_read(0x14) & 0x1F) | 0x40)

        reg = [0] * 7
        for bound, multi, reg5, reg6 in _DIVIDERS:
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

    # -- public interface ------------------------------------------------

    def initialize(self, frequency=100100000, sample_rate=240000, gain=280):
        """Initialize already-configured device. Gain is tenths of a dB or None for AGC."""
        init_baseband(self)
        self.repeater(True)
        try:
            self.tuner_id = self._treg_read(FC0013_CHECK_ADDR)
            if self.tuner_id != FC0013_CHECK_VAL:
                raise RuntimeError(
                    "FC0013 tuner probe got 0x%02x, expected 0x%02x"
                    % (self.tuner_id, FC0013_CHECK_VAL)
                )
            # Zero-IF tuner: keep the baseband defaults and take both ADC
            # inputs.
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

    def set_sample_rate(self, rate):
        # This narrow-band path is deliberately limited to low rates. The
        # FC0013 analog filter does not narrow below a DVB-T channel, so
        # adjacent-channel rejection relies on the RTL2832U decimation chain.
        if not 225000 < rate <= 300000:
            raise ValueError("FM driver accepts 225001..300000 samples/s")
        ratio, exact = sample_ratio(rate)
        self.if_freq = 0
        self._if(0)
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
                for index, (step, bits) in enumerate(_LNA_GAINS):
                    if step >= gain or index + 1 == len(_LNA_GAINS):
                        value |= bits
                        break
                self._treg_write(0x14, value)
        finally:
            self.repeater(False)

    def tune(self, frequency):
        if not 87500000 <= frequency <= 108000000:
            raise ValueError("FM-only driver accepts 87.5..108 MHz")
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
    probe = RTL2832FM(device, timeout=timeout, log=None, max_packet=max_packet)
    init_baseband(probe)

    def identify(address, register):
        # Address the tuner explicitly: RTL2832FM._i2c_write is fixed at the
        # R82xx address and cannot be reused for the FC0013.
        probe._control(0x40, address, 0x610, bytes((register,)))
        return probe._control(0xC0, address, 0x600, bytearray(1))[0]

    probe.repeater(True)
    try:
        for address, register, expected, name in (
            (FC0013_I2C_ADDR, FC0013_CHECK_ADDR, FC0013_CHECK_VAL, "FC0013"),
            (R820T_I2C_ADDR, 0, R82XX_CHECK_VAL, "R82xx"),
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


def open_receiver(device, log=print, max_packet=64, timeout=1000):
    """Return a driver instance matching the tuner actually fitted."""
    found = detect_tuner(device, log=None, max_packet=max_packet, timeout=timeout)
    if log:
        log("tuner detected", found)
    if found == "FC0013":
        return RTL2832FC0013(device, timeout=timeout, log=log, max_packet=max_packet)
    if found == "R82xx":
        return RTL2832FM(device, timeout=timeout, log=log, max_packet=max_packet)
    raise RuntimeError("no supported tuner found (expected FC0013 or R82xx)")
