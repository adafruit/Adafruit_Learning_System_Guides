# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Face detection for CircuitPython turbo: an OpenCV LBP cascade in Viper."""

import array
import os
import micropython
from micropython import const
from supervisor import ticks_ms

_TICKS_MASK = const(0x1FFFFFFF)  # ticks_ms() wraps at 2**29

# The cascade binary
_HEADER = const(16)  # words before the stages
_STAGE_WORDS = const(3)  # first weak classifier, count, threshold
_WEAK_WORDS = const(11)  # feature, 8-word mask, two leaves
_FEATURE_WORDS = const(4)  # x, y, block width, block height

# Slots of the scan kernel's argument array. Hits follow from _A_HITS.
_A_STRIDE = const(0)  # integral table row stride, in words
_A_X0 = const(1)  # window columns to try: X0, X0 + STEP, ... below X1
_A_X1 = const(2)
_A_Y0 = const(3)  # window rows likewise
_A_Y1 = const(4)
_A_STEP = const(5)
_A_CAPACITY = const(6)  # hits the array has room for
_A_WINDOWS = const(7)  # out: windows tested (added to)
_A_FEATURES = const(8)  # out: features evaluated (added to)
_A_HITS = const(16)

# Window rows per scan call
_ROWS_PER_CALL = const(4)
# pylint: disable=undefined-variable, too-many-locals, too-many-statements, too-many-boolean-expressions
# pylint: disable=too-many-branches, too-many-instance-attributes, too-many-arguments

def _elapsed(now, then):
    return (now - then) & _TICKS_MASK

def _zeros(count):
    """An int array of count zeros, without building a list first."""
    try:
        return array.array("i", [0]) * count
    except TypeError:
        return array.array("i", bytes(4 * count))

@micropython.viper
def _gray(frame: ptr8, gray: ptr8, count: int, totals: ptr32):
    """RGB565 to 8-bit brightness. Sum of the brightness and of
    its square / 256, for the frame's mean and contrast"""
    total = 0
    squares = 0
    i = 0
    j = 0
    while j < count:
        v = (frame[i] << 8) | frame[i + 1]
        r = v >> 11
        g = (v >> 5) & 63
        b = v & 31
        level = (
            77 * ((r << 3) | (r >> 2)) + 150 * ((g << 2) | (g >> 4)) + 29 * ((b << 3) | (b >> 2))
        ) >> 8
        gray[j] = level
        total += level
        squares += (level * level) >> 8
        i += 2
        j += 1
    totals[0] = total
    totals[1] = squares

@micropython.viper
def _resize(src: ptr8, dst: ptr8, args: ptr32):
    """Shrink an 8-bit image with bilinear filtering
    args: source width and height, destination width and height,
    then source pixels per destination pixel across and down
    in 16.16 fixed point"""
    src_w = args[0]
    src_h = args[1]
    dst_w = args[2]
    dst_h = args[3]
    step_x = args[4]
    step_y = args[5]
    out = 0
    y = 0
    while y < dst_h:
        sy = ((((y << 1) + 1) * step_y) - 65536) >> 1
        sy = max(sy, 0)
        y0 = sy >> 16
        fy = (sy >> 8) & 255
        if y0 >= src_h - 1:
            y0 = src_h - 1
            fy = 0
        row0 = y0 * src_w
        row1 = row0
        if fy:
            row1 = row0 + src_w
        x = 0
        while x < dst_w:
            sx = ((((x << 1) + 1) * step_x) - 65536) >> 1
            sx = max(sx, 0)
            x0 = sx >> 16
            fx = (sx >> 8) & 255
            if x0 >= src_w - 1:
                x0 = src_w - 1
                fx = 0
            x1 = x0
            if fx:
                x1 = x0 + 1
            top = src[row0 + x0] * (256 - fx) + src[row0 + x1] * fx
            bottom = src[row1 + x0] * (256 - fx) + src[row1 + x1] * fx
            dst[out + x] = (top * (256 - fy) + bottom * fy + 32768) >> 16
            x += 1
        out += dst_w
        y += 1

