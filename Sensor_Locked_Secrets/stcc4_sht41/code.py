# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import hashlib
import struct
import time

import board
import bitmaptools
import aesio
from displayio import Group, TileGrid, Palette, Bitmap
import supervisor
import terminalio
from adafruit_display_text.text_box import TextBox
from adafruit_display_text.bitmap_label import Label
import adafruit_binascii
import adafruit_stcc4
from digitalio import DigitalInOut, Direction, Pull

# =============================================================================
# USER CONFIGURATION
# =============================================================================

# --- Sequence of challenges ---
# Each entry is a dict with the following keys:
#
#   type        : "text"  -> Vigenère-encrypted ciphertext
#                 "image" -> AES-CTR-encrypted .abmp image file
#
#   data        : (text)  the ciphertext string
#                 (image) filename of the .abmp.enc file
#
#   sha256      : hex-encoded SHA-256 digest used to confirm correct decryption
#                 - text  -> SHA-256 of the plaintext string encoded as UTF-8
#                 - image -> SHA-256 of the raw decrypted pixel-data bytes
#                 Generate these offline with the encryptor web page.
#
#   reading     : which sensor data type drives this challenge. One of:
#                 "temperature" -> sensor.temperature (°C, float)
#                 "humidity"    -> sensor.relative_humidity (%, float)
#                 "co2"         -> sensor.CO2 (ppm, int)
#
#   precision_level : width of each unlock band, in the units of `reading`.
#                 e.g. reading=temperature, precision_level=1   -> bands like 22-23 (°C)
#                      reading=humidity,    precision_level=5   -> bands like 40-45 (%)
#                      reading=co2,         precision_level=100 -> bands like 400-500 (ppm)
#                 Must match the precision used at encryption time.
#
#   iv          : (image only) 16-byte AES initialisation vector matching
#                 the one used during encryption. "InitializationVe" is used
#                 by default if None. Omit or set None for text.
#
# Challenges must be worked through in order: solve #0 to unlock #1, etc.
#


SEQUENCE = [
    {
        "type":        "text",
        "data":        ">H5mv=h|bL3&iW4Fu]gbBNQ5&.2YC`J",
        "sha256":      "9313a63935c54a01de05e00bca67176639101f6251e411a7422ea1c0451a2588",
        "reading":     "temperature",
        "precision_level": 2,
    },
    {
        "type":        "image",
        "data":        "example_image.abmp.enc",
        "iv":          b"InitializationVe",
        "sha256":      "932185ffbba8b245a97a0819428d6038997e968174cadd3bd0a5bab970d0e560",
        "reading":     "humidity",
        "precision_level": 1,
    },
    # Add more entries here...
]

# Map of reading-type names to (sensor attribute, unit label for prints).
READING_TYPES = {
    "temperature": ("temperature", "°C"),
    "humidity": ("relative_humidity", "%"),
    "co2": ("CO2", "ppm"),
}

# --- Display rotation (degrees) ---
DISPLAY_ROTATION = 180

# =============================================================================
# END OF USER CONFIGURATION
# =============================================================================

# =============================================================================
# SENSOR SETUP
# =============================================================================

i2c = board.I2C()
sensor = adafruit_stcc4.STCC4(i2c)
sensor.continuous_measurement = True
SENSOR_READ_COOLDOWN = 1.0

# =============================================================================
# Validate SEQUENCE entries
# =============================================================================
if not SEQUENCE:
    raise ValueError("SEQUENCE must contain at least one entry.")

for _i, _entry in enumerate(SEQUENCE):
    if _entry.get("type") not in ("text", "image"):
        raise ValueError(f"SEQUENCE[{_i}]: 'type' must be 'text' or 'image'.")
    if not _entry.get("data"):
        raise ValueError(f"SEQUENCE[{_i}]: 'data' must be set.")
    if not _entry.get("sha256"):
        raise ValueError(f"SEQUENCE[{_i}]: 'sha256' must be set.")
    if _entry.get("reading") not in READING_TYPES:
        raise ValueError(
            f"SEQUENCE[{_i}]: 'reading' must be one of {list(READING_TYPES)}."
        )
    _bs = _entry.get("precision_level")
    if not isinstance(_bs, int) or _bs <= 0:
        raise ValueError(f"SEQUENCE[{_i}]: 'precision_level' must be a positive int.")
    if _entry["type"] == "image" and not _entry.get("iv"):
        SEQUENCE[_i]["iv"] = b"InitializationVe"

