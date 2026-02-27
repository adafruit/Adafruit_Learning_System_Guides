# SPDX-FileCopyrightText: 2025 Pedro for Adafruit Industries
#
# SPDX-License-Identifier: MIT

'''PyPortal Art Display - Multi-feed with mode switching'''

# pylint: disable=global-statement,invalid-name,too-many-lines
# pylint: disable=consider-using-f-string,redefined-outer-name
# pylint: disable=no-member,protected-access,too-many-return-statements

from os import getenv
import os
import gc
import math
import time
import random
import supervisor
import board
import displayio  # pylint: disable=unused-import
import digitalio

from adafruit_pyportal import PyPortal
from adafruit_display_text import label
import terminalio
import adafruit_lis3dh

# ============================================
# FEED MODES - tap screen to cycle through
# Reorder or comment out to customize rotation
# ============================================
FEED_MODES = [
    "cma",
    "nasa",
    "cats",
    "dogs",
    "local",
]

# Starting mode (must be in FEED_MODES)
START_MODE = "cma"

# --- Cleveland Museum of Art settings ---
# No API key needed! CC0 open access with guaranteed images
CMA_API_URL = (
    "https://openaccess-api.clevelandart.org"
    "/api/artworks/"
)
CMA_IMAGE_COUNT = 37000  # CC0 works with images
CMA_DISPLAY_TIME = 60  # seconds between images

# --- NASA APOD settings ---
# Get a free key at https://api.nasa.gov
# Add NASA_API_KEY to your settings.toml
# DEMO_KEY works but is rate-limited (30/hr)
NASA_API_KEY = getenv("NASA_API_KEY") or "DEMO_KEY"
NASA_API_URL = (
    "https://api.nasa.gov/planetary/apod"
)
NASA_START_YEAR = 1995
NASA_END_YEAR = 2025
NASA_DISPLAY_TIME = 60  # seconds between images

# --- Cat API settings ---
# No API key needed
CAT_API_URL = (
    "https://api.thecatapi.com/v1/images/search"
)
CAT_DISPLAY_TIME = 60  # seconds between images

# --- Dog API settings ---
# No API key needed
DOG_API_URL = (
    "https://dog.ceo/api/breeds/image/random"
)
DOG_DISPLAY_TIME = 60  # seconds between images

# --- Local SD card settings ---
# Place BMP images in /sd/imgs/
LOCAL_IMG_PATH = "/sd/imgs"
LOCAL_DISPLAY_TIME = 60  # seconds between images

# ============================================
# DISPLAY & HARDWARE SETUP
# ============================================
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height
board.DISPLAY.rotation = 0
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

# Skip button on D3 (pull-up, active low)
# Set to False if no button is wired to D3
USE_BUTTON = False
skip_btn = None
if USE_BUTTON:
    skip_btn = digitalio.DigitalInOut(board.D3)
    skip_btn.direction = digitalio.Direction.INPUT
    skip_btn.pull = digitalio.Pull.UP

# --- LIS3DH Accelerometer (STEMMA I2C) ---
# Set to False if no accelerometer is connected
USE_ACCEL = True
lis3dh = None

# Tilt detection: LIS3DH on back of diamond-oriented display.
# Resting position reads ~-10 to -16 degrees on Z-axis.
# Tilt left (-8 to -2) or right (-31 to -19) = skip.
TILT_TARGET_LEFT = -1.5    # center of left zone (0 to -3)
TILT_TARGET_RIGHT = -60   # center of right zone (-50 to -70)
TILT_THRESHOLD_LEFT = 6    # +/- tolerance (range: 0 to -3)
TILT_THRESHOLD_RIGHT = 30  # +/- tolerance (range: -50 to -70)
TILT_HOLD_TIME = 0.5      # seconds to hold at target before skip
tilt_start = 0.0          # when tilt was first detected

# Shake detection: triggers skip on quick shake gesture
SHAKE_THRESHOLD = 20.0    # m/s^2 total accel (1g = 9.8)
SHAKE_COUNT_NEEDED = 2    # spikes needed within window
SHAKE_WINDOW = 0.5        # seconds to collect spikes
shake_times = []          # timestamps of detected spikes

if USE_ACCEL:
    try:
        i2c = board.I2C()
        lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)
        lis3dh.range = adafruit_lis3dh.RANGE_2_G
        print("LIS3DH accelerometer found!")
    except (ValueError, RuntimeError) as accel_err:
        print("No LIS3DH found:", accel_err)
        lis3dh = None
        USE_ACCEL = False

