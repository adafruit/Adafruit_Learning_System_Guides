# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""FM-1 Flasher: the touch UI on the Metro ESP32-P4 and 2.8" TFT Touch Shield.

tools/deploy.py copies it to CIRCUITPY as code.py, with lib/fm1ui, the fm1
libraries, fonts/ and the splash; the bundle libraries it needs are listed there.
Firmware comes from /sd/firmware (Catalog over WiFi, or tools/make_sd.py), or
/firmware on CIRCUITPY. A card without firmware starts in Catalog.
"""
# Disabled for the Learn Guides lint check: the console note is printed before the slow imports.
# pylint: disable=ungrouped-imports,wrong-import-position
import gc

# First, before the slow imports: what shows on the panel's console after a
# reload (a start shows the splash instead).
print(
    "\x1b[2J\nFM-1 Flasher\n\nLoading the firmware list...\n\n"
    "The touchscreen comes back\nin a few seconds.\n"
)

from fm1ui import device as D  # noqa: E402
from fm1ui import ui  # noqa: E402

display, spi = D.display_setup()
D.splash(display)  # after a start, not a reload
D.host_setup(spi)
sd = D.mount_sd(spi)
root = D.firmware_root(sd)
state = D.DeviceState("/sd/flasher.json" if sd else "/flasher.json")

fill = False
if root is None and sd:
    # An empty card on a board with WiFi: fill it from the hub.
    import fm1catalog
    fm1catalog.mkdirs("/sd/firmware")
    fm1catalog.write_index("/sd/firmware")
    root, fill = "/sd/firmware", True

if root is None:
    import displayio
    D.display_redo(display)  # after a start, not a reload
    w, h = display.width, display.height
    g = displayio.Group()
    g.append(ui.rect(0, 0, w, h, ui.BG))
    g.append(ui.text(ui.NAME, "No firmware found", ui.FG, w // 2, h // 2 - 20, (0.5, 0.5)))
    hint = "Put a microSD card in the slot."
    g.append(ui.text(ui.BODY, hint, ui.DIM, w // 2, h // 2 + 10, (0.5, 0.5)))
    display.root_group = g
    display.refresh()
    while True:
        pass

from fm1ui import app as A  # noqa: E402

gc.collect()
app = A.App(display, D.Touch(), root, state, D.Probe(), D.Installer(), updater=D.Network())
print("free RAM:", gc.mem_free())
D.display_redo(display)  # after a start, not a reload
from fm1ui import flat  # noqa: E402

home = flat.list_screen(app)  # the list; it scrolls with Settings > Scroll pages on
if fill:
    from fm1ui.update import UpdateScreen
    app.stack.append(home)  # under it: where Back and OK go
    app.run(UpdateScreen(app))
app.run(home)
