# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
import traceback
from adafruit_editor import editor, picker
from adafruit_featherwing import tft_featherwing_35
import terminalio
import displayio
from adafruit_display_text.bitmap_label import Label
import usb_cdc
#pylint: disable=redefined-builtin,broad-exception-caught

def print(message):
    usb_cdc.data.write(f"{message}\r\n".encode("utf-8"))


tft_featherwing = tft_featherwing_35.TFTFeatherWing35V2()
display = tft_featherwing.display
display.rotation = 180

customized_console_group = displayio.Group()
display.root_group = customized_console_group
customized_console_group.append(displayio.CIRCUITPYTHON_TERMINAL)

visible_cursor = Label(terminalio.FONT, text="",
                       color=0x000000, background_color=0xeeeeee, padding_left=1)
visible_cursor.hidden = True
visible_cursor.anchor_point = (0, 0)
customized_console_group.append(visible_cursor)

try:
    while True:
        try:
            visible_cursor.hidden = True
            filename = picker.pick_file()
        except KeyboardInterrupt:
            customized_console_group.remove(displayio.CIRCUITPYTHON_TERMINAL)
            break

        try:
            visible_cursor.hidden = False
            editor.edit(filename, visible_cursor)
        except KeyboardInterrupt:
            visible_cursor.hidden = True

# Any Exception, including Keyboard Interrupt
except Exception as e:
    print("\n".join(traceback.format_exception(e)))
    customized_console_group.remove(displayio.CIRCUITPYTHON_TERMINAL)
