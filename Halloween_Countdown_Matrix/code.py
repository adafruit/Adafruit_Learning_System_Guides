import time
import board
from adafruit_matrixportal.matrixportal import MatrixPortal

EVENT_YEAR = 2021
EVENT_MONTH = 10
EVENT_DAY = 31
EVENT_HOUR = 17
EVENT_MINUTE = 0

FRAME_DURATION = 3
FRAMES = (
    "bmps/jack.bmp",
    "DAYS",
    "bmps/ghost.bmp",
    "HOURS",
    "bmps/bats.bmp",
    "MINUTES",
    "bmps/skull.bmp",
    "bmps/halloween.bmp",
)

EVENT_DAY_IMAGE = "bmps/happy_halloween.bmp"
SYNCHRONIZE_CLOCK = True

# --- Display setup ---
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=True)

current_frame = None

# Create a new label with the color and text selected
matrixportal.add_text(
    text_font="fonts/Arial-12.bdf",
    text_position=(4, (matrixportal.graphics.display.height // 2) - 1),
    text_color=0xEF7F31,
)


def set_time_until(unit=None):
    event_time = time.struct_time(
        (
            EVENT_YEAR,
            EVENT_MONTH,
            EVENT_DAY,
            EVENT_HOUR,
            EVENT_MINUTE,
            0,  # we don't track seconds
            -1,
            -1,
            False,
        )
    )
    remaining = time.mktime(event_time) - time.mktime(time.localtime())
    if remaining <= 0:
        # oh, its event time!
        matrixportal.set_background(EVENT_DAY_IMAGE)
        return
    remaining //= 60
    mins_remaining = remaining % 60
    remaining //= 60
    hours_remaining = remaining % 24
    remaining //= 24
    days_remaining = remaining

    if unit == "DAYS":
        text = "{} day".format(days_remaining)
        if days_remaining != 1:
            text += "s"
    if unit == "HOURS":
        text = "{} hour".format(hours_remaining)
        if hours_remaining != 1:
            text += "s"
    if unit == "MINUTES":
        text = "{} min".format(mins_remaining)
        if mins_remaining != 1:
            text += "s"
    matrixportal.set_text(text)
    matrixportal.set_background(0)


def set_next_frame():
    # pylint: disable=global-statement
    global current_frame

    # Advance to next frame if we already have one
    if current_frame is not None:
        current_frame += 1

    # Loop back or set initial frame
    if current_frame is None or current_frame >= len(FRAMES):
        current_frame = 0

    # Check if Picture or Text
    print(FRAMES[current_frame])
    if FRAMES[current_frame][-4:] == ".bmp":
        matrixportal.set_background(FRAMES[current_frame])
        matrixportal.set_text("")
    else:
        set_time_until(FRAMES[current_frame])


# Simulate the delay in case fetching time is fast
set_next_frame()
start_time = time.monotonic()
if SYNCHRONIZE_CLOCK:
    matrixportal.get_local_time()
while time.monotonic() < start_time + FRAME_DURATION:
    pass

while True:
    set_next_frame()
    time.sleep(FRAME_DURATION)
