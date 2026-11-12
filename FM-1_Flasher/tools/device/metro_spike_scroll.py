# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Spike: can the Metro ESP32-P4 scroll the list's card pages with the
finger, iPhone-style? Times sliding two pages of cards across the 2.8"
shield at several SPI clocks. With the UI deployed, at the REPL:

    import metro_spike_scroll as m; m.run()  # cards as the list builds them, at 40/60/80 MHz
    m.run_flat()                               # each page drawn once into one bitmap
    m.show(80_000_000, seconds=20)             # slide back and forth to watch
    m.touch(seconds=90, pages_n=5)             # drag the pages, let go to glide

Results (3 November 2026): the list's cards slide at 10 fps whatever the SPI
clock (displayio drawing the polygons and text is the limit); flattened pages
at 22 fps at 40 MHz and 29 fps at 80 MHz.
80 MHz looked clean. touch(): dragging flat pages with the finger ran at
17-24 fps (reading the FT6206 each frame costs a little), and the user found
it worked great.

Cards are built like the list's (outlined panels, text, 40x40 pictures in
RAM), with the header and footer fixed, so only the card band redraws.
"""
import time

import board
import displayio
import fourwire

import adafruit_ili9341
from fm1ui import ui

W, H = 320, 240
TOP, BOTTOM = 36, 204  # the card band (fm1ui.layout._small)
CARD_W, CARD_H, GAP, GRID_X = 100, 82, 4, 6


def make_display(baud):
    displayio.release_displays()
    spi = board.SPI()
    bus = fourwire.FourWire(spi, command=board.D9, chip_select=board.D10, baudrate=baud)
    return adafruit_ili9341.ILI9341(bus, width=W, height=H, auto_refresh=False)


def picture(seed):
    """A busy 40x40 picture, like a firmware's thumbnail."""
    bmp = displayio.Bitmap(40, 40, 16)
    pal = displayio.Palette(16)
    for i in range(16):
        pal[i] = ((i * 37 + seed * 53) & 0xFF) << 16 | ((i * 91 + seed * 17) & 0xFF) << 8 | (i * 23 + seed * 71) & 0xFF
    for y in range(40):
        for x in range(40):
            bmp[x, y] = (x * 3 + y * 5 + seed + (x * y >> 3)) & 15
    return displayio.TileGrid(bmp, pixel_shader=pal)


