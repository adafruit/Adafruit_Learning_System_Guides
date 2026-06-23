# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython Chiptune Player
Uses AY8912 emulator helper library to play VGM files
through I2S DAC. TFT FeatherWing for touchscreen GUI"""
import time
import os
import gc
import board
import displayio
import fourwire
import storage
import sdcardio
from adafruit_hx8357 import HX8357
import simpleio
from adafruit_button import Button
import adafruit_tsc2007
import terminalio
from adafruit_display_text import label as text_label
import audiobusio
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
)
from adafruit_ay8912.ay8912_emulator import AY8912
from adafruit_ay8912.vgm_player import VGMFile

displayio.release_displays()
spi = board.SPI()
SD_CS = board.D5
VGM_EXTS = (".vgm", ".vgz")

playlist = []
for attempt in range(3):
    try:
        sdcard = sdcardio.SDCard(spi, SD_CS)
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")
        playlist = sorted(
            (n for n in os.listdir("/sd") if n.lower().endswith(VGM_EXTS)),
            key=lambda n: n.lower(),
        )
        print(f"Found {len(playlist)} VGM file(s) on SD")
        break
    except OSError as exc:
        print(f"SD init attempt {attempt + 1} failed:", exc)
        time.sleep(0.25)
else:
    print("SD card not available - running with an empty playlist.")

# init display after sd card
tft_cs = board.D9
tft_dc = board.D10
display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = HX8357(display_bus, width=320, height=480, rotation=90)  # portrait
SCREEN_W = 320
SCREEN_H = 480

i2c = board.I2C()
tsc = adafruit_tsc2007.TSC2007(i2c, invert_x=True, invert_y=True)

audio = audiobusio.I2SOut(board.A1, board.A2, board.A3)

# touch screen buttons
OUTLINE = 0xFF00FF
LABEL_COLOR = 0x000000
# pylint: disable=global-statement, too-many-branches
def make_button(action, x, y, w, h, label, fill, label_color=LABEL_COLOR):
    """Build a Button and tag it with the action it triggers."""
    b = Button(
        x=x, y=y, width=w, height=h,
        style=Button.ROUNDRECT,
        fill_color=fill,
        outline_color=OUTLINE,
        label=label,
        label_font=terminalio.FONT,
        label_color=label_color,
    )
    return b, action

def fmt_time(seconds):
    """Seconds -> 'M:SS'."""
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"

def fit(text, maxchars):
    """Truncate long strings so they don't overrun the screen."""
    if len(text) > maxchars:
        return text[:maxchars - 3] + "..."
    return text


# ====================================================================
#  PLAY VIEW
# ====================================================================
play_group = displayio.Group()

# Repeat toggle, top-left. Its "selected" state is the lit state:
# off -> black body + cyan text; on -> cyan body + black text.
repeat_button = Button(
    x=6, y=8, width=76, height=34,
    style=Button.ROUNDRECT,
    fill_color=0x000000, outline_color=OUTLINE,
    label="REPEAT", label_font=terminalio.FONT, label_color=0x00FFFF,
    selected_fill=0x00FFFF, selected_label=0x000000,
)
play_group.append(repeat_button)

# Track info, centered in the open top area (filled in by load_track).
NP_X = SCREEN_W // 2
title_label = text_label.Label(terminalio.FONT, text="(no track)", color=0x00FFFF,
                               scale=2, anchor_point=(0.5, 0.5), anchored_position=(NP_X, 150))
author_label = text_label.Label(terminalio.FONT, text="", color=0xFFFF00,
                                anchor_point=(0.5, 0.5), anchored_position=(NP_X, 182))
game_label = text_label.Label(terminalio.FONT, text="", color=0xFF00FF,
                              anchor_point=(0.5, 0.5), anchored_position=(NP_X, 204))
play_group.append(title_label)
play_group.append(author_label)
play_group.append(game_label)

