# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Face detector on Fruit Jam with a Logitech C270

Uses the Frontal Face cascade model from OpenCV.

The feed from the C270 is displayed through DVI. When a face is detected,
a green box is drawn around the face.
"""

import gc

import board
import displayio
import picodvi
import picogame
from supervisor import ticks_ms

from face_lbp import FaceDetector
from face_camera import CameraSession

# --- Camera ---
CAMERA_MODE = (320, 240)
DECODE_SCALE = 1
CAMERA_WAIT_MS = 3  # how long each check waits for a frame
MIRROR = True

# --- Face detection ---
CASCADE_PATH = "/frontalface.lbp"
SCALE_FACTOR = 1.3  # size step between searches; 1.1 is finer and slower
MIN_NEIGHBORS = 1  # raise for fewer false faces, lower to find more
# Smallest face to look for, in screen pixels.
# 48 is the smallest a 160x120 picture can show; with DECODE_SCALE 0, a
# smaller value finds faces farther away but takes much longer.
MIN_FACE_ON_SCREEN = 48
DETECT_SLICE_MS = 10  # detection work per loop pass, between video frames
TRACK = True  # after finding a face, search near it first
TRACK_MISSES = 5  # tracking passes that may miss before a full search again
# Combine each pass's hits with the previous pass's, so a face needs
# MIN_NEIGHBORS + 1 hits across two frames rather than in one frame.
MERGE_PASSES = True
PRINT_FACES = True

# Debugging: don't take camera frames (or redraw) while a search is running.
PAUSE_CAMERA_DURING_SEARCH = False

# --- Screen ---
SCREEN_W, SCREEN_H = 320, 240
WAIT_FOR_VBLANK = False  # True avoids tearing, but can wait up to a frame
BOX_COLOR = picogame.rgb565(0, 255, 0)
LINE = 2  # box line thickness in screen pixels
MAX_FACES = 3
HOLD_MS = 1200  # keep a box this long after its face was last found
SMOOTHING = 0.7  # 0 jumps straight to each new position, near 1 glides

REPORT_SECONDS = 4  # 0 for no timing reports

_TICKS_MASK = 0x1FFFFFFF  # ticks_ms() wraps at 2**29
_CLEAR = picogame.rgb565(255, 0, 255)  # the overlay's transparent color

frame_w = CAMERA_MODE[0] >> DECODE_SCALE
frame_h = CAMERA_MODE[1] >> DECODE_SCALE
zoom = SCREEN_W // frame_w  # screen pixels per camera pixel


def elapsed(the_now, then):
    return (the_now - then) & _TICKS_MASK


def reached(the_now, deadline):
    """Whether ticks_ms() time now is at or past deadline, across a wrap."""
    return elapsed(the_now, deadline) < (_TICKS_MASK >> 1)

gc.collect()

# --- The detector, while memory is unfragmented ---
detector = FaceDetector(
    CASCADE_PATH,
    frame_w,
    frame_h,
    scale_factor=SCALE_FACTOR,
    min_neighbors=MIN_NEIGHBORS,
    min_size=max(0, MIN_FACE_ON_SCREEN // zoom),
    track=TRACK,
    track_misses=TRACK_MISSES,
    merge_passes=MERGE_PASSES,
)
verifier = live_copy = None
verified = mismatched = 0
print(
    "detecting in %dx%d frames: %d pyramid levels, faces from %d to %d camera pixels"
    % (frame_w, frame_h, len(detector.levels), detector.levels[0][6], detector.levels[-1][6])
)

# --- Display ---
displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    SCREEN_W,
    SCREEN_H,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
target = picogame.Framebuffer(framebuffer, SCREEN_W, SCREEN_H, native_rgb565=True)
wait_for_vblank = getattr(framebuffer, "wait_for_vblank", None) if WAIT_FOR_VBLANK else None
overlay = picogame.Canvas(SCREEN_W, SCREEN_H, transparent=_CLEAR)
overlay.clear(_CLEAR)
video = None  # the camera sprite, once a camera is connected
layers = [overlay]

def render():
    if wait_for_vblank is not None:
        wait_for_vblank()
    picogame.render(target, layers, None, 0, 0, SCREEN_W, SCREEN_H)


class Box:
    """One face outline"""

    def __init__(self):
        self.visible = False
        self.x = self.y = self.w = self.h = 0.0
        self.seen = 0

    def show(self, x, y, w, h, the_now):
        if self.visible:
            keep = SMOOTHING
            self.x += (x - self.x) * (1 - keep)
            self.y += (y - self.y) * (1 - keep)
            self.w += (w - self.w) * (1 - keep)
            self.h += (h - self.h) * (1 - keep)
        else:
            self.x, self.y, self.w, self.h = float(x), float(y), float(w), float(h)
        self.visible = True
        self.seen = the_now

    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def draw(self):
        x = int(self.x + 0.5)
        y = int(self.y + 0.5)
        w = int(self.w + 0.5)
        h = int(self.h + 0.5)
        for i in range(LINE):
            if w - 2 * i > 0 and h - 2 * i > 0:
                overlay.rect(x + i, y + i, w - 2 * i, h - 2 * i, BOX_COLOR)

boxes = [Box() for _ in range(MAX_FACES)]

def redraw_boxes():
    overlay.clear(_CLEAR)
    for box in boxes:
        if box.visible:
            box.draw()

def show_faces(the_faces, the_now): # pylint: disable=too-many-locals
    """Move each box to the nearest new face, or start a new box"""
    matched = []
    for face in the_faces[:MAX_FACES]:
        x, y, w, h = face[0], face[1], face[2], face[3]
        if MIRROR:
            x = frame_w - x - w
        x, y, w, h = x * zoom, y * zoom, w * zoom, h * zoom
        cx, cy = x + w / 2, y + h / 2
        best = None
        best_distance = w
        for box in boxes:
            if box.visible and box not in matched:
                bx, by = box.center()
                distance = abs(bx - cx) + abs(by - cy)
                if distance < best_distance:
                    best, best_distance = box, distance
        if best is None:
            for box in boxes:
                if not box.visible:
                    best = box
                    break
        if best is not None:
            best.show(x, y, w, h, the_now)
            matched.append(best)

def hide_stale_boxes(the_now):
    changed = False
    for box in boxes:
        if box.visible and elapsed(the_now, box.seen) >= HOLD_MS:
            box.visible = False
            changed = True
    return changed

# --- Camera session, reconnecting when it fails ---
camera = frame = None
retry_at = ticks_ms()

def disconnect(error):
    global camera, frame, video, retry_at  # pylint: disable=global-statement
    if camera is not None:
        camera.close()
    camera = frame = None
    if video is not None:
        layers.remove(video)
        video = None
    detector.reset()
    for box in boxes:
        box.visible = False
    redraw_boxes()
    render()
    retry_at = (ticks_ms() + 3000) & _TICKS_MASK
    print("Camera problem, retrying in 3 s:", type(error).__name__, error)
    gc.collect()

def connect():
    global camera, frame, video  # pylint: disable=global-statement
    try:
        camera = CameraSession(
            CAMERA_MODE[0],
            CAMERA_MODE[1],
            DECODE_SCALE,
            read_timeout_ms=CAMERA_WAIT_MS,
            stale_seconds=5,
        )
        frame = memoryview(camera.bitmap).cast("B")
        # displayio bitmaps hold RGB565 high byte first, which is picogame's
        # transfer byte order, so picogame reads the camera bitmap directly.
        picture = picogame.Bitmap(camera.bitmap, frame_w, frame_h)
        video = picogame.Sprite(picture, 0, 0, flip_x=MIRROR)
        video.scale = zoom
        layers.insert(0, video)
        print("Camera connected: %dx%d MJPEG decoded at %dx%d" % (CAMERA_MODE + (frame_w, frame_h)))
    except (RuntimeError, OSError, ValueError, MemoryError) as error:
        disconnect(error)

def print_faces(the_faces):
    kind = "tracking" if detector.tracked else "full"
    if not the_faces:
        print("no face  [%s pass, %d raw hits]" % (kind, detector.hits))
        return
    parts = ["%dx%d at (%d, %d), %d hits" % (w, h, x, y, n) for x, y, w, h, n in the_faces]
    print(
        "%d face%s: %s  [%s pass, %d raw hits, %d ms]"
        % (
            len(the_faces),
            "" if len(the_faces) == 1 else "s",
            "; ".join(parts),
            kind,
            detector.hits,
            detector.pass_ms,
        )
    )

render()
gc.collect()
print("free memory: %d" % gc.mem_free())
cam_frames = draws = passes = full_passes = 0
draw_ms = work_ms = pass_ms = features = hits = faces_seen = 0
had_faces = False
report_at = ticks_ms()

while True:
    now = ticks_ms()
    if camera is None and reached(now, retry_at):
        connect()

    new_frame = False
    if camera is not None and not (PAUSE_CAMERA_DURING_SEARCH and detector.busy):
        try:
            new_frame = camera.poll()
        except (RuntimeError, OSError, ValueError, MemoryError) as error:
            disconnect(error)
    if new_frame:
        cam_frames += 1
        if not detector.busy:
            detector.start(frame)

    boxes_changed = False
    if detector.busy and detector.work(DETECT_SLICE_MS):
        faces = detector.faces
        show_faces(faces, ticks_ms())
        boxes_changed = bool(faces)
        passes += 1
        full_passes += 0 if detector.tracked else 1
        pass_ms += detector.pass_ms
        work_ms += detector.work_ms
        features += detector.features
        hits += detector.hits
        faces_seen += len(faces)
        if PRINT_FACES and (faces or had_faces):
            print_faces(faces)
        had_faces = bool(faces)
        if verifier is not None and not detector.tracked:
            again = [tuple(f) for f in verifier.detect(live_copy)]
            same = (verifier.hits, verifier.features) == (detector.hits, detector.features)
            if same:
                verified += 1
            else:
                mismatched += 1
            print(
                "verify: live pass %d hits, %d features, %d faces; same frame again"
                " %d hits, %d features, %d faces -> %s"
                % (
                    detector.hits,
                    detector.features,
                    len(faces),
                    verifier.hits,
                    verifier.features,
                    len(again),
                    "same" if same else "DIFFERENT",
                )
            )
    if hide_stale_boxes(ticks_ms()):
        boxes_changed = True
    if boxes_changed:
        redraw_boxes()
    if new_frame or boxes_changed:
        t0 = ticks_ms()
        render()
        draw_ms += elapsed(ticks_ms(), t0)
        draws += 1

    # debug printing
    if REPORT_SECONDS and elapsed(ticks_ms(), report_at) >= REPORT_SECONDS * 1000:
        n = max(passes, 1)
        line = (
            f"camera {cam_frames / REPORT_SECONDS:.1f} fps,"
            f" screen {draws / REPORT_SECONDS:.1f} fps ({draw_ms / max(draws, 1):.0f} ms each)"
            f" | passes {passes} ({full_passes} full):"
            f" {pass_ms // n} ms start to finish, {work_ms // n} ms working,"
            f" {features // n} features, {hits / n:.1f} raw hits, {faces_seen / n:.1f} faces"
            f" | frame brightness {detector.brightness}, contrast {detector.contrast}"
        )
        if verifier is not None:
            line += f" | verify: {verified} same, {mismatched} different"
        if camera is not None:
            snap = camera.snapshot()
            line += (
                f" | dropped {snap['partial_frames_dropped']},"
                f" decode errors {snap['decode_errors']},"
                f" max decode {snap['max_decode_ns'] / 1e6:.0f} ms"
            )
        print(line)
        cam_frames = draws = passes = full_passes = 0
        draw_ms = work_ms = pass_ms = features = hits = faces_seen = 0
        report_at = (report_at + REPORT_SECONDS * 1000) & _TICKS_MASK
