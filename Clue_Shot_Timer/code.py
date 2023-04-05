# SPDX-FileCopyrightText: 2023 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import random
import time
import gc
import simpleio
import audiobusio

import displayio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect

import board
import digitalio

settings = {}

with open("/settings.txt", "r") as F:
    for line in F:
        k, v = line.replace("\n", "").split(",")
        print(k, v)
        settings[k] = v

MODE = settings["mode"]
if settings["delay"] == "RNDM":
    DELAY_TIME = settings["delay"]
else:
    DELAY_TIME = int(settings["delay"])
PB = float(settings["pb"])
PAR = float(settings["par"])
SENSITIVITY = int(settings["sensitivity"])


gc.enable()
DEAD_TIME_DELAY = 0.11

arial18 = bitmap_font.load_font("/fonts/Arial-18.pcf")
arialb24 = bitmap_font.load_font("/fonts/Arial-Bold-24.pcf")
lato74 = bitmap_font.load_font("/fonts/Lato-Regular-74.pcf")

display = board.DISPLAY

display.auto_refresh = False

group = displayio.Group()

button_a = digitalio.DigitalInOut(board.BUTTON_A)
button_a.switch_to_input(pull=digitalio.Pull.UP)
button_b = digitalio.DigitalInOut(board.BUTTON_B)
button_b.switch_to_input(pull=digitalio.Pull.UP)

main_time = label.Label(
    font=lato74,
    anchored_position=(120, 40),
    text="00.00",
    color=0xFFFFFF,
    anchor_point=(0.5, 0.5),
)
group.append(main_time)

shot_num = label.Label(
    font=arialb24,
    anchored_position=(120, 80),
    text="#0   SPL 00.00",
    anchor_point=(0.5, 0),
)
group.append(shot_num)

first = label.Label(
    font=arialb24,
    anchored_position=(120, 120),
    text="1st: 00.00",
    anchor_point=(0.5, 0),
)
group.append(first)

delay = label.Label(
    font=arialb24,
    anchored_position=(120, 160),
    text=f"Delay: {DELAY_TIME}",
    anchor_point=(0.5, 0),
)
group.append(delay)

sens = label.Label(font=arialb24, x=15, y=220, text=f"{SENSITIVITY}")
group.append(sens)

if MODE == "PB":
    mode_text = f"{MODE} {PB:05.2f}"
elif MODE == "Par":
    mode_text = f"{MODE} {PAR:05.2f}"
else:
    mode_text = MODE
mode_label = label.Label(
    font=arialb24, anchored_position=(225, 210), text=mode_text, anchor_point=(1, 0)
)
group.append(mode_label)


def normalized_rms(values):
    """Gets the normalized RMS of the mic samples"""
    minbuf = int(sum(values) / len(values))
    samples_sum = sum(float(sample - minbuf) * (sample - minbuf) for sample in values)

    return (samples_sum / len(values)) ** 0.5


def picker(current):
    """Displays screen allowing user to set a time"""
    pick[0].text, pick[1].text, pick[2].text, pick[3].text = list(
        current.replace(".", "")
    )
    display.show(pick)
    time.sleep(0.2)
    index = 0

    while True:
        if not button_b.value:
            pick[index].background_color = None
            pick[index].color = 0xFFFFFF
            index += 1
            if index == 4:
                index = 0
            pick[index].background_color = 0xFFFFFF
            pick[index].color = 0x000000
            started = time.monotonic()
            while not button_b.value:
                if time.monotonic() - started > 1:
                    pick[0].color = 0x000000
                    pick[0].background_color = 0xFFFFFF
                    pick[1].color = 0xFFFFFF
                    pick[1].background_color = None
                    pick[2].color = 0xFFFFFF
                    pick[2].background_color = None
                    pick[3].color = 0xFFFFFF
                    pick[3].background_color = None
                    return float(
                        f"{pick[0].text}{pick[1].text}.{pick[2].text}{pick[3].text}"
                    )

        if not button_a.value:
            pick[index].text = str(int(pick[index].text) + 1)[-1]
            started = time.monotonic()
            while not button_a.value:
                if time.monotonic() - started > 1:
                    return current
        display.refresh()

    display.show(None)