# Progress bar + time readout.
BAR_W, BAR_H = 288, 24
BAR_X = (SCREEN_W - BAR_W) // 2
BAR_Y = 360
progress_bar = HorizontalProgressBar(
    (BAR_X, BAR_Y), (BAR_W, BAR_H),
    min_value=0.0, max_value=1.0, value=0.0,
    bar_color=0x00FFFF, outline_color=0xFF00FF, fill_color=0x000000,
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
play_group.append(progress_bar)
time_label = text_label.Label(terminalio.FONT, text="0:00 / 0:00", color=0x00FFFF,
                              anchor_point=(1.0, 1.0), anchored_position=(BAR_X + BAR_W, BAR_Y - 4))
play_group.append(time_label)

# Transport row: STOP  <<  PLAY/PAUSE  >>  MENU
ROW_Y = 400
BTN_H = 55
PLAY_W = 84
CTRL_W = 50
GAP = 6
play_x = (SCREEN_W - PLAY_W) // 2
rew_x = play_x - GAP - CTRL_W
stop_x = rew_x - GAP - CTRL_W
ffwd_x = play_x + PLAY_W + GAP
menu_x = ffwd_x + CTRL_W + GAP

play_buttons = [repeat_button]
play_actions = ["repeat"]
for btn, act in (
    make_button("stop", stop_x, ROW_Y, CTRL_W, BTN_H, "STOP", 0xFF0000),
    make_button("prev", rew_x, ROW_Y, CTRL_W, BTN_H, "<<", 0xFF00FF),
    make_button("play", play_x, ROW_Y, PLAY_W, BTN_H, "PLAY", 0x00FFFF),
    make_button("next", ffwd_x, ROW_Y, CTRL_W, BTN_H, ">>", 0xFFFF00),
    make_button("show_menu", menu_x, ROW_Y, CTRL_W, BTN_H, "MENU", 0x000000, 0xFFFFFF),
):
    play_group.append(btn)
    play_buttons.append(btn)
    play_actions.append(act)
play_button = play_buttons[3]   # the PLAY/PAUSE button (for label toggling)

# ====================================================================
#  MENU VIEW  (for selecting tracks)
# ====================================================================
menu_group = displayio.Group()

MENU_X, MENU_W = 10, 300
MENU_ROW_H, MENU_ROW_GAP, MENU_TOP = 38, 4, 8
PER_PAGE = 9

# Persistent bottom nav row: [<]  NOW PLAYING  [>]
NAV_Y, NAV_H = 420, 52
PAGE_W = 56
prevpage_btn, _ = make_button("page_prev", MENU_X, NAV_Y, PAGE_W, NAV_H, "<", 0x000000, 0x00FFFF)
np_btn, _ = make_button("show_play", MENU_X + PAGE_W + GAP, NAV_Y,
                        MENU_W - 2 * (PAGE_W + GAP), NAV_H, "NOW PLAYING", 0x00FFFF)
nextpage_btn, _ = make_button("page_next", MENU_X + MENU_W - PAGE_W, NAV_Y,
                              PAGE_W, NAV_H, ">", 0x000000, 0x00FFFF)
for btn in (prevpage_btn, np_btn, nextpage_btn):
    menu_group.append(btn)

page_label = text_label.Label(terminalio.FONT, text="", color=0x888893,
                              anchor_point=(0.5, 0.5), anchored_position=(NP_X, 404))
menu_group.append(page_label)

if not playlist:
    menu_group.append(text_label.Label(
        terminalio.FONT, text="No VGM files found on /sd", color=0xFFFFFF,
        anchor_point=(0.5, 0.5), anchored_position=(NP_X, 180)))

file_buttons = []
menu_page = 0
menu_buttons = [prevpage_btn, np_btn, nextpage_btn]
menu_actions = ["page_prev", "show_play", "page_next"]

# ====================================================================
#  AY8912 emulator setup
# ====================================================================
ay = AY8912(sample_rate=22050, clock_rate=1773400)
ay.begin(audio)

vgm = None
song_duration = 0.0
current_index = 0
is_playing = False
is_paused = False
repeat_mode = False
last_progress = -1.0
last_sec = -1

current_view = "play"
wait_release = False

def build_menu_page(page):
    """(Re)build the file buttons for the requested page, with wraparound."""
    global menu_page, menu_buttons, menu_actions, file_buttons
    if not playlist:
        return
    num_pages = (len(playlist) + PER_PAGE - 1) // PER_PAGE
    menu_page = page % num_pages
    for fb in file_buttons:           # clear the previous page
        menu_group.remove(fb)
    file_buttons = []
    fb_actions = []
    gc.collect()
    start = menu_page * PER_PAGE
    for slot, idx in enumerate(range(start, min(start + PER_PAGE, len(playlist)))):
        y = MENU_TOP + slot * (MENU_ROW_H + MENU_ROW_GAP)
        b, _ = make_button(idx, MENU_X, y, MENU_W, MENU_ROW_H,
                             fit(playlist[idx], 30), 0x000000, 0x00FFFF)
        menu_group.append(b)
        file_buttons.append(b)
        fb_actions.append(idx)
    menu_buttons = file_buttons + [prevpage_btn, np_btn, nextpage_btn]
    menu_actions = fb_actions + ["page_prev", "show_play", "page_next"]
    page_label.text = f"page {menu_page + 1} / {num_pages}"


def load_track(track_index):
    """Load (but don't start) the track at playlist index"""
    global vgm, song_duration, current_index, last_progress, last_sec
    if not playlist:
        return
    current_index = track_index % len(playlist)
    gc.collect()
    display.auto_refresh = False
    try:
        vgm = VGMFile("/sd/" + playlist[current_index])
    finally:
        display.auto_refresh = True
    ay.clock_rate = vgm.clock_hz
    song_duration = vgm.duration
    title_label.text = fit(vgm.title or playlist[current_index], 24)
    author_label.text = fit(vgm.author, 40)
    game_label.text = fit(vgm.game, 40)
    progress_bar.value = 0.0
    last_progress = -1.0
    last_sec = -1
    time_label.text = f"{fmt_time(0)} / {fmt_time(song_duration)}"

def play_track(track_index):
    """Load track index and start it from the beginning."""
    global is_playing, is_paused
    if not playlist:
        return
    load_track(track_index)
    if vgm is None:
        return
    vgm.play(ay)
    is_playing = True
    is_paused = False
    play_button.label = "PAUSE"

def change_track(delta):
    """Step the playlist with wraparound and play."""
    if not playlist:
        return
    play_track((current_index + delta) % len(playlist))

def show_menu():
    global current_view, wait_release
    current_view = "menu"
    display.root_group = menu_group
    wait_release = True

def show_play():
    global current_view, wait_release
    current_view = "play"
    display.root_group = play_group
    wait_release = True

def dispatch(action):
    """Run once per fresh button tap (rising edge)."""
    global is_playing, is_paused, repeat_mode, last_progress, last_sec
    if action == "show_menu":
        show_menu()
    elif action == "show_play":
        show_play()
    elif action == "page_prev":
        build_menu_page(menu_page - 1)
    elif action == "page_next":
        build_menu_page(menu_page + 1)
    elif action == "repeat":
        repeat_mode = not repeat_mode
        repeat_button.selected = repeat_mode      # lit when on
    elif isinstance(action, int):         # a file was picked in the menu
        play_track(action)
        show_play()
    elif action == "play":
        if vgm is None:
            return
        if not is_playing and not is_paused:
            vgm.play(ay)
            is_playing = True
            play_button.label = "PAUSE"
            last_progress = -1.0
            last_sec = -1
        elif is_playing:
            is_playing = False            # pause: stop pumping + mute
            is_paused = True
            play_button.label = "PLAY"
        else:
            is_paused = False             # resume
            is_playing = True
            play_button.label = "PAUSE"
    elif action == "stop":
        if vgm is not None:
            vgm.stop()                    # halts + resets the AY (silence)
        is_playing = False
        is_paused = False
        play_button.label = "PLAY"
        progress_bar.value = 0.0
        last_progress = 0.0
        time_label.text = f"{fmt_time(0)} / {fmt_time(song_duration)}"
        last_sec = 0
    elif action == "prev":
        change_track(-1)
    elif action == "next":
        change_track(1)

def touched_index(the_btns):
    """Index of the button in btns under the touch, or None."""
    if not tsc.touched:
        return None
    point = tsc.touch
    if point["pressure"] < 100:
        return None
    p = (
        simpleio.map_range(point['x'], 430, 3700, 0, 320),
        simpleio.map_range(point['y'], 315, 3800, 0, 480),
    )
    for ind, the_btn in enumerate(the_btns):
        if the_btn.contains(p):
            return ind
    return None

# --- Boot into the menu with the first track pre-loaded (stopped) ---
if playlist:
    build_menu_page(0)
    load_track(0)
show_menu()

# --- Main loop ---
POLL_INTERVAL = 0.02
last_index = None
last_poll = time.monotonic()

while True:
    # Feed audio as tightly as possible, in any view.
    if is_playing and vgm is not None:
        vgm.update()
        if not vgm.playing:               # track reached its end
            if repeat_mode:
                vgm.play(ay)              # replay the same track (no SD reload)
                last_progress = -1.0
                last_sec = -1
            else:
                change_track(1)           # auto-advance, wraps at the end
        elif vgm.loop_count >= 1 and not repeat_mode:
            change_track(1)               # looping file finished a pass; move on

    now = time.monotonic()
    if now - last_poll >= POLL_INTERVAL:
        last_poll = now

        btns = play_buttons if current_view == "play" else menu_buttons
        acts = play_actions if current_view == "play" else menu_actions
        index = touched_index(btns)
        for i, btn in enumerate(btns):
            if btn is repeat_button:      # its lit state reflects repeat_mode, not touch
                continue
            btn.selected = i == index

        if wait_release:
            if index is None:             # finger lifted; accept presses again
                wait_release = False
            last_index = index
        else:
            if index is not None and index != last_index:
                dispatch(acts[index])
            last_index = index

        if is_playing and vgm is not None:
            progress = vgm.progress
            if abs(progress - last_progress) >= 0.01:
                progress_bar.value = progress
                last_progress = progress
            sec = int(vgm.elapsed)
            if sec != last_sec:
                time_label.text = f"{fmt_time(sec)} / {fmt_time(song_duration)}"
                last_sec = sec