@micropython.viper
def _integral(gray: ptr8, table: ptr32, args: ptr32):
    """Summed-area table: table[y * stride + x] is the sum of the pixels
    above and left of (x, y); row 0 and column 0 are zero. args: width,
    height, stride."""
    width = args[0]
    height = args[1]
    stride = args[2]
    x = 0
    while x <= width:
        table[x] = 0
        x += 1
    src = 0
    above = 0
    here = stride
    y = 0
    while y < height:
        table[here] = 0
        row_sum = 0
        x = 0
        while x < width:
            row_sum += gray[src + x]
            table[here + x + 1] = table[above + x + 1] + row_sum
            x += 1
        src += width
        above = here
        here += stride
        y += 1

@micropython.viper
def _scan(table: ptr32, words: ptr32, offsets: ptr32, args: ptr32) -> int:
    """Run the cascade at each window position in args' range. Passing
    positions are stored from args[_A_HITS] as x, y pairs, up to the
    capacity; returns how many passed.

    offsets holds, for every feature, the 16 integral-table corners of its
    3x3 grid of blocks relative to the window's top-left corner."""
    stride = args[_A_STRIDE]
    x0 = args[_A_X0]
    x1 = args[_A_X1]
    y = args[_A_Y0]
    y1 = args[_A_Y1]
    step = args[_A_STEP]
    capacity = args[_A_CAPACITY]
    stage_end = _HEADER + _STAGE_WORDS * words[4]
    first_weak = stage_end
    windows = 0
    features = 0
    count = 0
    while y < y1:
        x = x0
        while x < x1:
            window = y * stride + x
            windows += 1
            passed = 1
            skip = 0
            stage = _HEADER
            while stage < stage_end:
                weak = first_weak + _WEAK_WORDS * words[stage]
                weak_end = weak + _WEAK_WORDS * words[stage + 1]
                total = 0
                while weak < weak_end:
                    o = words[weak] << 4
                    # The 4x4 corners around the feature's 3x3 blocks
                    s0 = table[window + offsets[o]]
                    s1 = table[window + offsets[o + 1]]
                    s2 = table[window + offsets[o + 2]]
                    s3 = table[window + offsets[o + 3]]
                    s4 = table[window + offsets[o + 4]]
                    s5 = table[window + offsets[o + 5]]
                    s6 = table[window + offsets[o + 6]]
                    s7 = table[window + offsets[o + 7]]
                    s8 = table[window + offsets[o + 8]]
                    s9 = table[window + offsets[o + 9]]
                    s10 = table[window + offsets[o + 10]]
                    s11 = table[window + offsets[o + 11]]
                    s12 = table[window + offsets[o + 12]]
                    s13 = table[window + offsets[o + 13]]
                    s14 = table[window + offsets[o + 14]]
                    s15 = table[window + offsets[o + 15]]
                    center = s5 - s6 - s9 + s10
                    # Each outer block against the center, clockwise from
                    # the top left: one bit each of an 8-bit code
                    code = 0
                    if s0 - s1 - s4 + s5 >= center:
                        code = 128
                    if s1 - s2 - s5 + s6 >= center:
                        code |= 64
                    if s2 - s3 - s6 + s7 >= center:
                        code |= 32
                    if s6 - s7 - s10 + s11 >= center:
                        code |= 16
                    if s10 - s11 - s14 + s15 >= center:
                        code |= 8
                    if s9 - s10 - s13 + s14 >= center:
                        code |= 4
                    if s8 - s9 - s12 + s13 >= center:
                        code |= 2
                    if s4 - s5 - s8 + s9 >= center:
                        code |= 1
                    # Bit `code` of the 256-bit mask picks the leaf
                    if (words[weak + 1 + (code >> 5)] >> (code & 31)) & 1:
                        total += words[weak + 9]
                    else:
                        total += words[weak + 10]
                    features += 1
                    weak += _WEAK_WORDS
                if total < words[stage + 2]:
                    passed = 0
                    if stage == _HEADER:
                        skip = 1
                    break
                stage += _STAGE_WORDS
            if passed:
                if count < capacity:
                    args[_A_HITS + (count << 1)] = x
                    args[_A_HITS + (count << 1) + 1] = y
                count += 1
            x += step
            if skip:
                x += step
        y += step
    args[_A_WINDOWS] += windows
    args[_A_FEATURES] += features
    return count