def rect_maker(shots):
    rects = displayio.Group()
    for i in range(len(shots)):
        if i == 10:
            break
        rectangle = Rect(x=0, y=24 + (i * 24), width=240, height=1, fill=0xFFFFFF)
        rects.append(rectangle)
    return rects


def shot_label_maker(grp):
    txt = ""

    for i, j in enumerate(shot_list):
        if i == 0:
            split = j
        else:
            split = j - shot_list[i - 1]
        txt = txt + f"{i+1:02}\t{j:05.2f}\t{split:05.2f}\n"
    grp.append(
        label.Label(
            font=arial18,
            anchored_position=(120, 3),
            text=txt[:-1],
            color=0xFFFFFF,
            line_spacing=0.82,
            anchor_point=(0.5, 0),
        )
    )
    gc.collect()
    return grp


def show_shot_list(shots, disp):
    done = False

    shot_group = rect_maker(shots)
    shot_group = shot_label_maker(shot_group)
    disp.show(shot_group)

    tracker = 10
    while True:
        if not button_b.value:
            started = time.monotonic()
            while not button_b.value:
                if time.monotonic() - started > 1:
                    done = True
                    break
            if tracker < len(shots) and not done:
                shot_group[10].y -= 24
                tracker += 1

        if not button_a.value:
            started = time.monotonic()
            while not button_a.value:
                if time.monotonic() - started > 1:
                    done = True
                    break
            if tracker > 10 and not done:
                shot_group[10].y += 24
                tracker -= 1

        if done:
            break
        disp.refresh()
    shot_group = None
    gc.collect()


def menu_mode(
    mode, delay_time, sensitivity_, pb, par, length_, submenus_
):  # pylint: disable=too-many-branches,too-many-statements
    selected = int(menu[0].y / 40) + 1
    display.show(menu)
    display.refresh()
    page_ = menu
    while not button_a.value:
        pass
    done = False
    while not done:
        if not button_a.value and selected < length_:
            started = time.monotonic()
            while not button_a.value:
                if time.monotonic() - started > 1:
                    if page_ == menu:
                        display.show(group)
                        display.refresh()
                        done = True
                    else:
                        page_ = menu
                        selected = int(page_[0].y / 40) + 1
                        length_ = len(page_) - 1
                        display.show(page_)
                        submenus_ = main_menu_opts
                        display.refresh()
                        break
            else:
                if not done:
                    rgb = page_[selected].color
                    color = (
                        ((255 - ((rgb >> 16) & 0xFF)) << 16)
                        + ((255 - ((rgb >> 8) & 0xFF)) << 8)
                        + (255 - (rgb & 0xFF))
                    )
                    page_[selected].color = color

                    page_[0].y += 40
                    selected += 1

                    rgb = page_[selected].color
                    color = (
                        ((255 - ((rgb >> 16) & 0xFF)) << 16)
                        + ((255 - ((rgb >> 8) & 0xFF)) << 8)
                        + (255 - (rgb & 0xFF))
                    )
                    page_[selected].color = color
            while not button_a.value:
                pass

        if not button_a.value and selected == length_ and not done:
            started = time.monotonic()
            while not button_a.value:
                if time.monotonic() - started > 1:
                    if page_ == menu:
                        display.show(group)
                        display.refresh()
                        done = True
                    else:
                        page_ = menu
                        selected = int(page_[0].y / 40) + 1
                        length_ = len(page_) - 1
                        display.show(page_)
                        submenus_ = main_menu_opts
                        display.refresh()
                        break
            else:
                if not done:
                    rgb = page_[selected].color
                    color = (
                        ((255 - ((rgb >> 16) & 0xFF)) << 16)
                        + ((255 - ((rgb >> 8) & 0xFF)) << 8)
                        + (255 - (rgb & 0xFF))
                    )
                    page_[selected].color = color

                    page_[0].y = 0
                    selected = 1

                    rgb = page_[selected].color
                    color = (
                        ((255 - ((rgb >> 16) & 0xFF)) << 16)
                        + ((255 - ((rgb >> 8) & 0xFF)) << 8)
                        + (255 - (rgb & 0xFF))
                    )
                    page_[selected].color = color
            while not button_a.value:
                pass

        if not button_b.value:
            if isinstance(submenus_[1], list):
                if submenus_[0] == mode:
                    mode = submenus_[1][selected - 1]
                    submenus_[0] = mode
                    if mode == "PB":
                        pb = picker(f"{PB:05.2f}")
                        mode_label.text = f"{mode} {pb}"
                        page_[selected].text = mode_label.text
                        display.show(page_)
                        display.refresh()
                    elif mode == "Par":
                        par = picker(f"{par:05.2f}")
                        mode_label.text = f"{mode} {par}"
                        page_[selected].text = mode_label.text
                        display.show(page_)
                        display.refresh()
                    else:
                        mode_label.text = mode
                if submenus_[0] == delay_time and len(submenus_[1]) == 5:
                    delay_time = submenus_[1][selected - 1]
                    submenus_[0] = delay_time
                    delay.text = f"Delay: {delay_time}"
                if submenus_[0] == sensitivity_ and len(submenus_[1]) == 6:
                    sensitivity_ = submenus_[1][selected - 1]
                    submenus_[0] = sensitivity_
                    sens.text = f"{sensitivity_}"
                for i in page_:
                    i.color = 0xFFFFFF
                page_[selected].color = 0x00FF00
            else:
                page_ = submenus_[selected - 1]
                submenus_ = page_opts[selected - 1]
                selected = int(page_[0].y / 40) + 1
                length_ = len(page_) - 1
                display.show(page_)
            while not button_b.value:
                pass

        display.refresh()
    return mode, delay_time, sensitivity_, pb, par


