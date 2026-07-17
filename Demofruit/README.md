# Demofruit

A demoscene sampler for the **Adafruit Fruit Jam** (RP2350). Six classic-style
effects, a live animated menu, per-demo tracker music, and a NeoPixel status
strip — all in a single sketch (`demofruit.ino`) that flashes as one UF2.

The project is a love letter to the Amiga/DOS demoscene of the early 1990s,
rebuilt on a microcontroller you can hold in your palm. It culminates in a
faithful port of Eric Graham's 1987 *Juggler* raytracer — the demo that helped
sell the world on the Amiga — running thousands of times faster than the
original hour-per-frame hardware.

---

## Hardware

- **Adafruit Fruit Jam** (RP2350B, 8 MB PSRAM, 16 MB flash, HSTX DVI output)
- HDMI display
- Headphones or a powered speaker (audio via the onboard TLV320DAC3100 codec)
- The board's onboard buttons (Button1/2/3) and 5-pixel NeoPixel strip

### Required build settings (Arduino IDE)

- **Board:** Adafruit Fruit Jam RP2350
- **CPU Speed:** 150 MHz — *required*. The DVI HSTX library manages its own
  overclock to 240 MHz; the Tools menu must be left at 150 MHz or the library
  refuses to compile.
- **Core:** arduino-pico (Earle Philhower) 5.6.0 or newer

### Required libraries (Library Manager)

- Adafruit DVI HSTX
- Adafruit GFX
- Adafruit TLV320 I2S (pulls in its dependencies)
- Adafruit NeoPixel

`pocketmod.h` / `pocketmod.c` ship inside the sketch folder — no library needed.

---

## The six demos

Each demo began as a standalone sketch and was merged into the sampler. They are
listed here in menu order, which is also roughly chronological by technique — a
small tour through the era's effects.

### 1. Starfield
A forward-warping star field with per-letter bouncing chrome text. The classic
"space + scroller" demo opener.

- **Button1** — cycle the text message (`Adafruit`, `Fruit Jam`, `kqvc`,
  `L 4 r 5 5 5`; editable at the top of `starfield_impl.h`)
- **Button2** — step warp intensity
- **Button3** — randomize star density

### 2. Plasma
Palette-cycled plasma — smoothly morphing colored blobs generated from summed
sine waves. Originally used the RP2350's hardware palette (DVHSTX8); in the
sampler it renders through the shared 16-bit display via a software palette LUT.

- **Button1** — cycle palette (Fire / Ice / Toxic / Lava / Rainbow)
- **Button2** — toggle palette-rotation vs. full-animate mode
- **Button3** — randomize wave frequencies and drift (can produce very large,
  slow cells)

### 3. Chrome Sphere
A dual-core raytracer: a reflective chrome sphere orbiting over a cream-and-red
checkerboard, with specular highlights and a shadow. Core 1 renders while core 0
upscales and blits.

- **Button1** — randomize light angle
- **Button2** — randomize camera height
- **Button3** — randomize camera distance

### 4. Valley Run
A wireframe trench flythrough with a flat-shaded fighter ship strafing and
banking through it — a nod to the vector-landscape demos and to *Star Fox*.

- **Button1** — cycle wire color (ship auto-picks the complementary color)
- **Button2** — step scroll speed (5 presets)
- **Button3** — randomize terrain

### 5. Rotozoom
A tiling bitmap rotating and scaling in real time (a "rotozoomer"), with a
blue-tinted spherical lens bubble drifting over it in a Lissajous orbit. Uses
fixed-point math and dual-core rendering. The source bitmap is a 128×128 image
baked into `texture.h` (see "Creating the rotozoom image" below).

- **Button1** — cycle motion preset (Normal / Fast / Reverse / Slow Drift /
  Zoom Frenzy)
- **Button2** — toggle the lens
- **Button3** — randomize the zoom range

### 6. The Juggler
A faithful port of **Eric Graham's 1987 Amiga *Juggler* raytracer** — a robotic
figure juggling three mirrored balls over a checkered floor. The original took
about an hour per frame on a 7 MHz 68000; the Fruit Jam renders a frame in about
1.5 seconds.

On launch it raytraces 24 frames of a juggling cycle into PSRAM (watch the
"venetian blind" render, ~20 seconds, both cores working), then loops smooth
playback forever — the same render-then-playback architecture as Graham's
original `movie` player.

- **Button1** — slower playback
- **Button2** — faster playback (3/6/12/18/24/30 fps)
- **Button3** — pause / resume

The renderer preserves Graham's original algorithm and 1987 copyright notice.
The juggling motion (a proper 3-ball cascade, plus a subtle knee-bend and
weight-shift) was recreated for this port, since the original animation data
wasn't in the published source.

---

## How the launcher works

