# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Controls for the TE YZY SP-1 under CircuitPython: buttons, faders, battery."""

import time

import analogio
import board
import digitalio

__version__ = "1.0.0"

ADC_MAX = 65535

# CP 16-bit medians for the shared ladder network
RUNGS = (3840, 7200, 13056, 21713, 32593)

# Which button each rung is, per channel. `None` = rung not populated.
LADDER1_NAMES = ("TRACK1", "TRACK2", "TRACK3", "TRACK4", "PLAY")
LADDER2_NAMES = (None, "ROCKER-", "VOL-", "ROCKER+", "VOL+")

BUTTONS = tuple(n for n in LADDER1_NAMES + LADDER2_NAMES if n)

IDLE_MAX = 1920

# A reading must land this close to a rung to count as that button, as a
# fraction of the rung value with an absolute floor.
TOLERANCE = 0.03
TOLERANCE_FLOOR = 250

# How long a decoded state must persist before it is reported.
DEBOUNCE = 0.02

# Median of this many reads per channel per update, to shrug off single-sample
# ADC noise.
SAMPLES = 3

RAIL_SETTLE = 0.001

# Faders: all four reach 0 at the bottom stop and ~65200 at the top
FADER_TOP = 65200
FADER_DEADBAND = 384
FADER_SNAP = 384
FADER_NAMES = ("FADER1", "FADER2", "FADER3", "FADER4")

VDD = 3.27
BATTERY_DIVIDER = 0.497

# Approximate resting discharge curve for a single-cell LiPo
BATTERY_CURVE = (
    (4.20, 100),
    (4.10, 90),
    (4.00, 80),
    (3.93, 70),
    (3.87, 60),
    (3.82, 50),
    (3.79, 40),
    (3.77, 30),
    (3.73, 20),
    (3.68, 10),
    (3.50, 5),
    (3.30, 0),
)


# --------------------------------------------------------------------------
# pure functions (no hardware; testable off-device)


def decode(raw, names):
    """One ladder reading -> button name, or None.

    Returns None both for "nothing held" (below IDLE_MAX) and for a reading
    that matches no rung within TOLERANCE
    """
    if raw < IDLE_MAX:
        return None
    best, best_err = None, None
    for i, rung in enumerate(RUNGS):
        err = abs(raw - rung)
        if best_err is None or err < best_err:
            best, best_err = i, err
    if best_err > rung_tolerance(RUNGS[best]):
        return None
    # An unpopulated rung (LADDER2's lowest) is `None` in the name map, so a
    # reading there reports as unknown rather than as a neighbour's button.
    return names[best] if best < len(names) else None


def rung_tolerance(rung):
    """Acceptance half-window around a rung, in counts."""
    t = int(rung * TOLERANCE)
    return t if t > TOLERANCE_FLOOR else TOLERANCE_FLOOR