def _divide_round(total, n):
    """total / n to the nearest int"""
    q = total // n
    r = total - q * n
    if 2 * r > n or (2 * r == n and q & 1):
        q += 1
    return q

def group_rectangles(rects, min_neighbors):
    """OpenCV's groupRectangles with eps 0.2, in integers: cluster similar
    rectangles, average each cluster, keep those with more than
    min_neighbors members, and drop small ones inside a stronger big one.
    """
    n = len(rects)
    if min_neighbors <= 0:
        return [(r[0], r[1], r[2], r[3], 1) for r in rects]
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        ax, ay, aw, ah = rects[i]
        for j in range(i + 1, n):
            bx, by, bw, bh = rects[j]
            limit = min(aw, bw) + min(ah, bh)
            if (
                10 * abs(ax - bx) <= limit
                and 10 * abs(ay - by) <= limit
                and 10 * abs(ax + aw - bx - bw) <= limit
                and 10 * abs(ay + ah - by - bh) <= limit
            ):
                a = root(i)
                b = root(j)
                if a != b:
                    parent[b] = a
    sums = {}
    for i in range(n):
        x, y, w, h = rects[i]
        total = sums.get(root(i))
        if total is None:
            sums[root(i)] = [x, y, w, h, 1]
        else:
            total[0] += x
            total[1] += y
            total[2] += w
            total[3] += h
            total[4] += 1
    clusters = []
    for total in sums.values():
        k = total[4]
        if k > min_neighbors:
            clusters.append(
                (
                    _divide_round(total[0], k),
                    _divide_round(total[1], k),
                    _divide_round(total[2], k),
                    _divide_round(total[3], k),
                    k,
                )
            )
    faces = []
    for face in clusters:
        x1, y1, w1, h1, n1 = face
        inside = False
        for other in clusters:
            if other is face:
                continue
            x2, y2, w2, h2, n2 = other
            dx = (w2 * 2 + 5) // 10  # round(0.2 * w2): never a tie
            dy = (h2 * 2 + 5) // 10
            if (
                x1 >= x2 - dx
                and y1 >= y2 - dy
                and x1 + w1 <= x2 + w2 + dx
                and y1 + h1 <= y2 + h2 + dy
                and (n2 > max(3, n1) or n1 < 3)
            ):
                inside = True
                break
        if not inside:
            faces.append(face)
    faces.sort(key=lambda f: -f[2])
    return faces