Because the demos each want slightly different display configurations and the
DVI HSTX library is happiest when its display object is constructed once at
startup, Demofruit uses a **reboot launcher** — the same technique multi-part
Amiga demos used to chain-load segments.

1. On a cold boot or after pressing **Reset**, no launch flag is set, so the
   sketch shows the **menu**: a slowly tumbling, dim shaded 3D cube behind
   green scrolling-style text, with the cube tinted to the highlighted demo's
   signature color.
2. Menu navigation: **Button3 = up**, **Button2 = down**, **Button1 = launch**.
   (This matches the physical top-to-bottom button order on the board.)
3. Selecting a demo writes its ID plus a magic number into the RP2350's
   **watchdog scratch registers** (which survive a soft reboot) and triggers a
   watchdog reboot.
4. On the next boot the sketch sees the flag, immediately clears it, and
   constructs that demo's ideal display and runs it forever.
5. Because the flag was cleared at demo start, pressing **Reset** returns you to
   the menu.

The NeoPixel strip reinforces the UI throughout: in the menu it glows the
highlighted demo's signature color; inside a demo it shows the current setting
(e.g. Valley Run lights *N* of 5 pixels for the speed preset, in the current
wire color). Pixel order is top-to-bottom. A brief blink acknowledges
"randomize"-type buttons that have no persistent state to display.

> **Tip:** If the board ever behaves strangely after flashing (blank screen, no
> USB serial port), do a full **power cycle** — unplug and replug — rather than
> just pressing Reset. The RP2350 + DVI + PSRAM combination can wedge USB during
> boot, and a true power cycle clears it. To force the bootloader for uploading,
> hold **Button1 (BOOT)**, tap **Reset**, then release Button1.

---

## How the music works

Each demo (and the menu) has its own soundtrack, played as a **ProTracker MOD**
file. MODs are the native music format of the demoscene: a small bank of
digitized instrument samples plus pattern data describing which sample plays at
what pitch on each channel. Whole songs fit in tens to a few hundred KB.

Playback uses **pocketmod**, a tiny single-file MIT-licensed MOD player, which
renders the music in real time on core 0 using only a few percent of CPU. The
audio path is: pocketmod mixes stereo float samples → converted to 16-bit →
sent to the TLV320DAC3100 codec over I2S (via the RP2350's PIO + DMA). A
non-blocking "pump" is called throughout each demo's loop so the music never
stutters, including during the Juggler's long render.

Songs live in the sketch as C headers, one per slot:

| File | Used by |
|------|---------|
| `song_0.h` | Menu |
| `song_1.h` | Starfield |
| `song_2.h` | Plasma |
| `song_3.h` | Chrome Sphere |
| `song_4.h` | Valley Run |
| `song_5.h` | Rotozoom |
| `song_6.h` | The Juggler |

Each header contains a `MOD_DATA` byte array; the sketch wraps each in its own
namespace so they don't collide. pocketmod supports up to 32 channels, so
6-channel, 8-channel, and wider MODs play fine (not just 4-channel) — though
authentic 4-channel MODs are the period-correct choice and mix with the least
CPU. If a song fails to load, the sketch logs the failure and simply runs
silent rather than crashing.

Volume is a fixed level in software (downstream powered speakers have their own
volume control); it is not adjustable from the demos.

### The onboard speaker (A1 jumper)

The onboard speaker is **muted by default**; the headphone jack always works.
The Fruit Jam's audio jack has no usable insertion-detect wiring, so rather
than auto-muting the speaker when headphones are plugged in, Demofruit gates
the speaker behind a hardware jumper:

- **To enable the speaker:** connect the **A1 pad (GPIO41)** on the GPIO header
  to **GND** with a jumper wire, then reset/power on the board.
- **To mute it:** remove the jumper and reset.

The jumper is read once at startup (with an internal pull-up: tied to GND =
speaker on, left open = muted), and the state is printed to the serial monitor.
The speaker connector needs the board powered from 5 V to be audible.

---

## Converting your own MOD files

A helper script, `mod2header.py`, converts any ProTracker `.mod` file into the
header format the sketch expects. It does a straight byte-to-array conversion —
it does not alter the music.

```
python3 mod2header.py yoursong.mod song_4.h
```

The second argument is optional; if omitted it writes `yoursong.h`. To change a
demo's music, convert your MOD directly to the matching `song_N.h` (see the
table above), then recompile. To change the menu music, target `song_0.h`.

### Where to find MODs