# --- Audio confirmation chirp ---
BEEP_FREQ_START = 843    # chirp start frequency Hz
BEEP_FREQ_END = 1200     # chirp end frequency Hz
BEEP_DURATION = 0.2      # seconds (short chirp)
BEEP_WAV = "/sd/beep.wav"


def play_beep():
    '''Play confirmation chirp via PyPortal's built-in audio.'''
    try:
        pyportal.play_file(BEEP_WAV)
    except (OSError, RuntimeError) as err:
        print("Beep error:", err)


def get_tilt_angle():
    '''Get Z-axis tilt angle in degrees.
    Returns ~-45 at rest on stand, ~0 when upright.'''
    if not lis3dh:
        return None
    _, accel_y, accel_z = lis3dh.acceleration
    angle = math.degrees(math.atan2(accel_z, accel_y))
    return angle


def check_tilt_skip():
    '''Check if display is tilted left or right long enough.
    Returns True if held in either zone for TILT_HOLD_TIME.'''
    global tilt_start  # pylint: disable=global-statement
    if not USE_ACCEL:
        return False
    angle = get_tilt_angle()
    if angle is None:
        return False
    in_left = abs(angle - TILT_TARGET_LEFT) < TILT_THRESHOLD_LEFT
    in_right = abs(angle - TILT_TARGET_RIGHT) < TILT_THRESHOLD_RIGHT
    if in_left or in_right:
        if tilt_start == 0.0:
            tilt_start = time.monotonic()
            direction = "left" if in_left else "right"
            print("Tilt: %s detected (%.0f deg)" % (
                direction, angle))
        else:
            elapsed = time.monotonic() - tilt_start
            remaining = TILT_HOLD_TIME - elapsed
            if remaining > 0:
                status_text.text = "Skip: %.1fs" % remaining
            if elapsed >= TILT_HOLD_TIME:
                print("Tilt: held %.1fs - skip!" % TILT_HOLD_TIME)
                status_text.text = ""
                play_beep()
                tilt_start = 0.0
                return True
    else:
        if tilt_start != 0.0:
            tilt_start = 0.0
            status_text.text = ""
    return False


def check_shake():
    '''Detect shake gesture from acceleration spikes.
    Returns True if enough spikes within time window.'''
    global shake_times  # pylint: disable=global-statement
    if not USE_ACCEL:
        return False
    accel_x, accel_y, accel_z = lis3dh.acceleration
    magnitude = math.sqrt(
        accel_x * accel_x
        + accel_y * accel_y
        + accel_z * accel_z
    )
    now = time.monotonic()
    if magnitude > SHAKE_THRESHOLD:
        shake_times.append(now)
    # Prune old spikes outside window
    shake_times = [t for t in shake_times
                   if now - t < SHAKE_WINDOW]
    if len(shake_times) >= SHAKE_COUNT_NEEDED:
        print("Shake detected! (%.1f m/s^2)" % magnitude)
        shake_times = []
        play_beep()
        return True
    return False


# Minimum pressure for a real tap (filters ghost touches from SPI noise)
TAP_PRESSURE = 40000


def check_tap():
    '''Check for a confirmed screen tap.
    Requires minimum pressure and a second read to filter ghosts.'''
    touch = pyportal.touchscreen.touch_point
    if touch and touch[2] > TAP_PRESSURE:
        time.sleep(0.05)  # brief pause
        confirm = pyportal.touchscreen.touch_point
        if confirm and confirm[2] > TAP_PRESSURE:
            return True
    return False


def tap_aware_sleep(seconds):
    '''Sleep for given seconds but check for taps every 0.2s.
    Returns True if tapped, False if completed.'''
    end_time = time.monotonic() + seconds
    while time.monotonic() < end_time:
        if check_tap():
            return True
        time.sleep(0.2)
    return False


TAP_WINDOW = 0.8          # seconds to wait for additional taps


def count_taps():
    '''Count total taps within TAP_WINDOW after first tap.
    Returns tap count (1 if no extra taps detected).'''
    taps = 1
    deadline = time.monotonic() + TAP_WINDOW
    while time.monotonic() < deadline:
        if check_tap():
            taps = taps + 1
            # Reset window on each tap
            deadline = time.monotonic() + TAP_WINDOW
        time.sleep(0.1)
    return taps


