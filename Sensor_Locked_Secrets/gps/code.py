import hashlib
import struct
import time

import board
import busio
import bitmaptools
import aesio
from displayio import Group, TileGrid, Palette, Bitmap
import supervisor
import terminalio
from adafruit_display_text.text_box import TextBox
from adafruit_display_text.bitmap_label import Label
import adafruit_binascii
import adafruit_gps
from digitalio import DigitalInOut, Direction, Pull

# =============================================================================
# USER CONFIGURATION
# =============================================================================

# --- Sequence of challenges ---
# Each entry is a dict with the following keys:
#
#   type   : "text"  -> Vigenère-encrypted ciphertext
#            "image" -> AES-CTR-encrypted .abmp image file
#
#   data   : (text)  the ciphertext string
#            (image) filename of the .abmp.enc file
#
#   sha256 : hex-encoded SHA-256 digest used to confirm correct decryption
#            - text  -> SHA-256 of the plaintext string encoded as UTF-8
#            - image -> SHA-256 of the raw decrypted pixel-data bytes
#            Generate these offline with the helper snippet at the bottom
#            of this file.
#
#   reading     : which sensor data type drives this challenge. One of:
#                 "gps" -> gps.latitude,gps.longitude (coordinates, string)
#
#   precision_level : Controls how big the "unlock" target area is.
#                     Approximate sizes at the equator:
#                     2 -> ~1.1 km    (city block scale)
#                     3 -> ~110 m     (large building)
#                     4 -> ~11 m      (room scale)
#                 Must match the precision used at encryption time.
#
#   iv     : (image only) 16-byte AES initialisation vector matching
#            the one used during encryption. Omit or set None for text.
#
# Challenges must be worked through in order: solve #0 to unlock #1, etc.
# The key for each challenge is derived from the GPS coordinates at the
# target location. The user must physically be there to decrypt correctly.

SEQUENCE = [
    # Add more entries here...
]

# --- Display rotation (degrees) ---
DISPLAY_ROTATION = 180

# =============================================================================
# END OF USER CONFIGURATION — do not edit below unless you know what you're doing
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
    if _entry["type"] == "image" and not _entry.get("iv"):
        raise ValueError(f"SEQUENCE[{_i}]: image entries require an 'iv'.")

# Printable ASCII constants (text Vigenère)
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
btn_prev_value = btn.value
btn_last_change_time = time.monotonic()

# =============================================================================
# GPS SETUP
# =============================================================================

uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=10)
gps = adafruit_gps.GPS(uart, debug=False)
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
gps.send_command(b"PMTK220,1000")

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

def derive_key(coord_str, b64=True):
    """SHA-256 hash of the GPS coordinate string.

    b64=True  -> base64-encoded bytes  (Vigenère key)
    b64=False -> raw 32-byte digest    (AES-256 key)
    """
    h = hashlib.new("sha256")
    h.update(coord_str.encode("utf-8"))
    if b64:
        return adafruit_binascii.b2a_base64(h.digest()).strip()
    else:
        return h.digest()


def get_coord_string():
    """Return "<lat>,<lon>" at COORD_PRECISION decimal places, or None if no fix."""
    if not gps.has_fix or gps.latitude is None or gps.longitude is None:
        return None

    precision_level = entry["precision_level"]
    _coord_str = f"{gps.latitude:.{precision_level}f},{gps.longitude:.{precision_level}f}"
    cur_reading_label.text = _coord_str
    return _coord_str


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


def try_decrypt_text(_entry, coord_str):
    """Decrypt text and verify against the stored hash.

    Returns (success: bool, plaintext: str).
    Plaintext is always returned so the display shows the garbled attempt
    while the user is at the wrong location — part of the puzzle UX.
    """
    key_bytes = derive_key(coord_str, b64=True)
    _plaintext = vigenere_decrypt(_entry["data"], key_bytes)
    _success = verify(_plaintext, _entry["sha256"])
    return _success, _plaintext


def try_decrypt_image(_entry, coord_str, img_width, img_height,
                      encrypted_raw, pixel_start):
    """AES-CTR decrypt pixel data and verify against the stored hash.

    Returns (success: bool, decrypted: bytearray).
    Decrypted is always returned so the bitmap updates on every coordinate
    change, letting the user see the image snap into focus at the right spot.
    """
    key_bytes = derive_key(coord_str, b64=False)
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
    """Read and parse an encrypted ABMP file. Returns a state dict.

    The file is cached in memory so subsequent challenges that reuse the
    same filename don't hit the filesystem again.
    """
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
        self.secret_message_text.text = "Waiting for fix..."

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
    """Replace content_group with a 'you win' message and halt."""
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
    while True:
        pass  # halt / wait forever


# =============================================================================
# MAIN LOOP
# =============================================================================

current_index = 0
old_coord = ""
total = len(SEQUENCE)
challenge_solved = False  # True while waiting for the user to press the button

while True:
    gps.update()

    entry = SEQUENCE[current_index]
    renderer.setup(current_index)
    update_hud(current_index, total)

    now = time.monotonic()
    cur_coord = get_coord_string()  # None until GPS has a fix

    # -----------------------------------------------------------------
    # While a challenge is solved-but-not-yet-confirmed, keep updating
    # the display with the latest decryption (GPS may still drift slightly)
    # but wait for a button press before advancing.
    # -----------------------------------------------------------------
    if challenge_solved:
        btn_cur_val = btn.value
        if not btn_cur_val and btn_prev_value:
            print(f"Challenge {current_index + 1} confirmed by button press — advancing.")
            current_index += 1
            challenge_solved = False
            old_coord = ""  # force re-decrypt immediately on next loop

            if current_index >= total:
                update_hud(total, total)
                show_completion_screen()
        btn_prev_value = btn_cur_val
        continue  # skip normal decrypt logic while waiting for button

    # -----------------------------------------------------------------
    # No GPS fix — show waiting message and loop.
    # -----------------------------------------------------------------
    if cur_coord is None:
        if old_coord != "":
            # Fix was just lost
            if entry["type"] == "text":
                renderer.secret_message_text.text = "Waiting for fix..."
            old_coord = ""
        continue

    # -----------------------------------------------------------------
    # Normal path: decrypt on every coordinate change and check for a solve.
    # -----------------------------------------------------------------
    if cur_coord != old_coord:
        print(f"[{current_index + 1}/{total}] coord: {cur_coord}")
        old_coord = cur_coord

        if entry["type"] == "text":
            success, plaintext = try_decrypt_text(entry, cur_coord)
            renderer.secret_message_text.text = plaintext

            if success:
                print(f"Challenge {current_index + 1} SOLVED (text): {plaintext}")
                challenge_solved = True

        elif entry["type"] == "image":
            s = renderer.image_state
            success, decrypted = try_decrypt_image(
                entry, cur_coord,
                s["img_width"], s["img_height"],
                s["encrypted_raw"], s["pixel_start"],
            )
            renderer.update_image(decrypted)

            if success:
                print(f"Challenge {current_index + 1} SOLVED (image)")
                challenge_solved = True