def page(n):
    g = displayio.Group()
    for i in range(6):
        x = GRID_X + (i % 3) * (CARD_W + GAP)
        y = TOP + (i // 3) * (CARD_H + GAP)
        card = ui.outlined(x, y, CARD_W, CARD_H, ui.PANEL, ui.LINE)
        card.append(ui.rect(x + 4, y + 2, CARD_W - 8, 3, ui.CYAN if (n + i) % 2 else ui.WARN))
        pic = picture(n * 6 + i)
        pic.x, pic.y = x + 30, y + 8
        card.append(pic)
        card.append(ui.text(ui.NAME, "Firmware %d" % (n * 6 + i + 1), ui.FG, x + CARD_W // 2, y + 52, (0.5, 0)))
        card.append(ui.text(ui.SMALL, "1.%d.0" % i, ui.DIM, x + CARD_W // 2, y + 68, (0.5, 0)))
        g.append(card)
    return g


def scene():
    root = displayio.Group()
    root.append(ui.rect(0, 0, W, H, ui.BG))
    pages = displayio.Group()
    for n in range(3):  # the page before, this one, the next
        p = page(n)
        p.x = (n - 1) * W
        pages.append(p)
    root.append(pages)
    root.append(ui.text(ui.NAME, "Scroll spike", ui.CYAN, 10, 12, (0, 0)))
    root.append(ui.rect(0, BOTTOM, W, H - BOTTOM, ui.BG))
    root.append(ui.text(ui.SMALL, "1/3", ui.FG, W // 2, 222, (0.5, 0.5)))
    return root, pages


def slide(display, pages, frames, distance=W):
    """Slide one page left in `frames` steps; ms per frame."""
    times = []
    for f in range(1, frames + 1):
        pages.x = -distance * f // frames
        t = time.monotonic_ns()
        display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)
        times.append((time.monotonic_ns() - t) // 1_000_000)
    pages.x = 0
    display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)
    return times


def run(bauds=(40_000_000, 60_000_000, 80_000_000)):
    for baud in bauds:
        display = make_display(baud)
        root, pages = scene()
        display.root_group = root
        t = time.monotonic_ns()
        display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)
        full = (time.monotonic_ns() - t) // 1_000_000
        small = slide(display, pages, 16)  # finger-sized steps, 20 px
        drag = slide(display, pages, 64, 64)  # 1 px steps: a slow drag
        ms = sum(small[2:]) / len(small[2:])
        print("%d MHz: full %d ms; page slide %.0f ms/frame (%.0f fps), 1 px drag %.0f ms/frame; actual SPI %.1f MHz"
              % (baud // 1_000_000, full, ms, 1000 / ms, sum(drag) / len(drag), board.SPI().frequency / 1e6
                 if hasattr(board.SPI(), "frequency") else 0))


def show(baud=80_000_000, seconds=20, frames=12, flat=True):
    """Slide pages back and forth, eased, to watch for glitches."""
    display = make_display(baud)
    root, pages = flat_scene() if flat else scene()
    display.root_group = root
    end = time.monotonic() + seconds
    direction = -1
    while time.monotonic() < end:
        for f in range(1, frames + 1):
            t = f / frames
            ease = 1 - (1 - t) ** 3
            pages.x = int(direction * W * ease) if direction < 0 else int(-W + W * ease)
            display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)
        time.sleep(0.6)
        direction = -direction


# -- each page drawn once into one bitmap -------------------------------------

def flat_page(n):
    """The page as one 320x168 bitmap: cards as filled rectangles with an
    edge, pictures and text blitted in (what a flattened card page costs)."""
    import bitmaptools
    band = BOTTOM - TOP
    pal = displayio.Palette(32)
    colors = [ui.BG, ui.PANEL, ui.LINE, ui.CYAN, ui.WARN, ui.FG, ui.DIM]
    for i, c in enumerate(colors):
        pal[i] = c
    bmp = displayio.Bitmap(W, band, 32)
    bmp.fill(0)
    for i in range(6):
        x = GRID_X + (i % 3) * (CARD_W + GAP)
        y = (i // 3) * (CARD_H + GAP)
        bitmaptools.fill_region(bmp, x, y, x + CARD_W, y + CARD_H, 2)
        bitmaptools.fill_region(bmp, x + 1, y + 1, x + CARD_W - 1, y + CARD_H - 1, 1)
        bitmaptools.fill_region(bmp, x + 4, y + 2, x + CARD_W - 4, y + 5, 3 if (n + i) % 2 else 4)
        pic = picture(n * 6 + i).bitmap
        for py in range(40):  # 16 picture colors at 16..31
            for px in range(40):
                bmp[x + 30 + px, y + 8 + py] = 16 + pic[px, py]
        for py in range(14):  # stand-ins for the name and version
            bitmaptools.fill_region(bmp, x + 20, y + 52 + py, x + 80, y + 53 + py, 5 if py % 3 else 1)
    for c in range(16):
        pal[16 + c] = ((c * 37 + n * 53) & 0xFF) << 16 | ((c * 91) & 0xFF) << 8 | (c * 23) & 0xFF
    return displayio.TileGrid(bmp, pixel_shader=pal)


def flat_scene():
    root = displayio.Group()
    root.append(ui.rect(0, 0, W, TOP, ui.BG))
    pages = displayio.Group(y=TOP)
    for n in range(3):
        p = flat_page(n)
        p.x = (n - 1) * W
        pages.append(p)
    root.append(pages)
    root.append(ui.text(ui.NAME, "Scroll spike (flat)", ui.CYAN, 10, 12, (0, 0)))
    root.append(ui.rect(0, BOTTOM, W, H - BOTTOM, ui.BG))
    return root, pages


def run_flat(bauds=(40_000_000, 80_000_000)):
    for baud in bauds:
        display = make_display(baud)
        root, pages = flat_scene()
        display.root_group = root
        display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)
        small = slide(display, pages, 16)
        drag = slide(display, pages, 64, 64)
        ms = sum(small[2:]) / len(small[2:])
        print("flat %d MHz: page slide %.0f ms/frame (%.0f fps), 1 px drag %.0f ms/frame"
              % (baud // 1_000_000, ms, 1000 / ms, sum(drag) / len(drag)))


# -- touch: drag the pages, let go to glide ------------------------------------

def touch(baud=80_000_000, seconds=60, pages_n=3, glide_frames=8):
    """Drag the pages with a finger; let go and they glide to a page: the
    next one after a flick or a drag past a quarter of the screen, else back.
    The ends give a little (rubber band). Prints the drag's frame rate."""
    from fm1ui import metro_p4
    import adafruit_focaltouch
    ft = adafruit_focaltouch.Adafruit_FocalTouch(board.I2C())
    ax, bx, ay, by = metro_p4.TOUCH_CAL

    def screen_x(p):  # as metro_p4.Touch.map
        return min(W - 1, max(0, int(ax * p["y"] + bx)))
    display = make_display(baud)
    root = displayio.Group()
    root.append(ui.rect(0, 0, W, TOP, ui.BG))
    pages = displayio.Group(y=TOP)
    for n in range(pages_n):
        p = flat_page(n)
        p.x = n * W
        pages.append(p)
    root.append(pages)
    root.append(ui.text(ui.NAME, "Drag the cards", ui.CYAN, 10, 12, (0, 0)))
    root.append(ui.rect(0, BOTTOM, W, H - BOTTOM, ui.BG))
    label = ui.text(ui.SMALL, "1/%d" % pages_n, ui.FG, W // 2, 222, (0.5, 0.5))
    root.append(label)
    display.root_group = root

    def draw():
        display.refresh(target_frames_per_second=None, minimum_frames_per_second=0)

    draw()
    page = 0
    lo, hi = -(pages_n - 1) * W, 0
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            pts = ft.touches
        except OSError:
            pts = []
        if not pts:
            continue
        x0 = screen_x(pts[0])
        base = pages.x
        hist = [(time.monotonic(), x0)]
        frames, t0 = 0, time.monotonic()
        while True:  # dragging
            try:
                pts = ft.touches
            except OSError:
                pts = hist and pts
            if not pts:
                break
            x = screen_x(pts[0])
            hist.append((time.monotonic(), x))
            off = base + x - x0
            if off > hi:
                off = hi + (off - hi) // 3  # rubber band past the ends
            elif off < lo:
                off = lo + (off - lo) // 3
            if off != pages.x:
                pages.x = off
                draw()
                frames += 1
        dt = time.monotonic() - t0
        if frames:
            print("drag: %d frames in %.2f s, %.0f fps" % (frames, dt, frames / dt))
        # Velocity over the last 0.1 s, in px/s.
        now = time.monotonic()
        recent = [h for h in hist if now - h[0] <= 0.12] or hist[-2:]
        v = (recent[-1][1] - recent[0][1]) / max(0.001, recent[-1][0] - recent[0][0])
        moved = pages.x - (-page * W)
        if (moved < -W // 4 or v < -400) and page < pages_n - 1:
            page += 1
        elif (moved > W // 4 or v > 400) and page > 0:
            page -= 1
        start, target = pages.x, -page * W
        for f in range(1, glide_frames + 1):
            e = 1 - (1 - f / glide_frames) ** 3
            pages.x = int(start + (target - start) * e)
            draw()
        label.set("%d/%d" % (page + 1, pages_n))
        draw()
