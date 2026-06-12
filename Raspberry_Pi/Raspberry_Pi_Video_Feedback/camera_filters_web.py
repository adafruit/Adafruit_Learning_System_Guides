# SPDX-FileCopyrightText: 2026 Tim Cocks, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Live camera preview with stackable, intensity-adjustable filters,
served as a web page over the local network via Flask + MJPEG.

Designed for Raspberry Pi 4/5 with a USB camera, but works on any system with
a webcam.

Setup:
    sudo apt update
    sudo apt install python3-flask python3-opencv python3-numpy
    # Or via pip in a venv:
    # pip install flask opencv-python numpy

Run:
    python3 camera_filters_web.py

Then open http://<pi-ip>:5000 in any browser on the local network.
(On the Pi itself, http://localhost:5000 also works.)

Controls:
    - Toggle each filter on/off with its checkbox.
    - Adjust the intensity number input (0-100%) for each filter.
    - Filters are applied top-to-bottom in the order shown.
"""
# pylint: disable=too-many-locals

import os
import time
import threading
from typing import List, Optional, TypedDict

import cv2
import numpy as np
import rainbowio
from flask import (
    Flask,
    Response,
    request,
    jsonify,
    render_template,
    send_from_directory,
    abort,
)


# config argument unused by some filters but gets passed dynamically
# to all filter functions so the argument needs to exist.
# pylint: disable=unused-argument

# ----------------------
# Filter implementations
# ----------------------
def filter_grayscale(frame, config=None):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


_RAINBOW_CACHE = {"key": None, "offsets": None, "index": None}

# Rainbow orientations: which way the color bands run.
_RB_ROW = 0  # horizontal bands, one color per row
_RB_COLUMN = 1  # vertical bands, one color per column
_RB_DIAG_DOWN = 2  # bands run top-left -> bottom-right (constant x - y)
_RB_DIAG_UP = 3  # bands run bottom-left -> top-right (constant x + y)


def filter_rainbow(frame, config=None):
    """Overlay a rainbow pattern by color-shifting each row, column, or
    diagonal line.

    Like the Color Gel filter, but instead of one offset for the whole
    frame, every line (row, column, or 45-degree diagonal) gets its own
    color offset taken from rainbowio.colorwheel(), indexed by that line.
    The result is a rainbow gradient laid over the image.

    Config:
        orientation: which way the color bands run.
            0 = per row    (horizontal bands)
            1 = per column (vertical bands)
            2 = diagonal down-right (constant x - y)
            3 = diagonal up-right   (constant x + y)
            (the legacy key "vertical" is still accepted as a fallback.)
        scale:    0..1 multiplier on the offset strength (default 1.0).
        spread:   number of lines per color band (default 1). With spread
                  2, each colorwheel color covers two lines, and so on,
                  widening the bands.
        offset:   added to the colorwheel index, shifting where in the
                  rainbow the pattern starts (default 0).

    The colorwheel input wraps every 256 colors, so the rainbow repeats
    across the frame.
    """
    if config is None:
        config = {}
    # "orientation" supersedes the old 0/1 "vertical" flag, which still
    # works for existing configs.
    orientation = int(config.get("orientation", config.get("vertical", 0)))
    scale = float(config.get("scale", 1.0))
    spread = max(1, int(config.get("spread", 1)))
    offset = int(config.get("offset", 0))
    h, w = frame.shape[:2]

    # How many distinct lines there are depends on the orientation. The
    # diagonals span every (x +/- y) value, so there are w + h - 1 of them.
    if orientation == _RB_COLUMN:
        n = w
    elif orientation in (_RB_DIAG_DOWN, _RB_DIAG_UP):
        n = w + h - 1
    else:
        n = h

    # Building one offset per line (and, for diagonals, the per-pixel line
    # index map) is the slow part, so cache it and only rebuild when the
    # frame size, orientation, strength, spread, or offset changes.
    key = (h, w, orientation, scale, spread, offset)
    if _RAINBOW_CACHE["key"] != key:
        offsets = np.empty((n, 3), dtype=np.int16)
        for i in range(n):
            color = rainbowio.colorwheel((i // spread + offset) % 256)
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            # OpenCV channel order is BGR.
            offsets[i] = (round(b * scale), round(g * scale), round(r * scale))

        # For diagonals, precompute the line index of every pixel so we can
        # gather offsets with a single fancy-index per frame.
        _line_index = None
        cols = np.arange(w)
        rows = np.arange(h)
        if orientation == _RB_DIAG_DOWN:
            # constant x - y; shift by (h - 1) so indices start at 0.
            _line_index = (cols[np.newaxis, :] - rows[:, np.newaxis]) + (h - 1)
        elif orientation == _RB_DIAG_UP:
            # constant x + y.
            _line_index = cols[np.newaxis, :] + rows[:, np.newaxis]

        _RAINBOW_CACHE["key"] = key
        _RAINBOW_CACHE["offsets"] = offsets
        _RAINBOW_CACHE["index"] = _line_index
    offsets = _RAINBOW_CACHE["offsets"]
    _line_index = _RAINBOW_CACHE["index"]

    shifted = frame.astype(np.int16)
    if orientation == _RB_COLUMN:
        shifted += offsets[np.newaxis, :, :]  # one offset per column
    elif _line_index is not None:
        shifted += offsets[_line_index]  # one offset per diagonal line
    else:
        shifted += offsets[:, np.newaxis, :]  # one offset per row
    return np.clip(shifted, 0, 255).astype(np.uint8)


def filter_invert(frame, config=None):
    return cv2.bitwise_not(frame)


def filter_blur(frame, config=None):
    return cv2.GaussianBlur(frame, (15, 15), 0)


def filter_edges(frame, config=None):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def filter_cartoon(frame, config=None):
    color = cv2.bilateralFilter(frame, 9, 75, 75)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2
    )
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.bitwise_and(color, edges)


def filter_colorgel(frame, config=None):
    """Dynamic per-channel color shift.

    Config:
        red:   amount to add to the red channel   (-255..255).
        green: amount to add to the green channel (-255..255).
        blue:  amount to add to the blue channel  (-255..255).

    Negative values subtract from the channel. Channels are clipped to
    the valid 0-255 range.
    """
    if config is None:
        config = {}
    r_off = int(config.get("red", -20))
    g_off = int(config.get("green", 0))
    b_off = int(config.get("blue", 30))
    shifted = frame.astype(np.int16)
    shifted[..., 0] += b_off  # OpenCV channel order is BGR.
    shifted[..., 1] += g_off
    shifted[..., 2] += r_off
    return np.clip(shifted, 0, 255).astype(np.uint8)


def filter_colortransform(frame, config=None):
    """Apply a user-supplied 3x3 color matrix, like the sepia filter.

    Config:
        matrix: a 3x3 list of floats applied to each pixel via
                cv2.transform. Defaults to the classic sepia matrix.
    """
    if config is None:
        config = {}
    matrix = config.get("matrix") or _COLORTRANSFORM_DEFAULTS["matrix"]
    kernel = np.array(matrix, dtype=np.float64)
    transformed = cv2.transform(frame, kernel)
    return np.clip(transformed, 0, 255).astype(np.uint8)


_ROWSHIFT_SPLITS_TYPE = TypedDict("_ROWSHIFT_SPLITS_TYPE", {
    "key": Optional[tuple],
    "splits": Optional[List[int]]
})
_ROWSHIFT_SPLITS: _ROWSHIFT_SPLITS_TYPE = {"key": None, "splits": None}


def filter_rowshift(frame, config=None):
    """Split the frame into N horizontal rows; within each row, swap two
    parts at a fixed random split point.

    Config:
        num_rows: number of horizontal rows to split into (default 4).
        random_seed:   any changing token; bumping it re-rolls the split points.
    """
    if config is None:
        config = {}
    h, w = frame.shape[:2]
    num_rows = max(1, int(config.get("num_rows", 8)))
    random_seed = config.get("random_seed", 0)
    key = (w, num_rows, random_seed)
    if _ROWSHIFT_SPLITS["key"] != key:
        rng = np.random.default_rng()
        _ROWSHIFT_SPLITS["splits"] = [int(rng.integers(1, w)) for _ in range(num_rows)]
        _ROWSHIFT_SPLITS["key"] = key
    splits = _ROWSHIFT_SPLITS["splits"]

    out = frame.copy()
    row_edges = np.linspace(0, h, num_rows + 1, dtype=int)
    for i in range(num_rows):
        y1, y2 = row_edges[i], row_edges[i + 1]
        x = splits[i]  # pylint: disable=unsubscriptable-object
        row = frame[y1:y2]
        out[y1:y2] = np.concatenate((row[:, x:], row[:, :x]), axis=1)
    return out


def filter_glitch(frame, config=None):
    """Datamosh / RGB-shift / slice-displacement / noise glitch effect."""
    if config is None:
        config = {}
    h, w = frame.shape[:2]
    out = frame.copy()

    default_shift = max(4, w // 80)

    scale_x = config.get("scale_x", 1)
    shear_x = config.get("shear_x", 0)
    translate_x = config.get("translate_x", default_shift)
    scale_y = config.get("scale_y", 1)
    shear_y = config.get("shear_y", 0)
    translate_y = config.get("translate_y", 0)

    b, g, r = cv2.split(out)

    M_r = np.float32([[scale_x, shear_x, translate_x], [shear_y, scale_y, translate_y]])
    M_b = np.float32(
        [[scale_x, -shear_x, -translate_x], [-shear_y, scale_y, -translate_y]]
    )
    r = cv2.warpAffine(r, M_r, (w, h), borderMode=cv2.BORDER_REPLICATE)
    b = cv2.warpAffine(b, M_b, (w, h), borderMode=cv2.BORDER_REPLICATE)
    out = cv2.merge([b, g, r])

    rng = np.random.default_rng()
    # num_slices = 6
    # for _ in range(num_slices):
    #     y1 = rng.integers(0, h)
    #     y2 = min(h, y1 + rng.integers(2, max(3, h // 20)))
    #     dx = int(rng.integers(-w // 12, w // 12))
    #     if dx == 0:
    #         continue
    #     band = out[y1:y2].copy()
    #     out[y1:y2] = np.roll(band, dx, axis=1)

    levels = 5
    step = 256 // levels
    out = (out // step) * step + step // 2

    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[..., 1] = np.clip(hsv[..., 1] + 80, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    noise = rng.integers(-40, 40, size=out.shape, dtype=np.int16)
    out = np.clip(out.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return out


# Registry of (name, function). Order here = order applied in the chain.
FILTERS = [
    ("Edges", filter_edges),
    ("Grayscale", filter_grayscale),
    ("Rainbow", filter_rainbow),
    ("Color Gel", filter_colorgel),
    ("Color Matrix", filter_colortransform),
    ("Invert", filter_invert),
    ("Blur", filter_blur),
    ("Cartoon", filter_cartoon),
    ("Glitch", filter_glitch),
    ("Rowshift", filter_rowshift),
]


# ---------------------------------------------------------------------------
# Filter chain state  (shared between the request handlers and frame loop)
# ---------------------------------------------------------------------------
class FilterState:
    """Plain Python replacement for the Qt FilterRow.

    Holds enabled flag + intensity (0.0-1.0) for one filter, and knows how
    to apply itself to a frame. A lock guards reads/writes since the frame
    loop runs in one thread and HTTP handlers run in others.
    """

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn
        self.enabled = False
        self.intensity = 1.0
        self.extra_config = {}

    def is_active(self):
        return self.enabled and self.intensity > 0

    def apply(self, frame):
        if not self.is_active():
            return frame
        filtered = self.fn(frame, self.extra_config)
        amt = self.intensity
        if amt >= 1.0:
            return filtered
        return cv2.addWeighted(frame, 1.0 - amt, filtered, amt, 0)


STATE_LOCK = threading.Lock()
FILTER_STATES = [FilterState(name, fn) for name, fn in FILTERS]

_GLITCH_DEFAULTS = {
    "scale_x": 1.0,
    "shear_x": 0.0,
    "translate_x": 8.0,
    "scale_y": 1.0,
    "shear_y": 0.0,
    "translate_y": 0.0,
}
_ROWSHIFT_DEFAULTS = {"num_rows": 4.0, "random_seed": 0.0}
_COLORGEL_DEFAULTS = {"red": -20.0, "green": 0.0, "blue": 30.0}
_RAINBOW_DEFAULTS = {"orientation": 0.0, "scale": 0.4, "spread": 2, "offset": 0.0}
_COLORTRANSFORM_DEFAULTS = {
    "matrix": [[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]]
}


def _default_config_for(name):
    """Return a fresh copy of the default extra_config for a filter, or {}."""
    if name == "Glitch":
        return dict(_GLITCH_DEFAULTS)
    if name == "Rowshift":
        return dict(_ROWSHIFT_DEFAULTS)
    if name == "Color Gel":
        return dict(_COLORGEL_DEFAULTS)
    if name == "Rainbow":
        return dict(_RAINBOW_DEFAULTS)
    if name == "Color Matrix":
        return {"matrix": [row[:] for row in _COLORTRANSFORM_DEFAULTS["matrix"]]}
    return {}


for _s in FILTER_STATES:
    if _s.name == "Rainbow":
        _s.intensity = 0.7
    _s.extra_config = _default_config_for(_s.name)


# ---------------------------------------------------------------------------
# Camera + frame generator
# ---------------------------------------------------------------------------
class Camera:
    """Wraps cv2.VideoCapture and serializes access with a lock.

    cv2.VideoCapture isn't thread-safe, and the frame generator may be
    called from multiple Flask worker threads if more than one viewer
    connects. We grab one frame at a time under a lock.
    """

    def __init__(self, camera_index=0, width=640, height=480):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open camera at index {camera_index}. "
                "Check that it's plugged in and not in use."
            )
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self.cap.read()

    def release(self):
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()


CAMERA = Camera(camera_index=0, width=1280, height=960)

# Where recordings and photos are written, relative to this script.
RECORD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")


class Processor(threading.Thread):
    """Single background thread that owns the camera read + filter chain.

    It reads one frame at a time, applies the active filter chain,
    stashes the result as the latest JPEG (for any number of MJPEG viewers)
    and, while recording, writes the same filtered frame to a VideoWriter.

    Doing the work in one place means recording is independent of whether
    (or how many) browsers are connected, and every viewer shares one
    consistent frame instead of each re-running the filters.
    """

    def __init__(self, camera):
        super().__init__(daemon=True)
        self.camera = camera
        self.running = True

        # Latest encoded frame, published to streaming clients.
        self.frame_cond = threading.Condition()
        self.latest_jpeg = None
        self.frame_id = 0

        # Size of the most recent frame, needed when opening a VideoWriter.
        self.frame_size = None

        # Smoothed measured frame rate (EMA), used as the recording FPS so
        # playback timing roughly matches real time.
        self.fps = 20.0
        self._last_t = None

        # Recording state, guarded by its own lock.
        self.rec_lock = threading.Lock()
        self.writer = None
        self.rec_path = None
        self.rec_start = None
        self.rec_frames = 0

    def run(self):
        while self.running:
            ok, frame = self.camera.read()
            if not ok:
                time.sleep(0.01)
                continue

            now = time.time()
            if self._last_t is not None:
                dt = now - self._last_t
                if dt > 0:
                    self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)
            self._last_t = now

            # Snapshot filter state under the lock so it can't change mid-chain.
            with STATE_LOCK:
                active = [(s.fn, s) for s in FILTER_STATES if s.is_active()]

            for fn, state in active:
                filtered = fn(frame, state.extra_config)
                intensity = state.intensity
                if intensity >= 1.0:
                    frame = filtered
                else:
                    frame = cv2.addWeighted(
                        frame, 1.0 - intensity, filtered, intensity, 0
                    )

            self.frame_size = (frame.shape[1], frame.shape[0])

            # Write the filtered frame to disk if we're recording.
            with self.rec_lock:
                if self.writer is not None:
                    self.writer.write(frame)
                    self.rec_frames += 1

            ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue

            with self.frame_cond:
                self.latest_jpeg = jpeg.tobytes()
                self.frame_id += 1
                self.frame_cond.notify_all()

    # -- recording control --------------------------------------------------
    def start_recording(self):
        """Open a VideoWriter. Returns the file path, or None on failure /
        if already recording."""
        with self.rec_lock:
            if self.writer is not None:
                return None
            size = self.frame_size or (640, 480)
            fps = max(5.0, min(30.0, self.fps))
            os.makedirs(RECORD_DIR, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            # Prefer H.264 ('avc1') in MP4: it's the only combination HTML5
            # <video> plays reliably across browsers. Fall back to MPEG-4
            # Part 2 ('mp4v') then MJPG/AVI for builds without an H.264
            # encoder, those won't play in a browser but at least record.
            for ext, fourcc in (("mp4", "avc1"), ("mp4", "mp4v"), ("avi", "MJPG")):
                path = os.path.join(RECORD_DIR, f"rec_{ts}.{ext}")
                writer = cv2.VideoWriter(
                    path, cv2.VideoWriter_fourcc(*fourcc), fps, size
                )
                if writer.isOpened():
                    self.writer = writer
                    self.rec_path = path
                    self.rec_start = time.time()
                    self.rec_frames = 0
                    return path
                writer.release()
            return None

    def stop_recording(self):
        """Finalize the current recording. Returns info dict, or None if not
        recording."""
        with self.rec_lock:
            if self.writer is None:
                return None
            self.writer.release()
            info = {
                "path": self.rec_path,
                "frames": self.rec_frames,
                "duration": time.time() - self.rec_start,
            }
            self.writer = None
            self.rec_path = None
            self.rec_start = None
            self.rec_frames = 0
            return info

    # -- still photos -------------------------------------------------------
    def save_snapshot(self):
        """Write the latest filtered frame to a JPEG. Returns the path, or
        None if no frame is available yet."""
        with self.frame_cond:
            jpeg = self.latest_jpeg
        if jpeg is None:
            return None
        os.makedirs(PHOTO_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(PHOTO_DIR, f"photo_{ts}.jpg")
        # Avoid clobbering if several shots land in the same second.
        n = 1
        while os.path.exists(path):
            path = os.path.join(PHOTO_DIR, f"photo_{ts}_{n}.jpg")
            n += 1
        with open(path, "wb") as f:
            f.write(jpeg)
        return path

    def record_status(self):
        with self.rec_lock:
            if self.writer is None:
                return {"recording": False}
            return {
                "recording": True,
                "elapsed": time.time() - self.rec_start,
                "file": os.path.basename(self.rec_path),
            }


PROCESSOR = Processor(CAMERA)


def generate_frames():
    """MJPEG generator: yields the processor's latest JPEG frame, blocking
    until a new one is available so we don't resend duplicates."""
    boundary = b"--frame"
    last_id = -1
    while True:
        with PROCESSOR.frame_cond:
            PROCESSOR.frame_cond.wait_for(
                lambda: PROCESSOR.frame_id != last_id, timeout=1.0
            )
            jpeg = PROCESSOR.latest_jpeg
            last_id = PROCESSOR.frame_id
        if jpeg is None:
            continue

        yield (
                boundary + b"\r\n"
                           b"Content-Type: image/jpeg\r\n"
                           b"Content-Length: " + str(len(jpeg)).encode() +
                           b"\r\n\r\n" + jpeg + b"\r\n"
        )


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def index():
    with STATE_LOCK:
        filter_state_snapshot = [
            {
                "name": s.name,
                "enabled": s.enabled,
                "intensity": s.intensity,
                "extra_config": dict(s.extra_config),
            }
            for s in FILTER_STATES
        ]
    return render_template("index.html", filters=filter_state_snapshot)


@app.route("/stream")
def stream():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/filter/<int:filter_index>", methods=["POST"])
def update_filter(filter_index):
    if not 0 <= filter_index < len(FILTER_STATES):
        return jsonify(error="bad index"), 400
    data = request.get_json(silent=True) or {}
    with STATE_LOCK:
        s = FILTER_STATES[filter_index]
        if "enabled" in data:
            s.enabled = bool(data["enabled"])
        if "intensity" in data:
            try:
                s.intensity = max(0.0, min(1.0, float(data["intensity"])))
            except (TypeError, ValueError):
                return jsonify(error="bad intensity"), 400
        if "config" in data and isinstance(data["config"], dict):
            for k, v in data["config"].items():
                if k == "matrix":
                    try:
                        mat = [[float(x) for x in row] for row in v]
                    except (TypeError, ValueError):
                        return jsonify(error="bad matrix value"), 400
                    if len(mat) != 3 or any(len(row) != 3 for row in mat):
                        return jsonify(error="matrix must be 3x3"), 400
                    s.extra_config[k] = mat
                    continue
                try:
                    s.extra_config[k] = float(v)
                except (TypeError, ValueError):
                    return jsonify(error=f"bad config value for {k}"), 400
    return jsonify(ok=True)


@app.route("/reset", methods=["POST"])
def reset():
    with STATE_LOCK:
        for s in FILTER_STATES:
            s.enabled = False
            s.intensity = 1.0
            s.extra_config = _default_config_for(s.name)
    return jsonify(ok=True)


@app.route("/record/start", methods=["POST"])
def record_start():
    path = PROCESSOR.start_recording()
    if path is None:
        status = PROCESSOR.record_status()
        if status["recording"]:
            # Already recording; report the in-progress file.
            return jsonify(ok=True, **status)
        return jsonify(error="could not start recording (VideoWriter failed)"), 500
    return jsonify(ok=True, recording=True, file=os.path.basename(path))


@app.route("/record/stop", methods=["POST"])
def record_stop():
    info = PROCESSOR.stop_recording()
    if info is None:
        return jsonify(ok=True, recording=False)
    return jsonify(
        ok=True,
        recording=False,
        file=os.path.basename(info["path"]),
        frames=info["frames"],
        duration=round(info["duration"], 1),
    )


@app.route("/record/status")
def record_status():
    return jsonify(PROCESSOR.record_status())


@app.route("/snapshot", methods=["POST"])
def snapshot():
    path = PROCESSOR.save_snapshot()
    if path is None:
        return jsonify(error="no frame available yet"), 503
    return jsonify(ok=True, file=os.path.basename(path))


# ---------------------------------------------------------------------------
# Gallery: browse / view / download saved photos and recordings
# ---------------------------------------------------------------------------
PHOTO_EXTS = (".jpg", ".jpeg", ".png")
VIDEO_EXTS = (".mp4", ".avi", ".mov", ".mkv")


def _list_media(directory, exts):
    """Return media filenames in `directory` matching `exts`, newest first.

    Sorted by modification time descending so the most recent capture leads
    the gallery. Missing directory yields an empty list.
    """
    try:
        names = [n for n in os.listdir(directory) if n.lower().endswith(exts)]
    except FileNotFoundError:
        return []
    names.sort(key=lambda n: os.path.getmtime(os.path.join(directory, n)), reverse=True)
    return names


@app.route("/photos")
def photos():
    files = _list_media(PHOTO_DIR, PHOTO_EXTS)
    return render_template("photos.html", files=files)


@app.route("/videos")
def videos():
    files = _list_media(RECORD_DIR, VIDEO_EXTS)
    return render_template("videos.html", files=files)


@app.route("/media/photos/<path:filename>")
def media_photo(filename):
    if not filename.lower().endswith(PHOTO_EXTS):
        abort(404)
    return send_from_directory(
        PHOTO_DIR, filename, as_attachment="download" in request.args
    )


@app.route("/media/videos/<path:filename>")
def media_video(filename):
    if not filename.lower().endswith(VIDEO_EXTS):
        abort(404)
    return send_from_directory(
        RECORD_DIR, filename, as_attachment="download" in request.args
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        PROCESSOR.start()
        # threaded=True lets the MJPEG stream and control endpoints run
        # concurrently. host='0.0.0.0' makes it reachable on the LAN.
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
    finally:
        PROCESSOR.running = False
        PROCESSOR.stop_recording()
        CAMERA.release()