# ============================================
# DIAGONAL SLIDE TRANSITION
# ============================================
WIPE_STEPS = 8           # number of animation frames
WIPE_DELAY = 0.02        # seconds between frames
# Drip bias: 0.0=pure vertical, 1.0=equal diagonal
WIPE_X_BIAS = 1           # equal diagonal


def wipe_transition(bg_path):
    '''Diagonal slide transition - paint drip style.
    New image slides over old from top-left corner.
    Both images visible during transition, no black.
    Ease-in curve accelerates like gravity on paint.
    Vertical bias makes it feel like dripping down.'''
    gc.collect()

    try:
        new_bmp = displayio.OnDiskBitmap(bg_path)
        new_tile = displayio.TileGrid(
            new_bmp, pixel_shader=new_bmp.pixel_shader
        )
    except MemoryError:
        print("Wipe: low memory, direct swap")
        pyportal.set_background(bg_path)
        return

    # Start off-screen: mostly above, slightly left
    new_tile.x = int(-WIDTH * WIPE_X_BIAS)
    new_tile.y = -HEIGHT

    board.DISPLAY.auto_refresh = False
    try:
        pyportal.root_group.remove(text_area)
    except ValueError:
        pass
    try:
        pyportal.root_group.remove(status_text)
    except ValueError:
        pass

    # New image on top of old background
    pyportal.root_group.append(new_tile)
    pyportal.root_group.append(text_area)
    pyportal.root_group.append(status_text)
    board.DISPLAY.auto_refresh = True

    # Animate with ease-in (accelerates like dripping)
    for step in range(1, WIPE_STEPS + 1):
        t = step / WIPE_STEPS
        progress = t * t  # ease-in: slow start, fast finish
        new_x = int(-WIDTH * WIPE_X_BIAS * (1.0 - progress))
        new_y = int(-HEIGHT * (1.0 - progress))
        new_tile.x = new_x
        new_tile.y = new_y
        time.sleep(WIPE_DELAY)

    # Snap to final position
    new_tile.x = 0
    new_tile.y = 0

    # Cleanup: remove old layers below new_tile
    # (avoids pyportal.set_background which forces a refresh)
    board.DISPLAY.auto_refresh = False
    while (len(pyportal.root_group) > 0
           and pyportal.root_group[0] != new_tile):
        pyportal.root_group.pop(0)
    board.DISPLAY.auto_refresh = True
    gc.collect()


def url_encode(url_string):
    '''Simple URL encoding for image URLs.'''
    encoded = ""
    for char in url_string:
        if char == " ":
            encoded += "%20"
        elif char == '"':
            encoded += "%22"
        elif char == "'":
            encoded += "%27"
        elif char == "#":
            encoded += "%23"
        elif char == "?":
            encoded += "%3F"
        elif char == "&":
            encoded += "%26"
        else:
            encoded += char
    return encoded


# Adafruit IO image converter credentials
AIO_USER = getenv("ADAFRUIT_AIO_USERNAME") or ""
AIO_KEY = getenv("ADAFRUIT_AIO_KEY") or ""

IMAGE_CONVERTER_BASE = (
    "https://io.adafruit.com/api/v2/"
    + AIO_USER
    + "/integrations/image-formatter"
)



# Check for required settings.toml keys
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
missing_keys = []
if not ssid or not password:
    missing_keys.append("WIFI")
    print("WARNING: WiFi credentials missing from settings.toml")
if not AIO_USER:
    missing_keys.append("AIO_USER")
    print("WARNING: ADAFRUIT_AIO_USERNAME missing")
if not AIO_KEY:
    missing_keys.append("AIO_KEY")
    print("WARNING: ADAFRUIT_AIO_KEY missing")
online_available = len(missing_keys) == 0

BACKGROUND_FILE = "/background.bmp"
if WIDTH > 320:
    BACKGROUND_FILE = "/background_480.bmp"

# Init PyPortal
pyportal = PyPortal(
    default_bg=BACKGROUND_FILE,
    image_resize=(WIDTH, HEIGHT),
    image_position=(0, 0),
)