- **The Mod Archive** (modarchive.org) — tens of thousands of tracks; filter by
  license (prefer public domain / Creative Commons for anything you'll publish)
  and by file size (leaner tracks make smaller headers and faster compiles).
- **Compose your own** in a tracker — **MilkyTracker** runs natively on macOS
  (including Apple Silicon) and Windows/Linux, exports 4-channel MODs, and is
  free.

### Notes on file size and editing

The bulk of a MOD's size is its **sample data**, not its pattern/song length.
To shrink a header:

- Prefer choosing a natively small MOD over trimming a large one.
- In a tracker, the biggest lever is **downsampling** the largest samples in the
  Sample Editor (roughly halves their size per octave of rate reduction);
  trimming silence and tightening loops also helps.
- Shortening the **order list** (how many patterns play in sequence) plus
  deleting the now-unused patterns/samples reduces size only modestly, but is
  the right tool for fitting a track's *length* to a demo.

pocketmod loops a MOD automatically at its end, so a clean **loop point** often
matters more than absolute length. Whatever you edit, listen to the loop seam
(play to the end and let it wrap) before converting to a header.

MOD editing tools:

- **MilkyTracker** (milkytracker.org) — native macOS/Windows/Linux; loads MODs,
  edits samples and order lists, exports MOD.
- **OpenMPT** (openmpt.org) — Windows only (runs on macOS via CrossOver/Wine);
  the most capable option for multichannel editing and for down-converting
  richer formats like S3M to MOD, with per-channel control.

---

## Creating the rotozoom image

The Rotozoom demo tiles and spins a **128×128 pixel** source image stored in
`texture.h` as an RGB565 array.

### Image requirements

- **Exactly 128×128 pixels** (power-of-two — the demo wraps with a fast bitwise
  mask, `TEXTURE_MASK 0x7F`, instead of division)
- **24-bit uncompressed BMP** (Windows/DIB), no alpha, no RLE
- **Bold, high-contrast content** — thick shapes, chunky patterns, or a strong
  central subject. Rotozoom blurs fine detail, so thin lines alias badly and
  very dark images disappear. Concentric shapes, mandalas, chunky pixel art, or
  a bold face/logo all work well.

### Making the BMP

Any image editor works — Photoshop, GIMP, Affinity, Procreate, Pixelmator.
Create or resize to 128×128 and export/save as **BMP, 24-bit, uncompressed**.

### Converting the BMP to `texture.h`

A helper script, `bmp2texture.py`, bakes the image into the C header the sketch
expects. It reads the BMP, handles its bottom-up row order, converts each pixel
to RGB565, and writes the `texture[128][128]` array with the `TEXTURE_W`,
`TEXTURE_H`, and `TEXTURE_MASK` defines.

```
python3 bmp2texture.py yourimage.bmp texture.h
```

The second argument is optional and defaults to `texture.h`. The script
validates its input and will refuse anything that isn't a 128×128, 24-bit,
uncompressed BMP — with a message telling you what to fix (wrong size, wrong bit
depth, or compression enabled). Overwrite the project's `texture.h` with your
converted version and recompile to change the rotozoom image.

---

## Credits and links

- **Music** — original tracker modules by **kqvc**, composed for this project.
- **Juggler raytracer** — original by **Eric Graham**, 1987 (public domain with
  attribution). Source archive:
  github.com/AlphaPixel/Eric-Graham-1987-Juggler-Raytracer-1.0
- **pocketmod** — MOD player by rombankzero (MIT):
  github.com/rombankzero/pocketmod
- **MilkyTracker** — milkytracker.org / github.com/milkytracker/MilkyTracker
- **OpenMPT** — openmpt.org
- **The Mod Archive** — modarchive.org
- Built on the **arduino-pico** core by Earle Philhower:
  github.com/earlephilhower/arduino-pico
- Inspired by Future Crew's **Second Reality** (1993) and the Amiga/DOS
  demoscene generally.

---

## File map

| File | Role |
|------|------|
| `demofruit.ino` | Main sketch: boot dispatch, display construction, demo launch |
| `common.h` | Buttons, launch scratch registers, memory arenas, PSRAM timing fix |
| `launcher.h` | The menu: tumbling cube background + text + navigation |
| `leds.h` | NeoPixel status-strip helpers and UI grammar |
| `audio.h` | Codec + I2S setup and the non-blocking music pump |
| `starfield_impl.h` | Starfield demo |
| `plasma_impl.h` | Plasma demo |
| `raytracer_impl.h` | Chrome Sphere demo |
| `valley_impl.h` | Valley Run demo |
| `rotozoom_impl.h` | Rotozoom demo |
| `juggler_impl.h` | The Juggler (renderer + scene + kinematics + playback) |
| `texture.h` | 128×128 RGB565 source image for Rotozoom |
| `song_0.h` … `song_6.h` | Per-slot MOD music (menu + six demos) |
| `pocketmod.h` / `pocketmod.c` | MOD player (MIT) |
| `mod2header.py` | Converts a `.mod` file into a `song_N.h` header |
| `bmp2texture.py` | Converts a 128×128 BMP into `texture.h` for Rotozoom |