# Printable ASCII constants (text Vigenere)
ASCII_MIN = 32
ASCII_MAX = 126
ASCII_RANGE = ASCII_MAX - ASCII_MIN + 1  # 95

# =============================================================================
# BUTTON SETUP
# =============================================================================

btn = DigitalInOut(board.BOOT0)
btn.direction = Direction.INPUT
btn.pull = Pull.UP

# btn.value is True when not pressed (pull-up), False when pressed (active-low)
btn_prev_value = btn.value  # tracks last reading for edge detection

# =============================================================================
# DISPLAY SETUP
# =============================================================================

display = supervisor.runtime.display
display.rotation = DISPLAY_ROTATION

main_group = Group()
display.root_group = main_group

# --- Persistent HUD: progress label (always visible right side) ---
hud_group = Group(scale=2, x=2, y=2)

cur_reading_label = Label(terminalio.FONT)
cur_reading_label.anchor_point = (1.0, 1.0)
cur_reading_label.anchored_position = (display.width // 2, display.height // 2)

progress_label = Label(terminalio.FONT)
progress_label.anchor_point = (1.0, 1.0)
progress_label.anchored_position = (display.width // 2, display.height // 2 - 12)

hud_group.append(progress_label)
hud_group.append(cur_reading_label)
main_group.append(hud_group)


# =============================================================================
# KEY DERIVATION
# =============================================================================

def derive_key(range_str, b64=True):
    """SHA-256 of the sensor reading range string.

    b64=True  -> base64-encoded bytes  (Vigenere key)
    b64=False -> raw 32-byte digest    (AES-256 key)
    """
    h = hashlib.new("sha256")
    h.update(range_str.encode("utf-8"))
    if b64:
        return adafruit_binascii.b2a_base64(h.digest()).strip()
    else:
        return h.digest()


def get_range_string_from_sensor(_entry):
    """Return a bucketed range string like '22-23' for the given challenge entry.

    Reads whichever sensor attribute is named by entry['reading'] and buckets
    the (truncated-to-int) value using entry['precision_level'].
    """
    attr_name, _unit = READING_TYPES[_entry["reading"]]

    if attr_name != "CO2":
        # read CO2 to refresh other data types
        _ = sensor.CO2

    reading = int(getattr(sensor, attr_name))
    cur_reading_label.text = str(reading)
    precision_level = _entry["precision_level"]
    bucket = (reading // precision_level) * precision_level
    return f"{bucket}-{bucket + precision_level}"


# =============================================================================
# HASH VERIFICATION
# =============================================================================

def sha256_hex(data):
    """Return lowercase hex SHA-256 digest of *data* (bytes or str -> UTF-8)."""
    h = hashlib.new("sha256")
    if isinstance(data, str):
        h.update(data.encode("utf-8"))
    else:
        h.update(data)
    # Convert raw digest bytes to hex without binascii
    return "".join("{:02x}".format(b) for b in h.digest())


def verify(data, expected_hex):
    """Return True if SHA-256 of *data* matches *expected_hex*."""
    return sha256_hex(data) == expected_hex.lower()


# =============================================================================
# DECRYPTION
# =============================================================================

def vigenere_decrypt(ciphertext_str, key_bytes):
    """Vigenere decryption over printable ASCII (32-126).

    Characters outside that range pass through unchanged.
    """
    out = []
    key_len = len(key_bytes)
    key_idx = 0
    for ch in ciphertext_str:
        c = ord(ch)
        if ASCII_MIN <= c <= ASCII_MAX:
            k = key_bytes[key_idx % key_len]
            k_shifted = (k - ASCII_MIN) % ASCII_RANGE
            p = ((c - ASCII_MIN) - k_shifted) % ASCII_RANGE
            out.append(chr(p + ASCII_MIN))
            key_idx += 1
        else:
            out.append(ch)
    return "".join(out)


def try_decrypt_text(_entry, range_str):
    """Decrypt text and verify against the stored hash.

    Returns (success: bool, plaintext: str).
    plaintext is always returned so the display shows the attempt in progress
    (garbled text while the wrong sensor reading is active is part of the puzzle UX).
    """
    key_bytes = derive_key(range_str, b64=True)
    _plaintext = vigenere_decrypt(_entry["data"], key_bytes)
    _success = verify(_plaintext, _entry["sha256"])
    return _success, _plaintext


def try_decrypt_image(_entry, range_str, img_width, img_height,
                      encrypted_raw, pixel_start):
    """AES-CTR decrypt pixel data and verify against the stored hash.

    Returns (success: bool, decrypted: bytearray).
    decrypted is always returned so the bitmap updates on every reading change,
    letting the user see the image snap into focus at the correct sensor level.
    """
    key_bytes = derive_key(range_str, b64=False)
    pixel_data = encrypted_raw[pixel_start: pixel_start + img_width * img_height]
    _decrypted = bytearray(len(pixel_data))
    cipher = aesio.AES(key_bytes, aesio.MODE_CTR, IV=_entry["iv"])
    cipher.decrypt_into(pixel_data, _decrypted)
    _success = verify(_decrypted, _entry["sha256"])
    return _success, _decrypted


# =============================================================================
# CHALLENGE RENDERER
# =============================================================================

_image_cache = {}


def load_image_entry(_entry):
    """Read and parse an encrypted ABMP file. Returns a state dict."""
    filename = _entry["data"]
    if filename not in _image_cache:
        with open(filename, "rb") as f:
            raw = bytearray(f.read())
        _image_cache[filename] = raw

    raw = _image_cache[filename]
    if raw[0:4] != b"ABMP":
        raise ValueError(f"Not a valid ABMP file: {filename}")

    img_width, img_height, n_colors = struct.unpack_from("<HHH", raw, 4)
    palette_start = 10
    pixel_start = palette_start + n_colors * 3

    palette = Palette(n_colors)
    for i in range(n_colors):
        off = palette_start + i * 3
        r, g, b = raw[off], raw[off + 1], raw[off + 2]
        palette[i] = (r << 16) | (g << 8) | b

    bitmap = Bitmap(img_width, img_height, n_colors)
    return {
        "bitmap": bitmap,
        "palette": palette,
        "img_width": img_width,
        "img_height": img_height,
        "encrypted_raw": raw,
        "pixel_start": pixel_start,
    }


class ChallengeRenderer(Group):
    """Manages the content_group display for the currently active challenge."""

    def __init__(self):
        super().__init__()
        self._active_index = None
        self.text_widget = None
        self.image_state = None

        self.secret_message_text = TextBox(
                terminalio.FONT,
                display.width // 2 - 2,
                (display.height) // 2,
                align=TextBox.ALIGN_LEFT,
                scale=2
            )
        self.secret_message_text.anchor_point = (0, 0)
        self.secret_message_text.anchored_position = (2, 0)
        self.append(self.secret_message_text)
        self.secret_message_text.text = "Reading sensor..."

        self.secret_image_tilegrid = None

        self.prompt_text = Label(terminalio.FONT)
        self.prompt_text.anchor_point = (0, 1.0)
        self.prompt_text.anchored_position = (2, display.height)
        self.prompt_text.text = "[ press Boot btn ]"
        self.prompt_text.hidden = True
        self.append(self.prompt_text)

    def setup(self, index):
        """Prepare content_group for challenge *index* (no-op if already set up)."""
        if self._active_index == index:
            return

        if self.secret_image_tilegrid is not None and self.secret_image_tilegrid in self:
            self.remove(self.secret_image_tilegrid)

        self.text_widget = None
        self.image_state = None
        _entry = SEQUENCE[index]

        if _entry["type"] == "text":
            self.secret_message_text.hidden = False
            self.secret_message_text.text = "Reading sensor..."

        elif _entry["type"] == "image":
            state = load_image_entry(_entry)
            self.image_state = state
            self.secret_message_text.hidden = True

            self.secret_image_tilegrid = TileGrid(state["bitmap"], pixel_shader=state["palette"])
            # self.secret_image_tilegrid.transpose_xy = True
            self.append(self.secret_image_tilegrid)

        self._active_index = index

    def update_image(self, decrypted_pixels):
        """Blit already-decrypted pixel bytes into the bitmap."""
        _s = self.image_state
        bitmaptools.arrayblit(
            _s["bitmap"], decrypted_pixels,
            x1=0, y1=0, x2=_s["img_width"], y2=_s["img_height"],
        )


renderer = ChallengeRenderer()
main_group.append(renderer)


# =============================================================================
# HUD + COMPLETION
# =============================================================================

def update_hud(_current_index, _total):
    """Update the top progress bar label."""
    label = f"{_current_index + 1}/{_total}"
    if progress_label.text != label:
        progress_label.text = label


def show_completion_screen():
    """Replace challenge content with a 'you win' message and halt."""
    while len(renderer):
        renderer.pop()

    fin = TextBox(
        terminalio.FONT,
        display.width // 2,
        (display.height - 16) // 2,
        align=TextBox.ALIGN_CENTER,
        scale=2
    )
    fin.anchor_point = (0, 0)
    fin.anchored_position = (0, 0)
    fin.text = "All secrets revealed.\nGood job!"

    renderer.append(fin)
    hud_group.hidden = True
    while True:
        pass  # halt / wait forever


# =============================================================================
# MAIN LOOP
# =============================================================================

current_index = 0
old_range = ""
total = len(SEQUENCE)
challenge_solved = False  # True while waiting for the user to press the button

last_sensor_read_time = 0
cur_cache_key = None
while True:
    entry = SEQUENCE[current_index]
    now = time.monotonic()
    if now - last_sensor_read_time > SENSOR_READ_COOLDOWN and not challenge_solved:
        try:
            cur_range = get_range_string_from_sensor(entry)
        except OSError as e:
            print(e, "retrying after cooldown")
            cur_range = cur_cache_key.split(":")[-1]
        last_sensor_read_time = now
    else:
        cur_range = cur_cache_key.split(":")[-1]
    # Include reading type in cache key so changing challenge boundaries
    # don't accidentally match a previous challenge's bucket value.
    cur_cache_key = f"{entry['reading']}:{cur_range}"

    renderer.setup(current_index)
    update_hud(current_index, total)

    # -----------------------------------------------------------------
    # While a challenge is solved-but-not-yet-confirmed, keep updating
    # the display with the latest decryption (sensor reading may still drift) but
    # wait for a button press before advancing.
    # -----------------------------------------------------------------
    if challenge_solved:
        # renderer.show_solved_prompt()
        btn_cur_val = btn.value
        if not btn_cur_val and btn_prev_value:
            print(f"Challenge {current_index + 1} confirmed by button press — advancing.")
            current_index += 1
            challenge_solved = False
            old_range = ""  # force re-decrypt immediately on next loop

            if current_index >= total:
                update_hud(total, total)
                show_completion_screen()
        btn_prev_value = btn_cur_val
        continue  # skip normal decrypt logic while waiting for button

    # -----------------------------------------------------------------
    # Normal path: decrypt on every reading-range change and check for a solve.
    # -----------------------------------------------------------------
    now = time.monotonic()
    if cur_cache_key != old_range:
        last_sensor_read_time = now
        unit = READING_TYPES[entry["reading"]][1]
        print(f"[{current_index + 1}/{total}] {entry['reading']} range: {cur_range} {unit}")
        old_range = cur_cache_key

        if entry["type"] == "text":
            success, plaintext = try_decrypt_text(entry, cur_range)
            renderer.secret_message_text.text = plaintext

            if success:
                print(f"Challenge {current_index + 1} SOLVED (text): {plaintext}")
                cur_reading_label.text = "*" + cur_reading_label.text
                challenge_solved = True

        elif entry["type"] == "image":
            s = renderer.image_state
            success, decrypted = try_decrypt_image(
                entry, cur_range,
                s["img_width"], s["img_height"],
                s["encrypted_raw"], s["pixel_start"],
            )
            renderer.update_image(decrypted)

            if success:
                print(f"Challenge {current_index + 1} SOLVED (image)")
                cur_reading_label.text = "*" + cur_reading_label.text
                challenge_solved = True