# Generate chirp WAV file on SD card at startup
try:
    import struct
    # 16-bit mono PCM WAV at 16000 Hz
    sample_rate = 16000
    num_samples = int(sample_rate * BEEP_DURATION)
    data_size = num_samples * 2
    with open(BEEP_WAV, "wb") as wav_file:
        # WAV header
        wav_file.write(b"RIFF")
        wav_file.write(struct.pack("<I", 36 + data_size))
        wav_file.write(b"WAVEfmt ")
        wav_file.write(struct.pack("<IHHIIHH",
                                   16, 1, 1, sample_rate,
                                   sample_rate * 2, 2, 16))
        wav_file.write(b"data")
        wav_file.write(struct.pack("<I", data_size))
        # Chirp: ramp frequency from start to end
        # Phase accumulates based on instantaneous freq
        phase = 0.0
        for i in range(num_samples):
            t = i / num_samples  # 0.0 to 1.0
            freq = (BEEP_FREQ_START
                    + (BEEP_FREQ_END - BEEP_FREQ_START) * t)
            phase += 2 * math.pi * freq / sample_rate
            val = math.sin(phase)
            sample = int(val * 32000)
            wav_file.write(struct.pack("<h", sample))
    print("Chirp WAV generated!")
except (OSError, RuntimeError) as wav_err:
    print("WAV generation error:", wav_err)

# Title text at bottom with white background bar
text_area = label.Label(
    terminalio.FONT,
    text="Loading...",
    color=0x000000,
    background_color=0xFFFFFF,
    padding_top=2,
    padding_bottom=2,
    padding_left=4,
    padding_right=4,
    x=5,
    y=HEIGHT - 15
)
pyportal.root_group.append(text_area)

# Status text in top right with dark background
status_text = label.Label(
    terminalio.FONT,
    text="",
    color=0xFFFF00,
    background_color=0x000000,
    padding_top=1,
    padding_bottom=1,
    padding_left=3,
    padding_right=3,
    anchor_point=(1.0, 0.0),
    anchored_position=(WIDTH - 5, 5)
)
pyportal.root_group.append(status_text)

# ============================================
# MODE MANAGEMENT
# ============================================
feed_index = FEED_MODES.index(START_MODE)
current_feed = FEED_MODES[feed_index]

# Show startup warnings for missing hardware/settings
startup_warnings = []
if not USE_ACCEL:
    startup_warnings.append("No accelerometer")
if missing_keys:
    startup_warnings.append(
        "No keys: " + ", ".join(missing_keys)
    )

# Force local mode if online features unavailable
if not online_available:
    current_feed = "local"
    feed_index = FEED_MODES.index("local")
    print("Online unavailable, forcing local mode")

# Flash warnings briefly at startup
if startup_warnings:
    for warning in startup_warnings:
        print("STARTUP:", warning)
        status_text.text = warning
        time.sleep(2)
    status_text.text = ""

# Prefetch state - alternate cache files to avoid
# overwriting the currently displayed OnDiskBitmap
prefetch_ready = False
prefetch_title = ""
prefetch_file = "/sd/cache2.bmp"  # next prefetch target
display_file = "/sd/cache.bmp"    # currently shown file

# Cache list of local images
local_images = []


def load_local_images():
    '''Scan /sd/imgs/ for BMP files.'''
    global local_images
    local_images = []
    try:
        for fname in os.listdir(LOCAL_IMG_PATH):
            if fname.lower().endswith(".bmp") and not fname.startswith("."):
                local_images.append(fname)
        print("Found", len(local_images), "local images")
    except OSError:
        print("No /sd/imgs/ folder found!")


def next_mode(steps=1):
    '''Cycle feed mode forward by steps.
    Skips online modes if settings are missing.'''
    global feed_index, current_feed  # pylint: disable=global-statement
    feed_index = (feed_index + steps) % len(FEED_MODES)
    # Skip online modes if WiFi/AIO keys are missing
    if not online_available:
        attempts = len(FEED_MODES)
        while FEED_MODES[feed_index] != "local" and attempts > 0:
            feed_index = (feed_index + 1) % len(FEED_MODES)
            attempts -= 1
    current_feed = FEED_MODES[feed_index]
    print("=== Switched to: %s (%d tap%s) ===" % (
        current_feed, steps, "s" if steps > 1 else ""))
    text_area.text = "Mode: " + current_feed


def get_display_time():
    '''Get display time for current feed.'''
    times = {
        "cma": CMA_DISPLAY_TIME,
        "nasa": NASA_DISPLAY_TIME,
        "cats": CAT_DISPLAY_TIME,
        "dogs": DOG_DISPLAY_TIME,
        "local": LOCAL_DISPLAY_TIME,
    }
    return times.get(current_feed, 30)



