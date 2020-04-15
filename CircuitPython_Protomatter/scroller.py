import array

from _pixelbuf import wheel
import board
import displayio
import framebufferio
import protomatter
import terminalio
displayio.release_displays()

proto = protomatter.Protomatter(
    width=64, height=32, bit_depth=3,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(proto, auto_refresh=False)

def tilegrid(palette):
    return displayio.TileGrid(
        bitmap=terminalio.FONT.bitmap, pixel_shader=palette,
        width=1, height=1, tile_width=6, tile_height=14, default_tile=32)

g = displayio.Group(max_size=2)
linelen = (64//7)+2
l1 = displayio.Group(max_size=linelen)
l2 = displayio.Group(max_size=linelen)
g.append(l1)
g.append(l2)
display.show(g)

l1.y = 1
l2.y = 16

sh = [displayio.Palette(2) for _ in range(linelen)]
tg1 = [tilegrid(shi) for shi in sh]
tg2 = [tilegrid(shi) for shi in sh]

charmap = array.array('b', [terminalio.FONT.get_glyph(32).tile_index]) * 256
for ch in range(256):
    glyph = terminalio.FONT.get_glyph(ch)
    if glyph is not None:
        charmap[ch] = glyph.tile_index

for idx, gi in enumerate(tg1):
    gi.x = 7 * idx
    l1.append(gi)

for idx, gi in enumerate(tg2):
    gi.x = 7 * idx
    l2.append(gi)

lines = [
    b"This scroller is brought to you by    CircuitPython & PROTOMATTER",
    b"        .... . .-.. .-.. --- / .--. .-. --- - --- -- .- - - . .-.",
    b"Greetz to ...          @PaintYourDragon      @v923z  @adafruit         ",
    b"  @danh        @ladyada  @kattni      @tannewt    all showers & tellers",
    b"New York Strong                       Wash Your Hands                  ",
    b"                  Flatten the curve                   Stronger Together",
]

even_lines = lines[0::2]
odd_lines = lines[1::2]

def scroll(t, b):
    sp = b' ' * linelen
    t = sp + t + sp
    b = sp + b + sp
    maxlen = max(len(t), len(b))
    for i in range(maxlen-linelen):
        for j in range(linelen):
            sh[j][1] = wheel(3 * (2*i+j))
            tg1[j][0] = charmap[t[i+j]]
            tg2[j][0] = charmap[b[i+j]]
        for j in range(7):
            l1.x = -j
            l2.x = -j
            display.refresh(minimum_frames_per_second=0)
            #display.refresh(minimum_frames_per_second=0)

while True:
    for e, o in zip(even_lines, odd_lines):
        scroll(e, o)