def label_maker(txt, grp, font, x, y, x_step=0, y_step=0, anchor=None, padding=0):
    for count, t in enumerate(txt):
        x_pos = x + (count * x_step)
        y_pos = y + (count * y_step)
        if anchor:
            grp.append(
                label.Label(
                    font,
                    text=t,
                    anchored_position=(x_pos, y_pos),
                    color=0xFFFFFF,
                    padding_top=padding,
                    anchor_point=anchor,
                )
            )
        else:
            grp.append(
                label.Label(
                    font, text=t, x=x_pos, y=y_pos, color=0xFFFFFF, padding_top=padding
                )
            )
    return grp


mode_opts = [MODE, ["Default", "PB", "Par"]]

delay_opts = [DELAY_TIME, [0, 1, 3, 5, "RNDM"]]

sensitivity_opts = [SENSITIVITY, [1, 2, 3, 4, 5, 6]]

# Number picker page
pick = displayio.Group()
pick = label_maker(
    ["0", "0"], pick, lato74, 40, 120, x_step=50, anchor=(0.5, 0.5), padding=8
)
pick = label_maker(
    ["0", "0"], pick, lato74, 150, 120, x_step=50, anchor=(0.5, 0.5), padding=8
)

pick[0].color = 0x000000
pick[0].background_color = 0xFFFFFF

dot = label.Label(
    lato74,
    text=".",
    color=0xFFFFFF,
    anchor_point=(0.5, 0.5),
    anchored_position=(120, 132),
)
pick.append(dot)

# Main menu page
menu = displayio.Group()
rect = Rect(0, 0, 240, 40, fill=0xFFFFFF)
menu.append(rect)

menu = label_maker(["Mode", "Delay", "Sensitivity"], menu, arialb24, 10, 20, y_step=40)
menu[1].color = 0x000000

# Mode menu page
mode_page = displayio.Group()

select = mode_opts[1].index(MODE)
rect = Rect(0, select * 40, 240, 40, fill=0xFFFFFF)
mode_page.append(rect)

mode_page = label_maker(
    ["Default", f"PB {PB}", f"Par {PAR}"], mode_page, arialb24, 10, 20, y_step=40
)
mode_page[select + 1].color = 0x00FF00

# Delay menu page
delay_page = displayio.Group()

select = delay_opts[1].index(DELAY_TIME)
rect = Rect(0, select * 40, 240, 40, fill=0xFFFFFF)
delay_page.append(rect)

delay_page = label_maker(
    ["0s", "1s", "3s", "5s", "Random"], delay_page, arialb24, 10, 20, y_step=40
)
delay_page[select + 1].color = 0x00FF00