# ============================================
# FEED HELPERS
# ============================================
def get_random_date():
    '''Generate a random date string for NASA APOD.'''
    year = random.randint(NASA_START_YEAR, NASA_END_YEAR)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    if year == 1995 and (month < 6 or
                         (month == 6 and day < 16)):
        month = 6
        day = 16
    return "{:04d}-{:02d}-{:02d}".format(year, month, day)


def build_feed_url():
    '''Build the API URL for the current feed.'''
    if current_feed == "nasa":
        rand_date = get_random_date()
        url = (
            NASA_API_URL
            + "?api_key=" + NASA_API_KEY
            + "&date=" + rand_date
        )
        print("NASA APOD date:", rand_date)
        return url
    if current_feed == "cats":
        return CAT_API_URL
    if current_feed == "dogs":
        return DOG_API_URL
    # Cleveland Museum of Art - random CC0 artwork with image
    skip = random.randint(0, CMA_IMAGE_COUNT - 1)
    return (
        CMA_API_URL
        + "?has_image=1&cc0&limit=1"
        + "&skip=" + str(skip)
        + "&fields=title,images"
    )


def validate_image(json_data):
    '''Check if JSON data has a usable image URL.'''
    if not json_data or not isinstance(json_data, dict):
        return None

    if current_feed == "nasa":
        media_type = json_data.get("media_type", "")
        if media_type != "image":
            print("Not an image (media_type:",
                  media_type, "), skipping...")
            return None
        img = json_data.get("url", "")
    elif current_feed == "cats":
        img = json_data.get("url", "")
    elif current_feed == "dogs":
        img = json_data.get("message", "")
    elif current_feed == "cma":
        try:
            img = json_data["images"]["web"]["url"]
        except (KeyError, TypeError):
            return None
    else:
        img = json_data.get("primaryImage", "")

    if img and len(img) > 10:
        return img
    return None


def get_title(json_data):
    '''Extract title from JSON data.'''
    if not json_data or not isinstance(json_data, dict):
        return "Untitled"

    if current_feed == "cats":
        cat_id = json_data.get("id", "???")
        return "Cat #" + str(cat_id)

    if current_feed == "dogs":
        img = json_data.get("message", "")
        try:
            breed = img.split("/breeds/")[1]
            breed = breed.split("/")[0]
            breed = breed.replace("-", " ").title()
        except (IndexError, AttributeError):
            breed = "Unknown"
        return breed

    # CMA, Met, and NASA all use 'title' key
    title = json_data.get("title", "Untitled")
    if not title:
        return "Untitled"
    max_chars = 40
    if len(title) > max_chars:
        title = title[:max_chars - 3] + "..."
    return title


# ============================================
# LOCAL IMAGE DISPLAY
# ============================================
def show_local_image():
    '''Display a random BMP from /sd/imgs/.'''
    if not local_images:
        load_local_images()
    if not local_images:
        print("No local images available!")
        text_area.text = "No images in /sd/imgs/"
        return False

    fname = random.choice(local_images)
    filepath = LOCAL_IMG_PATH + "/" + fname
    print("Local image:", filepath)

    try:
        wipe_transition(filepath)
        # Use filename without extension as title
        title = fname.rsplit(".", 1)[0]
        max_chars = 40
        if len(title) > max_chars:
            title = title[:max_chars - 3] + "..."
        text_area.text = title
        status_text.text = ""
        gc.collect()
        print("Local image displayed!")
        return True
    except (OSError, RuntimeError, MemoryError) as err:
        print("Local image error:", err)
        return False


FALLBACK_RETRY_TIME = 40  # seconds to retry online before SD fallback


def show_fallback_local():
    '''Retry online images for FALLBACK_RETRY_TIME seconds
    before falling back to a local SD card image.
    Returns True if online image loaded, "mode" if mode
    changed, False if fell back to local.'''
    # First, try online retries while current image stays
    deadline = time.monotonic() + FALLBACK_RETRY_TIME
    attempt = 0
    while time.monotonic() < deadline:
        # Check for tap to switch modes between retries
        if check_tap():
            print("Tap during retry: cycle mode")
            return "mode"
        attempt = attempt + 1
        remaining = int(deadline - time.monotonic())
        print("Retry online #%d (%ds left)..." % (
            attempt, remaining))
        status_text.text = "Retry #%d..." % attempt
        try:
            result = show_online_image()
            if result is True:
                print("Online image loaded!")
                return True
            if result == "mode":
                return result
        except (RuntimeError, Exception) as err:  # pylint: disable=broad-except
            print("Retry error:", err)
        gc.collect()
        # Tap-aware wait between retries
        if tap_aware_sleep(3):
            print("Tap during retry wait: cycle mode")
            return "mode"

    # All retries failed, now show local fallback
    print("Online retries exhausted, loading SD fallback...")
    if not local_images:
        load_local_images()
    if not local_images:
        print("No local fallback images available")
        return False
    show_local_image()
    return False