def thresholds(names):
    """Adjacent-rung midpoints for a channel, for reference and testing."""
    used = [RUNGS[i] for i, n in enumerate(names) if n]
    return [(a + b) // 2 for a, b in zip(used, used[1:])]


def fader_scale(raw):
    """Raw fader reading -> 0.0 at the bottom stop, 1.0 at the top."""
    if raw <= FADER_SNAP:
        return 0.0
    if raw >= FADER_TOP - FADER_SNAP:
        return 1.0
    return raw / FADER_TOP


def battery_volts(raw):
    """Raw VBATT reading -> pack volts through the 1:2 divider."""
    return raw / ADC_MAX * VDD / BATTERY_DIVIDER


def battery_pct(volts):
    """Pack volts -> approximate percent, via BATTERY_CURVE."""
    if volts >= BATTERY_CURVE[0][0]:
        return 100.0
    for (v_hi, p_hi), (v_lo, p_lo) in zip(BATTERY_CURVE, BATTERY_CURVE[1:]):
        if volts >= v_lo:
            return p_lo + (volts - v_lo) * (p_hi - p_lo) / (v_hi - v_lo)
    return 0.0


class Controls:
    """The SP-1's ladder buttons, faders and battery gauge.

    Construct once, call `update()` as often as you like. Each part is
    optional so a program that only wants faders does not claim the ADC
    channels it will not read:

        Controls(buttons=True, faders=True, battery=True, charger=True)

    Pass `rail=` your own `DigitalInOut` on LADDER_POWER if your code already
    owns that pin (constructing a second one raises ValueError).
    """

    def __init__(
        self,
        buttons=True,
        faders=True,
        battery=True,
        charger=True,
        rail=None,
        debounce=DEBOUNCE,
        samples=SAMPLES,
    ):
        self.debounce = debounce
        self.samples = samples

        self._owns_rail = rail is None
        if rail is None:
            rail = digitalio.DigitalInOut(board.LADDER_POWER)
            rail.direction = digitalio.Direction.OUTPUT
        rail.value = True
        self.rail = rail
        time.sleep(RAIL_SETTLE)

        self._ladders = ()
        if buttons:
            self._ladders = (
                (analogio.AnalogIn(board.LADDER1), LADDER1_NAMES),
                (analogio.AnalogIn(board.LADDER2), LADDER2_NAMES),
            )
        self._state = [[None, None, 0.0, 0] for _ in self._ladders]

        self._faders = ()
        self._fader_raw = [0] * len(FADER_NAMES)
        if faders:
            self._faders = tuple(
                analogio.AnalogIn(getattr(board, n)) for n in FADER_NAMES
            )
            self._fader_raw = [f.value for f in self._faders]

        self._battery = analogio.AnalogIn(board.VBATT) if battery else None

        self._power_good = self._charge_status = None
        if charger:
            self._power_good = digitalio.DigitalInOut(board.POWER_GOOD)
            self._power_good.direction = digitalio.Direction.INPUT
            self._charge_status = digitalio.DigitalInOut(board.CHARGE_STATUS)
            self._charge_status.direction = digitalio.Direction.INPUT

    def deinit(self):
        """Release every pin. Safe to call twice."""
        for adc, _ in self._ladders:
            adc.deinit()
        self._ladders = ()
        for f in self._faders:
            f.deinit()
        self._faders = ()
        for obj in (self._battery, self._power_good, self._charge_status):
            if obj is not None:
                obj.deinit()
        self._battery = self._power_good = self._charge_status = None
        if self.rail is not None:
            if self._owns_rail:
                self.rail.deinit()
            self.rail = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.deinit()

    # -- buttons -----------------------------------------------------------

    def _read(self, adc):
        s = sorted(adc.value for _ in range(self.samples))
        return s[len(s) // 2]

    def update(self):
        """Sample everything once; return a list of (name, pressed) events.

        `pressed` is True for a press, False for a release.
        """
        events = []
        now = time.monotonic()
        for i, (adc, names) in enumerate(self._ladders):
            raw = self._read(adc)
            st = self._state[i]
            st[3] = raw
            name = decode(raw, names)
            if name != st[1]:  # candidate changed; restart
                st[1], st[2] = name, now
            elif name != st[0] and now - st[2] >= self.debounce:
                if st[0] is not None:
                    events.append((st[0], False))
                if name is not None:
                    events.append((name, True))
                st[0] = name
        for i, f in enumerate(self._faders):
            raw = f.value
            if abs(raw - self._fader_raw[i]) >= FADER_DEADBAND:
                self._fader_raw[i] = raw
        return events

    @property
    def pressed(self):
        """The set of button names currently held (0-2 of them)."""
        return {st[0] for st in self._state if st[0] is not None}

    def is_pressed(self, name):
        return name in self.pressed

    @property
    def last_raw(self):
        """Most recent (LADDER1, LADDER2) readings"""
        return tuple(st[3] for st in self._state)

    # -- faders ------------------------------------------------------------

    @property
    def faders(self):
        """All four faders as floats, left to right, 0.0 (bottom) to 1.0."""
        return tuple(fader_scale(r) for r in self._fader_raw)

    def fader(self, n):
        """One fader by 1-based number, as the panel labels them."""
        return fader_scale(self._fader_raw[n - 1])

    @property
    def fader_raw(self):
        return tuple(self._fader_raw)

    # -- battery -----------------------------------------------------------

    @property
    def battery_voltage(self):
        """Pack volts, or None if the battery channel was not claimed."""
        if self._battery is None:
            return None
        s = sorted(self._battery.value for _ in range(self.samples))
        return battery_volts(s[len(s) // 2])

    @property
    def battery_percent(self):
        """Approximate charge percent. Reads high while charging"""
        v = self.battery_voltage
        return None if v is None else battery_pct(v)

    @property
    def usb_power(self):
        """True when the charger sees good input power (nPGOOD, active low)."""
        return None if self._power_good is None else not self._power_good.value

    @property
    def charging(self):
        """True while the charger is actually charging (nCHG, active low)."""
        return None if self._charge_status is None else not self._charge_status.value


# --------------------------------------------------------------------------


def monitor(seconds=None, interval=0.01, controls=None):
    """Print button events, faders and battery until `seconds` elapse."""
    c = controls or Controls()
    end = None if seconds is None else time.monotonic() + seconds
    print(
        "battery {:.2f} V ({:.0f}%) usb={} charging={}".format(
            c.battery_voltage, c.battery_percent, c.usb_power, c.charging
        )
    )
    print("faders", ", ".join("{:.3f}".format(v) for v in c.faders))
    last = c.fader_raw
    try:
        while end is None or time.monotonic() < end:
            for name, down in c.update():
                print(
                    "{:8.3f}  {:9s} {}".format(
                        time.monotonic(), name, "down" if down else "up"
                    ),
                    "  raw",
                    c.last_raw,
                )
            if c.fader_raw != last:
                last = c.fader_raw
                print(
                    "{:8.3f}  faders   ".format(time.monotonic()),
                    ", ".join("{:.3f}".format(v) for v in c.faders),
                )
            time.sleep(interval)
    finally:
        if controls is None:
            c.deinit()