def load_cascade(path):
    """Read a .lbp file straight into an int array"""
    size = os.stat(path)[6]
    if size % 4 or size < 4 * _HEADER:
        raise ValueError("%s is not a cascade from lbp_convert.py" % path)
    words = _zeros(size // 4)
    with open(path, "rb") as file:
        if file.readinto(words) != size:
            raise ValueError("%s: short read" % path)
    if words[0] != 0x4350424C:  # the bytes "LBPC", little-endian
        raise ValueError("%s is not a cascade from lbp_convert.py" % path)
    if words[1] != 1:
        raise ValueError("cascade format version %d isn't supported" % words[1])
    width, height = words[2], words[3]
    stages, weaks, features = words[4], words[5], words[6]
    first_weak = _HEADER + _STAGE_WORDS * stages
    first_feature = first_weak + _WEAK_WORDS * weaks
    if stages < 1 or weaks < 1 or features < 1:
        raise ValueError("empty cascade")
    if len(words) != first_feature + _FEATURE_WORDS * features:
        raise ValueError("cascade length doesn't match its header")
    for i in range(stages):
        first = words[_HEADER + 3 * i]
        count = words[_HEADER + 3 * i + 1]
        if count < 1 or first < 0 or first + count > weaks:
            raise ValueError("stage %d is out of range" % i)
    for i in range(weaks):
        feature = words[first_weak + _WEAK_WORDS * i]
        if not 0 <= feature < features:
            raise ValueError("weak classifier %d is out of range" % i)
    for i in range(features):
        x, y, w, h = words[first_feature + 4 * i : first_feature + 4 * i + 4]
        if w < 1 or h < 1 or x < 0 or y < 0 or x + 3 * w > width or y + 3 * h > height:
            raise ValueError("feature %d is outside the window" % i)
    return words

class FaceDetector:
    """Finds faces in width x height RGB565 frames.

    :param cascade_path: the .lbp file from lbp_convert.py
    :param scale_factor: size step between pyramid levels, as in OpenCV.
        1.2 is a good balance; 1.1 finds a few more faces and takes about
        twice as long.
    :param min_neighbors: number of hits a face needs
    :param min_size: smallest face to look for, in pixels
    :param max_size: largest face to look for (0 for the frame height)
    :param track: after finding faces, search only near them for the next
        few passes
    :param full_every: with track, cover the whole frame at least this
        often, counting passes
    :param track_misses: with track, how many tracking passes in a row may
        miss before going back to searching the whole frame
    :param merge_passes: group each pass's hits together with the previous
        pass's, so a face needs min_neighbors hits across two frames rather
        than in one
    :param keep_hits: once a face has been found, it stays found while at
        least this many of a pass's raw hits land on it.
    :param capacity: most hits kept per scan call
    """

    def __init__(
        self,
        cascade_path,
        width=160,
        height=120,
        *,
        scale_factor=1.2,
        min_neighbors=3,
        min_size=0,
        max_size=0,
        track=True,
        full_every=4,
        track_misses=2,
        merge_passes=True,
        keep_hits=1,
        capacity=128,
    ):
        if not 1.01 <= scale_factor <= 2.0:
            raise ValueError("scale_factor must be 1.01 to 2.0")
        if not (32 <= width <= 640 and 32 <= height <= 480):
            raise ValueError("frame size out of range")
        self.words = load_cascade(cascade_path)
        words = self.words
        self.window_w, self.window_h = words[2], words[3]
        if width < self.window_w or height < self.window_h:
            raise ValueError("frame is smaller than the cascade window")
        self.width = width
        self.height = height
        self.min_neighbors = min_neighbors
        self.track = track
        self.full_every = max(1, full_every)
        self.track_misses = max(0, track_misses)
        self.merge_passes = merge_passes
        self.keep_hits = keep_hits
        self.stride = stride = width + 1

        count = words[6]
        first_feature = _HEADER + _STAGE_WORDS * words[4] + _WEAK_WORDS * words[5]
        self.offsets = offsets = _zeros(16 * count)
        for i in range(count):
            fx, fy, fw, fh = words[first_feature + 4 * i : first_feature + 4 * i + 4]
            for r in range(4):
                for c in range(4):
                    offsets[16 * i + 4 * r + c] = (fy + r * fh) * stride + fx + c * fw

        self.gray = bytearray(width * height)
        self.level = bytearray(width * height)
        self.table = _zeros(stride * (height + 1))
        self.capacity = capacity
        self.args = _zeros(_A_HITS + 2 * capacity)
        self.args[_A_STRIDE] = stride
        self.args[_A_CAPACITY] = capacity
        self._resize_args = array.array("i", [width, height, 0, 0, 0, 0])
        self._integral_args = array.array("i", [0, 0, stride])
        self._totals = array.array("i", [0, 0])

        self.levels = []
        largest = max_size or min(width, height)
        step_q16 = int(scale_factor * 65536 + 0.5)
        factor = 65536  # 1.0
        while True:
            win_w = (self.window_w * factor + 32768) >> 16
            win_h = (self.window_h * factor + 32768) >> 16
            if win_w > min(largest, width) or win_h > min(largest, height):
                break
            level_w = (width * 65536 + factor // 2) // factor
            level_h = (height * 65536 + factor // 2) // factor
            if (win_w >= min_size and win_h >= min_size and
                level_w >= self.window_w and level_h >= self.window_h):
                self.levels.append(
                    (
                        factor,  # level pixels -> frame pixels, 16.16
                        level_w,
                        level_h,
                        (width * 65536 + level_w // 2) // level_w,  # resize steps
                        (height * 65536 + level_h // 2) // level_h,
                        1 if factor >= 131072 else 2,  # window spacing
                        win_w,
                        win_h,
                    )
                )
            factor = (factor * step_q16 + 32768) >> 16
        if not self.levels:
            raise ValueError("no pyramid levels for this size range")

        self.faces = []
        self._target = []  # the faces tracking passes look near
        self._misses = 0
        self._previous = []  # the last pass's hits, for merge_passes
        self.busy = False
        self.tracked = False  # whether the last pass was a tracking pass
        self._since_full = 0
        self._plan = []
        self._job = 0
        self._row = -1
        self._rects = []
        # Statistics of the last finished pass
        self.pass_ms = 0  # start() to the faces being ready
        self.work_ms = 0  # time spent inside work()
        self.windows = 0
        self.features = 0
        self.hits = 0  # windows that passed the cascade, before grouping
        self.kept = 0  # faces in the last result held on by keep_hits
        # Of the last frame given to start(): mean brightness, and contrast
        # as the standard deviation of brightness (both 0-255)
        self.brightness = 0
        self.contrast = 0
        self._started = 0
        self._work = 0

    def start(self, frame):
        """Begin a pass on frame: width x height RGB565, high byte first."""
        if len(frame) != 2 * self.width * self.height:
            raise ValueError("frame must be %d bytes" % (2 * self.width * self.height))
        self._started = ticks_ms()
        pixels = self.width * self.height
        _gray(frame, self.gray, pixels, self._totals)
        mean = self._totals[0] / pixels
        self.brightness = int(mean + 0.5)
        self.contrast = int(max(0.0, self._totals[1] * 256 / pixels - mean * mean) ** 0.5 + 0.5)
        self._plan = self._make_plan()
        self._job = 0
        self._row = -1
        self._rects = []
        self._work = 0
        self.args[_A_WINDOWS] = 0
        self.args[_A_FEATURES] = 0
        self.busy = True

    def cancel(self):
        """Abandon the pass in progress."""
        self.busy = False
        self._plan = []

    def reset(self):
        """Cancel and forget everything earlier passes found, so the next
        pass is a full one"""
        self.cancel()
        self.faces = []
        self._target = []
        self._misses = 0
        self._previous = []
        self._since_full = 0

    def work(self, budget_ms):
        """Do about budget_ms of the pass (at least one step). Returns True
        when the pass is done and ``faces`` holds its result."""
        if not self.busy:
            return False
        began = ticks_ms()
        while True:
            if self._job >= len(self._plan):
                self._finish(began)
                return True
            self._step()
            if _elapsed(ticks_ms(), began) >= budget_ms:
                self._work += _elapsed(ticks_ms(), began)
                return False

    def detect(self, frame):
        """A whole pass at once. It forgets earlier passes, so the result
        depends only on this frame."""
        self.reset()
        self.start(frame)
        while not self.work(1000):
            pass
        return self.faces

    def _make_plan(self):
        """The levels and window ranges for this pass"""
        full = not (self.track and self._target) or self._since_full + 1 >= self.full_every
        plan = []
        if full:
            self._since_full = 0
            self.tracked = False
            for i, level in enumerate(self.levels):
                plan.append((i, 0, level[1] - self.window_w + 1, 0, level[2] - self.window_h + 1))
            return plan
        self._since_full += 1
        self.tracked = True
        left = top = 1 << 20
        right = bottom = -1
        small = 1 << 20
        big = 0
        for x, y, w, h, _ in self._target: # pylint: disable=unused-variable
            margin = w // 2
            left = min(left, x - margin)
            top = min(top, y - margin)
            right = max(right, x + margin)
            bottom = max(bottom, y + margin)
            small = min(small, w)
            big = max(big, w)
        for i, (scale, level_w, level_h, _, _, step, win_w, _) in enumerate(self.levels):
            if win_w * 10 < small * 7 or win_w * 20 > big * 29:
                continue
            columns = level_w - self.window_w + 1
            rows = level_h - self.window_h + 1
            # Frame pixels to this level's positions, on the step grid
            x0 = max(0, left * 65536 // scale) // step * step
            y0 = max(0, top * 65536 // scale) // step * step
            x1 = min(columns, (right * 65536 + scale - 1) // scale + 1)
            y1 = min(rows, (bottom * 65536 + scale - 1) // scale + 1)
            if x0 < x1 and y0 < y1:
                plan.append((i, x0, x1, y0, y1))
        return plan

    def _step(self):
        index, x0, x1, y0, y1 = self._plan[self._job]
        scale, level_w, level_h, step_x, step_y, step, win_w, win_h = self.levels[index]
        args = self.args
        if self._row < 0:
            # Shrink the frame to this level and build its integral table
            if level_w == self.width and level_h == self.height:
                source = self.gray
            else:
                resize_args = self._resize_args
                resize_args[2] = level_w
                resize_args[3] = level_h
                resize_args[4] = step_x
                resize_args[5] = step_y
                _resize(self.gray, self.level, resize_args)
                source = self.level
            self._integral_args[0] = level_w
            self._integral_args[1] = level_h
            _integral(source, self.table, self._integral_args)
            self._row = y0
            return
        row_end = min(y1, self._row + _ROWS_PER_CALL * step)
        args[_A_X0] = x0
        args[_A_X1] = x1
        args[_A_Y0] = self._row
        args[_A_Y1] = row_end
        args[_A_STEP] = step
        found = min(_scan(self.table, self.words, self.offsets, args), self.capacity)
        width, height = self.width, self.height
        rects = self._rects
        for i in range(found):
            # Back to frame pixels, clipped to the frame like OpenCV
            x = (args[_A_HITS + 2 * i] * scale + 32768) >> 16
            y = (args[_A_HITS + 2 * i + 1] * scale + 32768) >> 16
            rects.append((x, y, min(win_w, width - x), min(win_h, height - y)))
        self._row = row_end
        if self._row >= y1:
            self._job += 1
            self._row = -1

    def _keep(self, rects):
        """Add back each followed face that lost min_neighbors support but
        still has keep_hits of this pass's hits on it"""
        faces = self.faces
        for tx, ty, tw, th, _ in self._target:
            found = False
            for x, y, w, h, _ in faces:
                cx, cy = x + w // 2, y + h // 2
                if tx <= cx < tx + tw and ty <= cy < ty + th:
                    found = True  # still found the normal way
                    break
            if found:
                continue
            sx = sy = sw = sh = n = 0
            for x, y, w, h in rects:
                cx, cy = x + w // 2, y + h // 2
                if (tx <= cx < tx + tw and ty <= cy < ty + th
                    and 5 * w >= 3 * tw and 5 * w <= 8 * tw):
                    sx += x
                    sy += y
                    sw += w
                    sh += h
                    n += 1
            if n and n >= self.keep_hits:
                faces.append((sx // n, sy // n, sw // n, sh // n, n))
                self.kept += 1
        if self.kept:
            faces.sort(key=lambda f: -f[2])

    def _finish(self, began):
        now = ticks_ms()
        self._work += _elapsed(now, began)
        rects = self._rects
        if self.merge_passes and self._previous:
            self.faces = group_rectangles(rects + self._previous, self.min_neighbors)
        else:
            self.faces = group_rectangles(rects, self.min_neighbors)
        self._previous = rects
        self.kept = 0
        if self.keep_hits and self._target:
            self._keep(rects)
        # Where the next tracking pass looks: the new faces, or after a miss
        # the old ones again, a few times, before a full search.
        if self.faces:
            self._target = self.faces
            self._misses = 0
        elif self.tracked and self._misses < self.track_misses:
            self._misses += 1
        else:
            self._target = []
            self._misses = 0
        self.busy = False
        self.pass_ms = _elapsed(now, self._started)
        self.work_ms = self._work
        self.windows = self.args[_A_WINDOWS]
        self.features = self.args[_A_FEATURES]
        self.hits = len(self._rects)
