# The MIT License (MIT)
#
# Copyright (c) 2020 Jeff Epler for Adafruit Industries LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
jeplayer - main file

This is an MP3 player for the PyGamer with CircuitPython.

See README.md for more information.
"""

import gc
import os
import random
import time

import adafruit_bitmap_font.bitmap_font
import adafruit_display_text.label
from adafruit_progressbar import ProgressBar
import adafruit_sdcard
import analogjoy
import audioio
import audiomp3
import board
import busio
import digitalio
import displayio
import terminalio
import gamepadshift
import icons
import neopixel
import repeat
import storage
from micropython import const

def clear_display():
    """Display nothing"""
    board.DISPLAY.show(displayio.Group(max_size=1))

clear_display()

# pylint: disable=invalid-name
def px(x, y):
    """Convert a raw value (x/y) to a pixel value, clamping negative values"""
    return 0 if x <= 0 else round(x / y)
# pylint: enable=invalid-name

(ICON_PLAY, ICON_PAUSE, ICON_STOP, ICON_PREV, ICON_NEXT, ICON_REPEAT,
 ICON_SHUFFLE, ICON_FOLDERNEXT) = range(8)

class PlaybackDisplay:
    """Manage display during playback"""
    def __init__(self):
        self.group = displayio.Group(max_size=4)
        self.glyph_width, self.glyph_height = font.get_bounding_box()[:2]
        self.pbar = ProgressBar(0, 0, board.DISPLAY.width,
                                self.glyph_height, bar_color=0x0000ff,
                                outline_color=0x333333, stroke=1)
        self.iconbar = icons.IconBar()
        self.iconbar.group.y = 112
        for i in range(5, 8):
            self.iconbar.icons[i].x += 32
        self.label = adafruit_display_text.label.Label(font, line_spacing=1.0,
                                                       max_glyphs=256)
        self.label.y = 6
        self._bitmap_filename = None
        self._fallback_bitmap = ["/rsrc/background.bmp"]
        self.set_bitmap([]) # Must be first!
        self.group.append(self.pbar)
        self.group.append(self.label)
        self.group.append(self.iconbar.group)
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 5)
        self.pixels.auto_write = False
        self.pixels.fill(0)
        self.pixels.show()
        self.paused = False
        self.next_choice = 0

    @property
    def text(self):
        """The text shown at the top of the display.  Usually 2 lines."""
        return self._text

    @text.setter
    def text(self, text):
        if len(text) > 256:
            text = text[:256]
        self._text = text
        self.label.text = text

    @property
    def progress(self):
        """The fraction of progress through the current track"""
        return self.pbar.progress

    @progress.setter
    def progress(self, frac):
        self.pbar.progress = frac

    def set_bitmap(self, candidates):
        """Find and use a background from among candidates, or else the fallback bitmap"""
        for i in candidates + self._fallback_bitmap:
            if i == self._bitmap_filename:
                return # Already loaded
            try:
                bitmap_file = open(i, 'rb')
            except OSError:
                continue
            bitmap = displayio.OnDiskBitmap(bitmap_file)
            self._bitmap_filename = i
            # Create a TileGrid to hold the bitmap
            self.tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())

            # Add the TileGrid to the Group
            if len(self.group) == 0:
                self.group.append(self.tile_grid)
            else:
                self.group[0] = self.tile_grid
            self.tile_grid.x = (160 - bitmap.width) // 2
            self.tile_grid.y = self.glyph_height*2 + max(0, (96 - bitmap.height) // 2)
            break

    @property
    def rms(self):
        """The RMS audio level, used to control the neopixel vu meter"""
        return self._rms

    @rms.setter
    def rms(self, value):
        self._rms = value
        self.pixels[0] = (20, 0, 0) if value > 20 else (px(value, 1), 0, 0)
        self.pixels[1] = (20, 0, 0) if value > 40 else (px(value - 20, 1), 0, 0)
        self.pixels[2] = (20, 0, 0) if value > 80 else (px(value - 40, 2), 0, 0)
        self.pixels[3] = (20, 0, 0) if value > 160 else (px(value - 80, 4), 0, 0)
        self.pixels[4] = (20, 0, 0) if value > 320 else (px(value - 160, 8), 0, 0)
        self.pixels.show()

    # pylint: disable=too-many-branches
    def press(self, idx):
        """Do the action for the current icon"""
        selected = self.iconbar.selected
        if selected in (ICON_PLAY, ICON_PAUSE):  # Play/Pause
            if self.paused:
                self.resume()
            else:
                self.pause()
            self.iconbar.select(not self.paused)
        elif selected == ICON_STOP:
            self.iconbar.deactivate(ICON_FOLDERNEXT)
            return (-1,)
        elif selected == ICON_PREV:
            if self.shuffle:
                return (None,)
            return (idx-1,)
        elif selected == ICON_NEXT:
            if self.shuffle:
                return (None,)
            return (idx+1,)
        elif selected == ICON_SHUFFLE:
            self.iconbar.toggle(selected)
            if self.iconbar.active[ICON_SHUFFLE]:
                self.iconbar.deactivate(ICON_REPEAT)
                self.iconbar.deactivate(ICON_FOLDERNEXT)
        elif selected == ICON_REPEAT:
            self.iconbar.toggle(selected)
            if self.iconbar.active[ICON_REPEAT]:
                self.iconbar.deactivate(ICON_SHUFFLE)
                self.iconbar.deactivate(ICON_FOLDERNEXT)
        elif selected == ICON_FOLDERNEXT:
            self.iconbar.toggle(selected)
            if self.iconbar.active[ICON_FOLDERNEXT]:
                self.iconbar.deactivate(ICON_REPEAT)
                self.iconbar.deactivate(ICON_SHUFFLE)
        return None

    def move(self, direction):
        """Switch the current icon in the given direction"""
        self.iconbar.select((self.iconbar.selected + direction) % 8)

    def play(self, stream):
        """Starting playing a stream on the speaker"""
        speaker.play(stream)
        self.paused = False
        self.iconbar.set_active(0, not self.paused)
        self.iconbar.set_active(1, self.paused)

    def pause(self):
        """Pause the stream"""
        speaker.pause()
        self.paused = True
        self.iconbar.set_active(0, not self.paused)
        self.iconbar.set_active(1, self.paused)

    def resume(self):
        """Resume the stream"""
        speaker.resume()
        self.paused = False
        self.iconbar.set_active(0, not self.paused)
        self.iconbar.set_active(1, self.paused)

    @property
    def shuffle(self):
        """Whether to shuffle the playlist"""
        return self.iconbar.active[ICON_SHUFFLE]
    @property
    def repeat(self):
        """Whether to repeat the playlist"""
        return self.iconbar.active[ICON_REPEAT]
    @property
    def auto_next(self):
        """Whether to play all folders"""
        return self.iconbar.active[ICON_FOLDERNEXT]

    @staticmethod
    def has_any_mp3s(folder):
        """True if the folder contains at least one item ending in .mp3"""
        return any(fn.lower().endswith(".mp3") for fn in os.listdir(folder))

    def choose_folder(self, base='/sd'):
        """Let the user choose a folder within a base directory"""
        all_folders = (m for m in os.listdir(base)
                       if not m.startswith('.') and isdir(join(base, m)))
        all_folders = sorted(f for f in all_folders if self.has_any_mp3s(join(base, f)))
        choices = ['Surprise Me'] + all_folders

        if playback_display.auto_next:
            idx = self.next_choice
        else:
            idx = menu_choice(choices,
                              BUTTON_START | BUTTON_A | BUTTON_B | BUTTON_SEL,
                              sel_idx=self.next_choice,
                              text_font=terminalio.FONT)
        clear_display()
        self.next_choice = idx
        if idx >= 1:
            result = all_folders[idx-1]
            self.next_choice = idx+1
            if self.next_choice == len(choices):
                self.next_choice = 1   # Go to first folder, not "surprise me"
        else:
            result = random.choice(all_folders)
        return join(base, result)

# pylint: disable=invalid-name
enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True
speaker = audioio.AudioOut(board.SPEAKER, right_channel=board.A1)
mp3stream = audiomp3.MP3Decoder(open("/rsrc/splash.mp3", "rb"))
speaker.play(mp3stream)

font = adafruit_bitmap_font.bitmap_font.load_font("rsrc/5x8.bdf")
playback_display = PlaybackDisplay()
board.DISPLAY.show(playback_display.group)
font.load_glyphs(range(32, 128))

BUTTON_SEL = const(8)
BUTTON_START = const(4)
BUTTON_A = const(2)
BUTTON_B = const(1)


joystick = analogjoy.AnalogJoystick()

up_key = repeat.KeyRepeat(lambda: joystick.up, rate=0.2)
down_key = repeat.KeyRepeat(lambda: joystick.down, rate=0.2)
left_key = repeat.KeyRepeat(lambda: joystick.left, rate=0.2)
right_key = repeat.KeyRepeat(lambda: joystick.right, rate=0.2)

buttons = gamepadshift.GamePadShift(digitalio.DigitalInOut(board.BUTTON_CLOCK),
                                    digitalio.DigitalInOut(board.BUTTON_OUT),
                                    digitalio.DigitalInOut(board.BUTTON_LATCH))
# pylint: enable=invalid-name

def mount_sd():
    """Mount the SD card"""
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    sd_cs = digitalio.DigitalInOut(board.SD_CS)
    sdcard = adafruit_sdcard.SDCard(spi, sd_cs, baudrate=6000000)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")

def join(*args):
    """Like posixpath.join"""
    return "/".join(args)

def shuffle(seq):
    """Shuffle a sequence using the Fisher-Yates shuffle algorithm (like random.shuffle)"""
    for i in range(len(seq)-2):
        j = random.randint(i, len(seq)-1)
        seq[i], seq[j] = seq[j], seq[i]

# pylint: disable=too-many-locals,too-many-statements
def menu_choice(seq, button_ok, button_cancel=0, *, sel_idx=0, text_font=font):
    """Display a menu and allow a choice from it"""
    gc.collect()
    board.DISPLAY.auto_refresh = True
    scroll_idx = 0
    glyph_width, glyph_height = text_font.get_bounding_box()[:2]
    num_rows = min(len(seq), board.DISPLAY.height // glyph_height)
    max_glyphs = board.DISPLAY.width // glyph_width
    palette = displayio.Palette(2)
    palette[0] = 0
    palette[1] = 0xffffff
    labels = [displayio.TileGrid(text_font.bitmap, pixel_shader=palette,
                                 width=max_glyphs+1, height=1,
                                 tile_width=glyph_width,
                                 tile_height=glyph_height)
              for i in range(num_rows)]
    terminals = [terminalio.Terminal(li, text_font) for li in labels]
    cursor = adafruit_display_text.label.Label(text_font, max_glyphs=1, color=0xddddff)
    base_y = 0
    caret_offset = glyph_height//2-1
    scene = displayio.Group(max_size=len(labels) + 1)
    for i, label in enumerate(labels):
        label.x = round(glyph_width * 1.5)
        label.y = base_y + glyph_height * i
        scene.append(label)
    cursor.x = 0
    cursor.y = caret_offset
    cursor.text = ">"
    scene.append(cursor)

    last_scroll_idx = max(0, len(seq) - num_rows)

    board.DISPLAY.show(scene)
    buttons.get_pressed() # Clear out anything from before now
    i = 0
    old_scroll_idx = None

    while True:
        enable.value = speaker.playing
        pressed = buttons.get_pressed()
        if button_cancel and (pressed & button_cancel):
            return -1
        if pressed & button_ok:
            return sel_idx

        joystick.poll()
        if up_key.value:
            sel_idx -= 1
        if down_key.value:
            sel_idx += 1

        sel_idx = min(len(seq)-1, max(0, sel_idx))

        if scroll_idx > sel_idx or scroll_idx + num_rows <= sel_idx:
            scroll_idx = sel_idx - num_rows // 2
        scroll_idx = min(last_scroll_idx, max(0, scroll_idx))

        board.DISPLAY.auto_refresh = False
        if old_scroll_idx != scroll_idx:
            for i in range(scroll_idx, scroll_idx + num_rows):
                j = i - scroll_idx
                new_text = ''
                if i < len(seq):
                    new_text = seq[i][:max_glyphs]
                terminals[j].write('\r\033[K')
                terminals[j].write(new_text)
        cursor.y = caret_offset + base_y + glyph_height * (sel_idx - scroll_idx)
        board.DISPLAY.auto_refresh = True
        old_scroll_idx = scroll_idx

        time.sleep(1/20)
# pylint: enable=too-many-locals

S_IFDIR = const(16384)
def isdir(x):
    """Return True if 'x' is a directory"""
    return os.stat(x)[0] & S_IFDIR

def wait_no_button_pressed():
    """Wait until no button is pressed"""
    while buttons.get_pressed():
        time.sleep(1/20)

def change_stream(filename):
    """Change the global MP3Decoder object to play a new file"""
    old_stream = mp3stream.file
    mp3stream.file = open(filename, "rb")
    old_stream.close()
    return mp3stream.file

def play_one_file(idx, filename, folder, title, playlist_size):
    """Play one file, reacting to user input"""
    board.DISPLAY.auto_refresh = False

    playback_display.set_bitmap([
        filename.rsplit('.', 1)[0] + ".bmp",
        filename.rsplit('/', 1)[0] + ".bmp",
        filename.rsplit('/', 1)[0] + "/cover.bmp",
    ])

    playback_display.text = "%s\n%s" % (folder, title)

    board.DISPLAY.refresh()

    result = None
    wait_no_button_pressed()
    file_size = os.stat(filename)[6]
    mp3file = change_stream(filename)
    playback_display.play(mp3stream)
    board.DISPLAY.auto_refresh = True
    last_pressed = buttons.get_pressed()

    while speaker.playing:

        # pylint: disable=no-member
        if gc.mem_free() < 4096:
            gc.collect()

        playback_display.rms = mp3stream.rms_level
        playback_display.progress = mp3file.tell() / file_size

        joystick.poll()
        if left_key.value:
            playback_display.move(-1)
        if right_key.value:
            playback_display.move(1)

        pressed = buttons.get_pressed()
        rising_edge = pressed & ~last_pressed
        last_pressed = pressed

        if rising_edge:
            return_now = playback_display.press(idx)
            wait_no_button_pressed()
            if return_now:
                result = return_now[0]
                break

    if result is None:
        if playback_display.shuffle:
            if playback_display.shuffle:
                #  Choose a random integer .. except for this one
                result = random.randrange(playlist_size-1)
                if result >= idx:
                    result += 1
        else:
            result = (idx + 1)
    speaker.stop()
    playback_display.rms = 0

    gc.collect()

    return result

def play_all(playlist, *, folder='', trim=0, location='/sd'):
    """Play everything in 'playlist', which is relative to 'location'.

    'folder' is a display name for the user."""
    i = 0
    board.DISPLAY.show(playback_display.group)
    while 0 <= i < len(playlist):
        filename = playlist[i]
        i = play_one_file(i, join(location, filename), folder, filename[trim:-4], len(playlist))
        if i == -1:
            break
        if playback_display.repeat and i == len(playlist):
            i = 0
    speaker.stop()
    clear_display()

def longest_common_prefix(seq):
    """Find the longest common prefix between all items in sequence"""
    seq0 = seq[0]
    for i, seq0i in enumerate(seq0):
        for j in seq:
            if len(j) < i or j[i] != seq0i:
                return i
    return len(seq0)

def play_folder(location):
    """Play everything within a given folder"""
    playlist = [d for d in os.listdir(location) if d.lower().endswith('.mp3')]
    if not playlist:
        # hmm, no mp3s in a folder?  Well, don't crash okay?
        del playlist
        gc.collect()
        return
    playlist.sort()
    trim = longest_common_prefix(playlist)
    enable.value = True
    play_all(playlist, folder=location.split('/')[-1], trim=trim, location=location)
    enable.value = False


def main():
    """The main function of the player"""
    try:
        mount_sd()
    except OSError as detail:
        text = "%s\n\nInsert or re-seat\nSD card\nthen press reset" % detail.args[0]
        error_text = adafruit_display_text.label.Label(font, text=text)
        error_text.x = 8
        error_text.y = board.DISPLAY.height // 2
        g = displayio.Group()
        g.append(error_text)
        board.DISPLAY.show(g)

        while True:
            time.sleep(1)

    while True:
        folder = playback_display.choose_folder()
        play_folder(folder)
main()
