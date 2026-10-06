# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Monster eyes (eyes_viper) that look toward motion seen by a Logitech C270"""

import array
import gc
import time

import board
import displayio
import picodvi

import eye_motion
import eyes_viper
from eyes_camera import CameraSession
from motion_gaze import MotionGaze

# --- Eyes ---
CONFIG_PATH = "/config.eye"
EYE_GAP = 16  # screen pixels between the two eyes

# --- Camera and motion ---
# The camera is checked once after each eye frame
CAMERA_WAIT_MS = 5
SENSITIVITY = 0  # 0 least, 2 most sensitive (motion_gaze.py)
MIRROR_X = True
PRINT_MOTION = True  # print each detected motion target
# Seconds without motion before the eyes disappear
SLEEP_SECONDS = 15

# --- Gaze ---
GAZE_RANGE = 1.0  # less than 1.0 keeps the eyes away from the extremes
REPORT_SECONDS = 4  # 0 for no timing reports

# --- Display and eyes ---
displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    320,
    240,
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
width, height = framebuffer.width, framebuffer.height

eyes = eyes_viper.Eyes(width, height, CONFIG_PATH, gap=EYE_GAP)
load_start = time.monotonic()
eyes.begin()
print("eyes ready in %.1f s" % (time.monotonic() - load_start))

try:
    screen = memoryview(framebuffer)
except TypeError as error:
    raise RuntimeError("this firmware's framebuffer has no buffer protocol") from error
gc.collect()
eyes.attach(screen)
wait_for_vblank = getattr(framebuffer, "wait_for_vblank", None)

blank_args = array.array("i", [0, width, height, width, 0])
background_args = array.array("i", [0, width, height, width, eyes.settings.eyelid_color])

def fill_screen(args):
    if wait_for_vblank is not None:
        wait_for_vblank()
    eyes_viper.fill(screen, args)

def look_at(x, y):
    """Point the eyes; x and y run -1..1 with positive y meaning down, as in
    the camera image. eyes_viper's set_gaze() counts positive y as up, so y
    is flipped here. set_gaze() also takes the gaze from eyes_viper's own
    wandering for good, which keeps the eyes still between detections."""
    eyes.set_gaze(x, -y)

# --- Camera session, reconnecting when it fails ---
camera = gaze = current = None
previous = bytearray(38400)
stats = bytearray(208)
retry_at = 0.0

def disconnect(e):
    global camera, current, retry_at  # pylint: disable=global-statement
    if camera is not None:
        camera.close()
    camera = current = None
    retry_at = time.monotonic() + 3
    print("Camera problem, retrying in 3 s:", type(e).__name__, e)
    gc.collect()

def connect():
    global camera, current, gaze  # pylint: disable=global-statement
    try:
        camera = CameraSession(read_timeout_ms=CAMERA_WAIT_MS, stale_seconds=5)
        current = memoryview(camera.bitmap).cast("B")
        previous[:] = current
        gaze = MotionGaze(mirror_x=MIRROR_X, sensitivity=SENSITIVITY)
        print("Camera connected")
    except (RuntimeError, OSError, ValueError, MemoryError) as error:
        disconnect(error)

def print_target():
    tx = -gaze.target_x if gaze.mirror_x else gaze.target_x
    cam_x = (tx + 1000) * 15 // 2000 * 10 + 5
    cam_y = (gaze.target_y + 1000) * 11 // 2000 * 10 + 5
    print(
        f"Motion at camera x={cam_x} y={cam_y} of 160x120",
        f"(strength {gaze.strength}) -> gaze {gaze.target_x:+d}, {gaze.target_y:+d}",
    )

look_at(0, 0)
last_xy = (0, 0)
awake = not SLEEP_SECONDS
last_motion = time.monotonic()
if not awake:
    fill_screen(blank_args)
    print("Waiting for motion (screen blank)")

gc.collect()
print("free memory: %d" % gc.mem_free())
eye_frames = cam_frames = 0
draw_ns = present_ns = camera_ns = 0
report_ns = time.monotonic_ns() + REPORT_SECONDS * 1_000_000_000

while True:
    if camera is None and time.monotonic() >= retry_at:
        connect()

    # --- One monster-eye frame, only while the eyes are on screen ---
    t0 = time.monotonic_ns()
    drew = awake
    if drew:
        eyes.update()
        eyes.draw()
        t1 = time.monotonic_ns()
        eyes.present(wait_for_vblank)
        t2 = time.monotonic_ns()
    else:
        t1 = t2 = time.monotonic_ns()

    # --- The camera, motion when a frame has completed ---
    if camera is not None:
        try:
            if camera.poll():
                eye_motion.process(previous, current, stats)
                gaze.update(stats, time.monotonic())
                cam_frames += 1
                if gaze.signal == "motion":
                    last_motion = time.monotonic()
                    if not awake:
                        awake = True
                        fill_screen(background_args)
                        print("Motion detected: eyes on")
                    if PRINT_MOTION:
                        print_target()
        except (RuntimeError, OSError, ValueError, MemoryError) as error:
            disconnect(error)
    t3 = time.monotonic_ns()

    # --- Steer the eyes ---
    if gaze is not None:
        state = gaze.update(None, time.monotonic(), new_frame=False)
        xy = (state["x"], state["y"])
        if xy != last_xy:
            look_at(xy[0] / 1000 * GAZE_RANGE, xy[1] / 1000 * GAZE_RANGE)
            last_xy = xy

    # --- Blank the screen after SLEEP_SECONDS without motion ---
    if awake and SLEEP_SECONDS and time.monotonic() - last_motion >= SLEEP_SECONDS:
        awake = False
        look_at(0, 0)  # come back centered next time
        last_xy = (0, 0)
        fill_screen(blank_args)
        print(f"No motion for {SLEEP_SECONDS} s: eyes off")

    if drew:
        eye_frames += 1
        draw_ns += t1 - t0
        present_ns += t2 - t1
        camera_ns += t3 - t2

    # --- Timing report ---
    if REPORT_SECONDS and t3 >= report_ns:
        n = max(eye_frames, 1)
        line = (
            f"eyes {eye_frames / REPORT_SECONDS:.1f} fps,"
            f" camera {cam_frames / REPORT_SECONDS:.1f} fps"
            f" | ms per eye frame: draw {draw_ns / n / 1e6:.1f},"
            f" present {present_ns / n / 1e6:.1f}, camera {camera_ns / n / 1e6:.1f}"
        )
        if camera is not None:
            snap = camera.snapshot()
            line += (
                f" | dropped {snap['partial_frames_dropped']},"
                f" decode errors {snap['decode_errors']},"
                f" max decode {snap['max_decode_ns'] / 1e6:.0f} ms"
            )
        if not awake:
            line += " | eyes off"
        if gaze is not None:
            line += f" | gaze {gaze.x:+.0f}, {gaze.y:+.0f} ({gaze.signal})"
        print(line)
        eye_frames = cam_frames = 0
        draw_ns = present_ns = camera_ns = 0
        report_ns += REPORT_SECONDS * 1_000_000_000