# ============================================
# ONLINE IMAGE DISPLAY
# ============================================
def show_online_image():
    '''Fetch and display an image from the API.
    Returns True on success, False on failure,
    or "mode" if screen was tapped mid-load.'''
    global display_file, prefetch_file  # pylint: disable=global-statement
    url = build_feed_url()
    print("Fetching:", url)
    status_text.text = "Fetching..."

    # Use low-level fetch for clean JSON handling
    response = pyportal.network.fetch(url)
    json_data = response.json()
    response.close()

    # Let touchscreen settle after SPI, check for tap
    if tap_aware_sleep(0.5):
        print("Tap during fetch: cycle mode")
        return "mode"

    # Cat API returns a list
    if isinstance(json_data, list) and json_data:
        json_data = json_data[0]

    # CMA API returns {"data": [...]}
    if current_feed == "cma":
        try:
            json_data = json_data["data"][0]
        except (KeyError, IndexError, TypeError):
            print("No CMA data in response")
            return False

    new_title = get_title(json_data)
    print("Title:", new_title)

    # Validate image URL
    image_url = validate_image(json_data)
    json_data = None
    gc.collect()
    if not image_url:
        print("No valid image, skipping...")
        return False

    # Check for tap before starting download
    if check_tap():
        print("Tap before download: cycle mode")
        return "mode"

    print("Fetching image:", image_url)
    status_text.text = "Downloading..."
    gc.collect()

    # Build converter URL manually with proper encoding
    safe_url = url_encode(image_url)
    converted = (
        IMAGE_CONVERTER_BASE
        + "?x-aio-key=" + AIO_KEY
        + "&width=" + str(WIDTH)
        + "&height=" + str(HEIGHT)
        + "&output=BMP16"
        + "&url=" + safe_url
    )
    print("Converter URL:", converted)
    # Download to non-displayed file to avoid glitch
    # (OnDiskBitmap reads live from disk)
    pyportal.network.wget(converted, prefetch_file)
    status_text.text = "Tap: switch mode"

    # Extended tap window after download
    if tap_aware_sleep(1.0):
        print("Tap after download: cycle mode")
        return "mode"

    # Check cached BMP file size
    file_size = os.stat(prefetch_file)[6]
    print("Image file size:", file_size, "bytes")

    if file_size < 100000:
        print("Image too small, trying another...")
        return False

    wipe_transition(prefetch_file)

    # Swap file roles: just-displayed file is protected,
    # old display file becomes next download target
    display_file, prefetch_file = prefetch_file, display_file
    print("Cache swap -> display:", display_file,
          "prefetch:", prefetch_file)

    print("Image displayed!")
    text_area.text = new_title
    status_text.text = ""
    gc.collect()
    return True


# ============================================
# PREFETCH - download next image while current shows
# ============================================
def prefetch_online_image():
    '''Download next image to alternate cache file.
    Current image stays on screen during download.
    Returns True on success, False on failure,
    or "mode" if screen was tapped mid-load.'''
    global prefetch_ready, prefetch_title  # pylint: disable=global-statement
    prefetch_ready = False
    prefetch_title = ""
    status_text.text = "Prefetching..."
    gc.collect()

    url = build_feed_url()
    print("Prefetch to:", prefetch_file)
    print("Prefetch:", url)

    response = pyportal.network.fetch(url)
    json_data = response.json()
    response.close()

    # Let touchscreen settle after SPI, check for tap
    if tap_aware_sleep(0.5):
        print("Tap during prefetch: cycle mode")
        return "mode"

    # Cat API returns a list
    if isinstance(json_data, list) and json_data:
        json_data = json_data[0]

    # CMA API returns {"data": [...]}
    if current_feed == "cma":
        try:
            json_data = json_data["data"][0]
        except (KeyError, IndexError, TypeError):
            print("Prefetch: no CMA data")
            status_text.text = "Prefetch failed"
            return False

    title = get_title(json_data)
    image_url = validate_image(json_data)
    json_data = None
    gc.collect()
    if not image_url:
        print("Prefetch: no valid image")
        status_text.text = "Prefetch failed"
        return False

    print("Prefetch image:", image_url)
    gc.collect()

    safe_url = url_encode(image_url)
    converted = (
        IMAGE_CONVERTER_BASE
        + "?x-aio-key=" + AIO_KEY
        + "&width=" + str(WIDTH)
        + "&height=" + str(HEIGHT)
        + "&output=BMP16"
        + "&url=" + safe_url
    )
    pyportal.network.wget(converted, prefetch_file)

    # Let touchscreen settle after SPI, check for tap
    if tap_aware_sleep(0.5):
        print("Tap after prefetch: cycle mode")
        return "mode"

    file_size = os.stat(prefetch_file)[6]
    print("Prefetch size:", file_size, "bytes")

    if file_size < 100000:
        print("Prefetch: image too small")
        status_text.text = "Prefetch failed"
        return False

    prefetch_title = title
    prefetch_ready = True
    print("Prefetch ready:", title)
    status_text.text = "Prefetch ready"
    return True


