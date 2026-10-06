# SPDX-FileCopyrightText: 2026 phillip torrone for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Controls eyeball movement for gaze"""
import math

# pylint: disable=too-many-locals, too-many-branches, too-many-statements
class MotionGaze:
    WARMUP = 12
    HOLD = 3.0
    RETURN = 1.6

    def __init__(self, mirror_x=True, blink=True, sensitivity=1):
        if not isinstance(mirror_x, bool) or not isinstance(blink, bool):
            raise ValueError('mirror_x and blink must be booleans')
        self.mirror_x = mirror_x
        if (isinstance(sensitivity, bool)
            or not isinstance(sensitivity, int)
            or not 0 <= sensitivity <= 2):
            raise ValueError('sensitivity must be 0..2')
        self.sensitivity = sensitivity
        self.enable_blink = blink
        self.frames = 0
        self.last_time = None
        self.started = None
        self.last_motion = None
        self.target_x = self.target_y = 0
        self.x = self.y = 0.0
        self.return_origin = None
        self.signal = 'warmup'
        self.strength = self.background = 0

    def _location(self, raw):
        # At most192 values. Sorting a small fixed grid establishes a robust
        # background, not a learned illumination or semantic model.
        ordered = sorted(raw[16:208])
        median = (ordered[95] + ordered[96]) // 2
        peak = ordered[-1]
        active = sum(value >= 12 for value in ordered)
        self.background = median
        if median >= 16 and active >= 144 and peak - median <= max(16, median):
            self.strength = 0
            self.signal = 'global-light'
            return None
        floor, peak_min, total_min = ((6,18,108),(4,12,72),(2,8,48))[self.sensitivity]
        weights = [max(0, value - median - floor) for value in raw[16:208]]
        if max(weights) < peak_min:
            self.strength = 0
            self.signal = 'quiet'
            return None
        # Rolling column totals find the strongest3x3 neighborhood in O(192).
        columns = [weights[x] + weights[16 + x] for x in range(16)]
        best = best_x = best_y = 0
        best_distance = None
        old_x = -self.target_x if self.mirror_x else self.target_x
        for y in range(12):
            total = columns[0] + columns[1]
            for x in range(16):
                if x:
                    if x + 1 < 16:
                        total += columns[x + 1]
                    if x - 2 >= 0:
                        total -= columns[x - 2]
                # Deterministic ties prefer proximity to the last target.
                distance = abs(x * 2000 // 15 -
                               1000 - old_x) + abs(y * 2000 // 11 -
                                                   1000 - self.target_y)
                if total > best or (total == best and (best_distance is None
                                                       or distance < best_distance)):
                    best, best_x, best_y, best_distance = total, x, y, distance
            if y < 11:
                for x in range(16):
                    if y >= 1:
                        columns[x] -= weights[(y - 1) * 16 + x]
                    if y + 2 < 12:
                        columns[x] += weights[(y + 2) * 16 + x]
        self.strength = best
        if best < total_min:
            self.signal = 'quiet'
            return None
        sx = sy = total = 0
        for y in range(max(0, best_y - 1), min(12, best_y + 2)):
            for x in range(max(0, best_x - 1), min(16, best_x + 2)):
                weight = weights[y * 16 + x]
                sx += x * weight
                sy += y * weight
                total += weight
        x = sx * 2000 // (total * 15) - 1000
        y = sy * 2000 // (total * 11) - 1000
        self.signal = 'motion'
        return (-x if self.mirror_x else x), y

    def update(self, stats, now, new_frame=True):
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError('finite monotonic time required')
        if self.last_time is not None and now < self.last_time:
            raise ValueError('time moved backwards')
        if not isinstance(new_frame, bool):
            raise ValueError('new_frame must be boolean')
        raw = None
        if new_frame:
            view = memoryview(stats)
            raw = view.cast('B')
            if len(view) != 208 or len(raw) != 208:
                raise ValueError('exactly208 byte stats required')
        if self.started is None:
            self.started = now
        dt = 0 if self.last_time is None else min(.25, now - self.last_time)
        self.last_time = now
        if new_frame:
            self.frames += 1
            if self.frames <= self.WARMUP:
                self.signal = 'warmup'
            else:
                location = self._location(raw)
                if location is not None:
                    x, y = location
                    # ~one grid cell of spatial hysteresis avoids tiny jitters.
                    if abs(x - self.target_x) >= 100:
                        self.target_x = x
                    if abs(y - self.target_y) >= 100:
                        self.target_y = y
                    self.last_motion = now
                    self.return_origin = None
        age = None if self.last_motion is None else now - self.last_motion
        if self.frames <= self.WARMUP:
            status = 'warmup'
        elif age is None:
            status = self.signal
            self.x = self.y = 0.0
        elif age <= self.HOLD:
            alpha = 1 - math.exp(-dt / .18)
            self.x += (self.target_x - self.x) * alpha
            self.y += (self.target_y - self.y) * alpha
            status = 'tracking' if new_frame and self.signal == 'motion' else 'holding'
        elif age < self.HOLD + self.RETURN:
            if self.return_origin is None:
                self.return_origin = (self.x, self.y)
            t = min(1, (age - self.HOLD) / self.RETURN)
            ease = t * t * (3 - 2 * t)
            self.x = self.return_origin[0] * (1 - ease)
            self.y = self.return_origin[1] * (1 - ease)
            status = 'returning'
        else:
            self.x = self.y = 0.0
            self.target_x = self.target_y = 0
            self.return_origin = None
            status = 'centered'
        blink = self.enable_blink and (now - self.started) % 5.2 >= 5.06
        return {'x': max(-1000, min(1000, int(round(self.x)))),
                'y': max(-1000, min(1000, int(round(self.y)))),
                'status': status, 'signal': self.signal, 'strength': self.strength,
                'background': self.background,
                'warmup_remaining': max(0,self.WARMUP - self.frames),
                'motion_age_s': age, 'blink': blink, 'mirror_x': self.mirror_x}
