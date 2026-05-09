# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Simple battery voltage monitor for the Beacon Ears.

Reads the BFF's voltage divider on board.A2 and exposes a `voltage`
property. We keep this minimal: no state machine, no auto-warnings, no
ambient rendering. The voltage is consumed only by the on-demand
battery display in code.py when the user explicitly asks for it.

Note: the ESP32-S3 ADC reads voltages higher than actual (uncalibrated
ADC gain error). We don't try to correct this - instead the thresholds
in code.py are tuned to match what the QT Py actually reports for
known battery states.
'''
# Target: Adafruit QT Py ESP32-S3 - the BLE Beacon Ears
import time

import analogio
import board

_ADC_FULL_SCALE = 65535
_DIVIDER_RATIO = 2.0

_SAMPLES_PER_READ = 10
_SAMPLE_INTERVAL_S = 5.0


class BatteryMonitor:
    '''Polls battery voltage on A2. No state machine, no auto-rendering.'''

    def __init__(self):
        try:
            self._pin = analogio.AnalogIn(board.A2)
        except (AttributeError, ValueError):
            self._pin = None
        self._last_read_t = 0.0
        self._last_voltage = None

    def _read_voltage(self):
        '''Read and average N ADC samples, return raw volts on the cell.'''
        if self._pin is None:
            return None
        total = 0
        for _ in range(_SAMPLES_PER_READ):
            total += self._pin.value
        avg = total / _SAMPLES_PER_READ
        ref_v = self._pin.reference_voltage
        return (avg / _ADC_FULL_SCALE) * ref_v * _DIVIDER_RATIO

    def update(self, force=False):
        '''Refresh voltage reading if enough time has passed.

        If force=True, read voltage immediately regardless of interval.
        Useful when responding to a user trigger - we want the value
        shown to reflect the moment of the press, not 5 seconds ago.
        '''
        now = time.monotonic()
        if not force and now - self._last_read_t < _SAMPLE_INTERVAL_S:
            return
        self._last_read_t = now
        self._last_voltage = self._read_voltage()

    @property
    def voltage(self):
        '''Last measured raw voltage in volts (None if unread/absent).'''
        return self._last_voltage