def display_prefetched():
    '''Instantly display the prefetched image.
    Swaps cache file roles so next prefetch writes
    to the file that is no longer on screen.'''
    global prefetch_ready  # pylint: disable=global-statement
    global display_file, prefetch_file
    if not prefetch_ready:
        return False
    wipe_transition(prefetch_file)
    text_area.text = prefetch_title
    status_text.text = ""
    prefetch_ready = False

    # Swap: displayed file becomes safe from overwrite,
    # old display file becomes next prefetch target
    display_file, prefetch_file = prefetch_file, display_file
    print("Cache swap -> display:", display_file,
          "prefetch:", prefetch_file)

    gc.collect()
    print("Displayed prefetched image!")
    return True


# ============================================
# INPUT HANDLING
# ============================================
def wait_for_input(duration):
    '''Wait for duration seconds.
    Returns "skip" for D3 button, tilt, or shake.
    Returns "mode" for screen tap.
    Returns "timeout" if time expires.'''
    global tilt_start  # pylint: disable=global-statement
    global shake_times
    stamp = time.monotonic()
    tap_cooldown = stamp + 1.0  # ignore taps for 1s
    btn_was_pressed = False
    tilt_start = 0.0  # reset tilt timer
    shake_times = []   # reset shake history

    while (time.monotonic() - stamp) < duration:
        # D3 button (active low) - skip image
        if USE_BUTTON and not skip_btn.value:
            if not btn_was_pressed:
                btn_was_pressed = True
                print("Button: skip image")
                time.sleep(0.2)  # debounce
                return "skip"
        else:
            btn_was_pressed = False

        # LIS3DH tilt to flat - skip image
        if check_tilt_skip():
            return "skip"

        # LIS3DH shake - skip image
        if check_shake():
            return "skip"

        # Touchscreen tap - cycle mode
        if time.monotonic() > tap_cooldown:
            if check_tap():
                print("Tap: cycle mode")
                return "mode"

        time.sleep(0.05)

    return "timeout"


# ============================================
# MAIN LOOP
# ============================================
load_local_images()
loopcount = 0
errorcount = 0

print("Starting art display...")
print("Mode:", current_feed)
text_area.text = "Mode: " + current_feed