# Sensitivity menu page
sensitivity_page = displayio.Group()

select = sensitivity_opts[1].index(SENSITIVITY)
rect = Rect(0, select * 40, 240, 40, fill=0xFFFFFF)
sensitivity_page.append(rect)

sensitivity_page = label_maker(
    ["1", "2", "3", "4", "5", "6"], sensitivity_page, arialb24, 10, 20, y_step=40
)
sensitivity_page[select + 1].color = 0x00FF00

main_menu_opts = [mode_page, delay_page, sensitivity_page]
page_opts = [mode_opts, delay_opts, sensitivity_opts]

submenus = main_menu_opts
page = menu
length = len(page) - 1

mic = audiobusio.PDMIn(
    board.MICROPHONE_CLOCK,
    board.MICROPHONE_DATA,
    sample_rate=16000,
    bit_depth=16,
)

sensitivity_settings = [8000, 10000, 15000, 20000, 25000, 30000]

display.show(group)
display.refresh()

sensitivity = sensitivity_settings[SENSITIVITY - 1]
while True:
    if not button_b.value:
        SHOTS = 0
        samples = array.array("H", [0] * 5)
        if DELAY_TIME == "RNDM":
            dly = round(random.uniform(1, 10), 2)
            time.sleep(dly)
        else:
            time.sleep(DELAY_TIME)
        start = time.monotonic()
        while not button_b.value:
            pass
        shot_list = []
        simpleio.tone(board.SPEAKER, 3500, duration=0.2)
        time.sleep(0.05)
        if MODE == "Par":
            shot_time = round(time.monotonic() - start, 2)
            while shot_time < PAR:
                shot_time = min(round(time.monotonic() - start, 2), PAR)
                main_time.text = f"{shot_time:05.2f}"
                display.refresh()
            simpleio.tone(board.SPEAKER, 3500, duration=0.2)
        else:
            if MODE == "PB":
                main_time.color = 0x00FF00
                display.refresh()
            while button_a.value and button_b.value:
                mic.record(samples, len(samples))
                magnitude = normalized_rms(samples)
                if magnitude > sensitivity:
                    SHOTS += 1
                    print("SHOT")
                    shot_time = round(time.monotonic() - start, 2)
                    if len(shot_list) != 0:
                        shot_num.text = (
                            f"#{SHOTS}   SPL {shot_time - shot_list[-1]:05.2f}"
                        )
                    else:
                        shot_num.text = f"#{SHOTS}   SPL {shot_time:05.2f}"
                    main_time.text = f"{shot_time:05.2f}"
                    if MODE == "PB" and shot_time > PB:
                        main_time.color = 0xFF0000
                    shot_list.append(shot_time)
                    first.text = f"1st: {shot_list[0]:05.2f}"
                    time.sleep(DEAD_TIME_DELAY)
                    display.refresh()
                    print(
                        (
                            magnitude,
                            SHOTS,
                        )
                    )
            gc.collect()
            if not button_b.value:
                show_shot_list(shot_list, display)
                display.show(group)
                display.refresh()
                while not button_b.value or not button_a.value:
                    pass

    if not button_a.value:
        start = time.monotonic()
        while not button_a.value:
            if time.monotonic() - start > 1:
                MODE, DELAY_TIME, SENSITIVITY, PB, PAR = menu_mode(
                    MODE, DELAY_TIME, SENSITIVITY, PB, PAR, length, submenus
                )
                sensitivity = sensitivity_settings[SENSITIVITY - 1]
                try:
                    with open("/settings.txt", "w") as F:
                        F.write(f"mode,{MODE}\n")
                        F.write(f"delay,{DELAY_TIME}\n")
                        F.write(f"par,{PAR}\n")
                        F.write(f"pb,{PB}\n")
                        F.write(f"sensitivity,{SENSITIVITY}")
                except OSError as e:  # Typically when the filesystem isn't writeable...
                    print("Filesystem is not writeable")
                break
        else:
            main_time.color = 0xFFFFFF
            main_time.text = "00.00"
            shot_num.text = "#0   SPL 00.00"
            first.text = "1st: 00.00"
            display.refresh()
            gc.collect()