while True:
    try:
        # Check for mode tap at start of each cycle
        if check_tap():
            taps = count_taps()
            next_mode(taps)
            prefetch_ready = False
            if current_feed == "local":
                load_local_images()
            text_area.text = "Mode: " + current_feed
            status_text.text = ""
            time.sleep(0.5)
            continue

        success = False

        if current_feed == "local":
            prefetch_ready = False
            success = show_local_image()
            if not success:
                tap_aware_sleep(2)
                continue
        elif prefetch_ready:
            # Instant display from cache2!
            success = display_prefetched()
            if not success:
                result = show_online_image()
                if result == "mode":
                    next_mode(count_taps())
                    prefetch_ready = False
                    if current_feed == "local":
                        load_local_images()
                    time.sleep(0.5)
                    continue
                if not result:
                    fb = show_fallback_local()
                    if fb == "mode":
                        next_mode(count_taps())
                        prefetch_ready = False
                        if current_feed == "local":
                            load_local_images()
                    continue
        else:
            result = show_online_image()
            if result == "mode":
                next_mode(count_taps())
                prefetch_ready = False
                if current_feed == "local":
                    load_local_images()
                time.sleep(0.5)
                continue
            if not result:
                fb = show_fallback_local()
                if fb == "mode":
                    next_mode(count_taps())
                    prefetch_ready = False
                    if current_feed == "local":
                        load_local_images()
                continue

        loopcount = loopcount + 1
        errorcount = 0
        print("Success! Loop:", loopcount)

    except MemoryError as mem_err:
        print("Main loop OOM:", mem_err)
        gc.collect()
        print("Free after gc:", gc.mem_free())
        errorcount = errorcount + 1
        if errorcount > 3:
            print("Repeated OOM, restarting...")
            status_text.text = "OOM restart..."
            time.sleep(2)
            supervisor.reload()
        tap_aware_sleep(5)
        continue

    except (KeyError, TypeError, ValueError) as parse_err:
        print("Data parsing error:", parse_err)
        tap_aware_sleep(5)
        continue

    except Exception as err:  # pylint: disable=broad-except
        error_str = str(err)
        print("Error:", error_str)

        if "404" in error_str or "Not Found" in error_str:
            print("Not found, trying local fallback...")
            fb = show_fallback_local()
            if fb == "mode":
                next_mode(count_taps())
                prefetch_ready = False
                if current_feed == "local":
                    load_local_images()
            continue
        if "422" in error_str or "Unprocessable" in error_str:
            print("Can't be processed, trying local fallback...")
            fb = show_fallback_local()
            if fb == "mode":
                next_mode(count_taps())
                prefetch_ready = False
                if current_feed == "local":
                    load_local_images()
            continue
        if ("ESP32 not responding" in error_str
                or "BrokenPipe" in error_str
                or "Expected" in error_str):
            print("ESP32 SPI/WiFi error - resetting...")
            try:
                pyportal.network._wifi.esp.reset()
                print("ESP32 reset complete, waiting...")
                if tap_aware_sleep(10):
                    next_mode(count_taps())
                    prefetch_ready = False
                    if current_feed == "local":
                        load_local_images()
            except RuntimeError:
                print("Reset failed, continuing...")
                tap_aware_sleep(5)
            continue
        if "429" in error_str or "Too Many" in error_str:
            print("Rate limited, switching mode...")
            next_mode()
            prefetch_ready = False
            if current_feed == "local":
                load_local_images()
            tap_aware_sleep(2)
            continue
        if "401" in error_str or "Unauthorized" in error_str:
            print("Auth error - check credentials")
            errorcount = errorcount + 1
        elif "range step" in error_str:
            print("Internal error, retrying...")
            tap_aware_sleep(2)
            continue
        else:
            print("Unexpected error, retrying...")
            errorcount = errorcount + 1

        if errorcount > 10:
            print("Too many errors, restarting...")
            status_text.text = "Restarting..."
            time.sleep(2)
            supervisor.reload()
        tap_aware_sleep(5)
        continue

    # --- Wait for timeout, button, or tap ---
    display_time = get_display_time()
    result = None

    if current_feed == "local":
        # No prefetch needed for local images
        result = wait_for_input(display_time)
    else:
        # Phase 1: prefetch next image (2 attempts)
        gc.collect()
        for pf_attempt in range(2):
            print(
                "--- Prefetch #%d (free: %d) ---"
                % (pf_attempt + 1, gc.mem_free())
            )
            try:
                pf_result = prefetch_online_image()
                if pf_result == "mode":
                    result = "mode"
                break  # success or mode, stop retrying
            except MemoryError as mem_err:
                print("Prefetch OOM:", mem_err)
                gc.collect()
                if pf_attempt == 0:
                    status_text.text = "Retrying prefetch"
                    tap_aware_sleep(5)
                    gc.collect()
                else:
                    status_text.text = "Prefetch: low mem"
                    prefetch_ready = False
            except Exception as pf_err:  # pylint: disable=broad-except
                print("Prefetch error:", pf_err)
                gc.collect()
                if pf_attempt == 0:
                    status_text.text = "Retrying prefetch"
                    tap_aware_sleep(5)
                    gc.collect()
                else:
                    status_text.text = "Prefetch failed"
                    prefetch_ready = False

        # Phase 2: wait full display time (skip/tap still work)
        if result != "mode":
            result = wait_for_input(display_time)

    if result == "mode":
        next_mode(count_taps())
        prefetch_ready = False
        if current_feed == "local":
            load_local_images()
        time.sleep(0.5)
    # "skip" and "timeout" loop to next image
    # prefetch_ready stays True so cached image is used
