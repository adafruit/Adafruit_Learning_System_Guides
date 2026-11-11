# FM-1 Flasher v2: plan (Metro ESP32-P4)

A second flasher on an Adafruit Metro ESP32-P4 with the 2.8" TFT Touch
Shield, which downloads firmwares from thefirmwarehub.com itself over WiFi.
The v1 Feather flasher (PLAN.md) is deprecated as of 3 November 2026: the
Metro does everything it did and more, and its changes since #40 were never
tested on the Feather. Its last tested version is the tag
`v1-feather-final` (03eb577, before #40). The Feather-only code was removed
on 4 November 2026: its hardware in `fm1ui.device` (now it takes everything
from `fm1ui.metro_p4`), the 480x320 layout and the layout switches only it
used, the Feather and Pico REPL scripts in `device/` (now `tools/device/`), its CircuitPython
patches (`patches/` now holds the Metro build's two), and the Feather parts
of `deploy.py`, `make_splash.py` and `ui_sim.py`. `fm1usb` clears the
endpoints' data toggles on every board now. The Feather-era RAM workarounds
(the install through a reload, the picture pool, packed fonts) are still in
place: relaxing them is the next piece of work.

## Hardware

**Metro ESP32-P4 "Hydra" (Adafruit 6536).**
- ESP32-P4 "v1" (not P4X): two 360 MHz RISC-V cores, 16 MB flash, 16 MB PSRAM.
- WiFi: ESP32-C6 coprocessor over SDIO (ESP-Hosted); CircuitPython
  `wifi`, `socketpool`, `ssl`.
- USB-A host: the P4's high-speed USB 2.0 controller (TinyUSB instance 1),
  software-controlled 5 V (`board.USB_HOST_POWER`) with a boost converter
  for battery use.
- microSD on the board: 4-bit SDIO (`sdioio`, `board.SD_*`, card detect
  `board.SD_CD`), on pins of its own.
- SPI on a separate 6-pin header (`board.SPI()`: GPIO15/16/17), not D11-D13.
  I2C on SDA/SCL (GPIO33/32).
- Barrel jack, USB-C, or a LiPo with charging; `board.VOLTAGE_MONITOR`.
- CircuitPython support since 11.0.0-alpha.2 (adafruit/circuitpython#11643).
  The port is alpha.

**2.8" TFT Touch Shield, capacitive (Adafruit 1947).**
- ILI9341, 320x240, SPI: CS D10, DC D9. SPI comes from the ICSP 2x3 header
  by default, which should mate with the Metro's 6-pin SPI header.
- Touch: FT6206 on I2C at 0x38 (`adafruit_focaltouch`). Newer shields may
  have a CST026; check which one this shield has.
- Backlight always on unless the "Pin 5" jumper is soldered (then D5).
- Its own SD slot (CS D4) isn't used: the Metro's SDIO slot is better.

## What v2 fixes

| v1 (Feather RP2350) | v2 (Metro ESP32-P4) |
|---|---|
| PIO-USB or MAX3421E host; V15 trouble on short cables | Native USB host controller |
| SD card shares SPI with the display and host chip; stale sectors, a wiped card (DEVNOTES §6.16-6.18) | SD card on its own SDIO bus |
| ~337 KB RAM: packed fonts, an 80 px picture pool, soft reload before installs (§6.11) | 16 MB PSRAM |
| Refreshing the card needs a computer and `make_sd.py` | Update firmwares from the hub on the device |

## Risks

1. **Enumeration buffer.** The Metro P4 build uses the 288-byte default
   `CFG_TUH_ENUMERATION_BUFSIZE`, so stock firmware shouldn't mount the FM-1
   (293-byte configuration descriptor). A per-board setting, as Fruit Jam
   has (4096), is an easier upstream ask than the global default (#11697).
2. **Enumeration retry.** v1 needed a TinyUSB enumeration retry. It may have
   been a PIO-USB timing problem that the native controller doesn't have.
3. **Alpha port:** WiFi over the coprocessor, high-speed host and `sdioio`
   are new on this chip.
4. **Card pictures:** the hub's are PNGs, and CircuitPython has no built-in
   PNG decoder. `adafruit_imageload` decodes PNG in Python; maybe too slow
   for ~150. Options: decode on first view and cache a BMP, or ask the hub
   for small BMPs or JPEGs (`jpegio` is built in).
5. **Physical fit:** whether the Metro's microSD slot can be reached with
   the shield on, whether the shield's ICSP socket mates with the Metro's
   SPI header, and whether the USB-A port and barrel jack clear the shield.
6. **Screen:** 320x240 is two-thirds of v1's 480x320 each way; the layouts
   need rework. Full-screen refreshes should be faster (half the pixels).

## Phase 0: Spikes (go/no-go, REPL scripts, no UI)

Bench setup: the Metro came without TinyUF2 (double-click reset did
nothing). BOOT + Reset gives the ROM loader (no drive); TinyUF2 0.36.0's
`combined.bin` was written at 0x0 with `esptool`, then a plain Reset gives
METROP4BOOT. This board's chip reports revision v0.1, which TinyUF2 and
CircuitPython accept.

- [x] Display and touch (`tools/device/metro_spike_display.py`): `board.SPI()`
      through the ICSP header with no jumpers (CS D10, DC D9, 40 MHz); a
      full-screen refresh takes 65 ms. Touch is an FT6206 (`adafruit_focaltouch`,
      0x38, chip ID 0x06) reporting portrait: screen x = 319 - raw y,
      screen y = raw x.
- [x] USB host: **passes with a custom build** (`ref/cp-metro-p4`, branch
      `fm1-metro-p4`: upstream `main` + a 512-byte enumeration buffer + a
      TinyUSB fix). From the REPL (`tools/device/metro_install.py`, 64-byte writes),
      with no lost replies or resends:

      | Install | Metro ESP32-P4 | v1 (Feather) |
      |---|---|---|
      | V15 → SLOOP | 52.2 s | 70-84 s |
      | SLOOP → V15 with factory voices | 49.4 s | 73-85 s |

      What it took:
      - **Enumeration buffer.** On the stock build (288 bytes) the FM-1
        doesn't enumerate; a keyboard does. With 512 the FM-1 (V15,
        `4c4a:c755`) enumerates in 0.2 s.
      - **TinyUSB: cancelling a running bulk IN.** With host DMA, a
        `read()` that timed out wasn't cancelled: `hcd_edpt_abort_xfer()`
        set channel disable and returned, and the halt arrived with NAK set,
        so `handle_channel_in_dma()` re-armed the channel. The stale read took
        the reply to the next query, later writes returned its length
        ("56 of 16 bytes") and reads never completed until a replug; and
        CircuitPython had freed the read's buffer. Fix (TinyUSB branch
        `fm1-dwc2-abort`, 943d479be): mark a non-periodic DMA channel
        `aborting`, as for periodic ones, so `handle_channel_irq()` retires it
        at its halt without a completion event, and wait for that halt before
        returning. Tested: 5 query/timeout rounds all answered, 800 1-20 ms
        read timeouts in a row with no error. Upstream TinyUSB has no fix yet.
        Host DMA off instead hard-faults on a soft reboot (tag
        `fm1-metro-nodma-experiment`).
      - **Data toggles (also v1, DEVNOTES §6.9).** The FM-1 stays enumerated
        through a soft reload; the host's endpoints restart at DATA0 and the
        FM-1's don't, so the first query and the first reply are dropped
        (`nnYYY` on each reopen). `fm1usb.CLEAR_HALT` sends
        CLEAR_FEATURE(ENDPOINT_HALT) to both endpoints when a transport opens,
        which fixes it for the apps and the SLOOP loader; the stock V15 loader
        stalls the request ("Pipe error"), so it's best effort, and
        `Updater._open()` now tries identity three times, which covers the
        double mismatch. `CLEAR_HALT` is on for the Metro only until it's
        tested on the Feather.
      - **Open question:** once, two `connect()` calls in a row failed with
        only two identity queries sent, then it didn't happen again in
        several dozen reopens. Not explained.
      - Cutting the host port's 5 V doesn't make a battery-powered FM-1
        disconnect; a clean test needs a cable replug.
- [x] SD card (`tools/device/metro_spike_net.py`): the board doesn't mount it;
      `sdioio.SDCard` (4-bit, 40 MHz) plus `storage.mount` does. 1 MB writes
      at 1.6-1.75 MB/s, reads at 6.9-7.7 MB/s. The full package checks on
      SLOOP (610 KB) take 2.3 s. Card detect (`board.SD_CD`) reads low with
      a card in.
- [x] WiFi (`tools/device/metro_spike_net.py`): `catalog.json` (148 firmwares,
      290 KB) in 3.6 s; SLOOP 2.8.4 streamed to the card at 0.21 MB/s with a
      matching SHA-256 (a full card, ~90 MB, would take ~7 min); 15 MB free
      RAM. The hub's picture (480x480 full-colour PNG, 4 KB) takes 9.3 s to
      decode with `adafruit_imageload`: too slow to do all ~150 at once
      (~23 min). Decode on first view and cache, or ask the hub for small
      BMPs. One hard fault into safe mode right after WiFi credentials were
      first added to `settings.toml`; it didn't recur after a reset.

## Phase 1: Port (done)

On the Metro from the touchscreen (logs/metro-p4-ui-20261102b.log): V15 →
SLOOP in 50.5 s and SLOOP → V15 with factory voices in 46.2 s. After each
reload the FM-1 answered the first identity query (v1 needs three). The
user found the screens good on the 2.8" panel.

- [x] Board-specific parts: `fm1ui/metro_p4.py` (ILI9341 display, FT6206
      touch, SDIO card, USB host, splash). `fm1ui.device` takes them over v1's
      when `board.board_id` is the Metro's, so v1 never loads them.
      `fm1proto`, `fm1update` and `fm1usb` are shared (`fm1usb.CLEAR_HALT` on).
- [x] Layouts: every size and position in `fm1ui/layout.py`, chosen by the
      display's size. v1's 480x320 is unchanged (all 11 simulator screens
      pixel-identical before and after). 320x240: no header title, 3x2 cards
      of 100x82 with 40 px pictures (`ui.shrink` halves the 80 px thumbnail),
      12 names a page in the text list, the 80 px picture on the details
      screen, notes that wrap to two lines. `ui_sim.py --size 320x240`.
- [x] Relax v1's RAM workarounds on the Metro (16 MB free). Installs run
      in place from the confirm screen (4 November 2026): no reload before
      or after, the NVM handoff and `fm1ui/console.py` are gone, and OK goes
      back to the firmware's details and reconnects to the FM-1. Each
      install opens a fresh transport, and closes it and the package file
      itself. The identity check before writing gets three tries (Aisling
      once didn't answer it). On the details of the firmware the FM-1 runs,
      Back is outlined in cyan and Install again is a plain button. Tested:
      V15 → Aisling 49.0 s, → V15 44.7-48.3 s, V15 → Skiff 80.5 s,
      → Clatter 39.1 s, → ChoralRoot 49.1 s. The picture pool and packed
      fonts stay.
- [x] `deploy.py` reads the board from `boot_out.txt` (`--board` overrides) and
      writes its splash; `make_splash.py --size 320x240` →
      `art/splash_text_320.png`. Deploy with the Metro build's mpy-cross
      (`ref/cp-metro-p4/mpy-cross/build/mpy-cross`); the Metro also needs
      adafruit_ili9341, adafruit_focaltouch, adafruit_bus_device and
      adafruit_usb_host_descriptors from the bundle.

## Phase 2: Update firmwares on the device

- [x] Move the catalogue logic out of `make_sd.py` into a shared
      `fm1catalog.py` for CPython and CircuitPython, with swappable fetch
      and file access (also usable by a web page later).
- [x] An Update firmwares screen: WiFi, a plan ("12 new, 3 updated,
      8 MB"), downloads with progress, SHA-256 against the
      catalogue plus the full package checks, pictures, `index.txt`, and
      no removals: a firmware the hub drops or moves to its own installer
      stays on the card until its owner deletes it (also in `make_sd.py`).
- [x] Resumable: write to a temporary name, then rename, so a power cut
      leaves a working card.
- [x] WiFi credentials from `settings.toml`. Offer to fill an empty card at
      first start (tested in the simulator, not yet on the Metro).
- [x] On-screen WiFi entry: Settings (the gear on the list) > WiFi scans,
      takes the password on an on-screen keyboard and keeps up to 8
      networks in NVM, not on the card; Update joins the most recently used
      one in range. Tested on the Metro, joining a second network elsewhere
      on battery (3 November 2026).

Result (2 to 3 November 2026): the Metro brought a card made on 29 October
up to date over WiFi, 31 new and 45 updated firmwares (46.4 MB), about 9 s
per firmware with all checks, then the pictures (about 5 s each, PNG decoded
and reduced on the device). Afterwards the card held all 145 firmwares the
catalogue had then, with no `.part` files left; the only differences from
the hub were 10 firmwares it added or updated later that day. Pictures:
137 converted, 7 marked as missing on the hub.

## Scrolling pages (done, 3 November 2026)

- [x] The list's pages follow the finger and glide to the next page, with
      Settings > Scroll pages to turn it off. displayio draws the list's cards
      (shapes and text) at 10 fps whatever the SPI clock, so each page is
      drawn once into one bitmap (`fm1ui/flat.py`): 22 fps at 40 MHz, 29 fps
      at 80 MHz, 17-24 fps while dragging (`tools/device/metro_spike_scroll.py`).
      The display now runs at 80 MHz, clean on the shield. Metro only.

## Phase 3: Battery and release

- [ ] Low-battery warning from `VOLTAGE_MONITOR`; installs on battery
      through the host port's boost. **Shelved for later (4 November 2026).**
      What we know so far: `board.VOLTAGE_MONITOR` is GPIO18. With a LiPo
      attached (and USB in) it reads a steady 1.859 V at the pin (raw
      ~36940 of 65535, 3.3 V reference), 3.72 V if the divider halves it,
      which fits a LiPo; /2 still needs checking against a multimeter or
      the schematic. With no battery the reading jumps around (raw
      41000-64000, ~4.5 V doubled): that's the charger output, not a
      battery. USB raises the reading while the battery charges, and no
      other pin was found that tells USB from battery, so the warning
      should just stay quiet when the reading is high. Proposed design:
      the median of ~50 quick samples (ignores the odd spike) every ~30 s,
      a header battery icon that turns red below ~3.5 V, and a
      confirmation before an install below ~3.4 V.
- [ ] Soak tests across many firmwares, a Learn Guide section, a release.
      Explained (4 November 2026): some installs stop during staging
      ("device stopped requesting data" after 4 requests; nothing written)
      because of the FM-1's flash "head". The four packages with M-VAVE's own
      loader (V15, Bubba, Amenity, Clatter; the hub's `"loader": "mvave"`)
      rewrite the first 16 KiB of flash, and carry one of two heads: V15's
      (V15, Bubba) or Amenity's (Amenity, Clatter). Felucca-based firmwares
      (SLOOP: `ota_stage()` in its `firmware/src/ota.c` returns -5, "update
      failed -5" on its screen; ZP12 and Duell behave the same) refuse to stage
      such a package unless its head equals the one on the FM-1. Firmwares
      built on V15 (V15, Bubba, Amenity, Clatter) don't check. So: Felucca-loader
      firmwares (149 of 152) install from anything; an M-VAVE-loader one
      installs from V15 or another of the four, and from a Felucca-based
      firmware only if the last of the four installed shares its head. Stuck:
      install the last of the four you had, then go on from it. Confirmed on
      the hub's web installer, step by step (V15 → SLOOP → V15 → Clatter →
      SLOOP → V15 refused → Amenity → V15 → SLOOP → Bubba), and it explains the
      Duell → Amenity and ZP12 → V15 stalls. USB rescue (OCT−, FM-1_000) is no
      way round. The hub's installer also loses a firmware whose USB name is
      "FM1 Community" (Clatter) after installing it: its port list has "fm-1".
- [x] The confirm screen warns when the running firmware will refuse an
      install because of the head, and names the way round first ("Install
      Amenity first, then M-VAVE V15. SLOOP will refuse it: the FM-1's start-up
      code differs."); Install stays available. `fm1ui.heads`: each package's
      loader (M-VAVE's own is known by its header CRCs and length, as SLOOP
      knows it: `fm1proto.official_loader`) and head CRC (`flash_head`), read
      once per version; the FM-1's head is the one the last M-VAVE-loader
      install wrote (kept in the state as `head`), or V15's without a record
      ("probably"); while a firmware with M-VAVE's loader runs, its own.
      Bubba Machine (FM-1_003) has an updater of its own, stricter still: it
      takes only packages with M-VAVE's loader and the FM-1's head (its
      `hal/fm1/fm1_update.c`: -5, -7), so Bubba → SLOOP stops after 3
      requests; the way off Bubba is V15 first. `fm1ui.heads.UPDATERS` lists
      firmwares like it, whose updater can't be told from their package.
- [ ] Tell zvenson (the hub's Back to official V15 and its rescue tip can't
      get past this; the "FM1 Community" port name), and Amenity's and
      Clatter's authors (their head differs from V15's).

## To look into

- [x] Sort the lists: A-Z, New (newest on the hub first) and RcntUp
      (newest release first). meta.json keeps the catalogue's `added` and
      `date`, and `index.txt` carries them as two more columns (older cards'
      six-column lines still read, and sort last). A Sort button in the
      header beside the tag and favourites tabs steps through the three
      (the favourites tab is now just the heart); the choice is
      kept in the state. Update firmwares copies the dates into an older
      card's unchanged firmwares (at once when there's nothing to download).

- [x] Move the OK button after an install from the centre to the right,
      where Install is on the details screen: a centred OK sat over the
      list's Catalog button, so the tap that closed it often opened Catalog
      too (user report, 4 November 2026). OK reloads the code, and the touch
      came through to the new list; `fm1ui.app.Gestures` now also ignores a
      touch that's already down when it starts, until it lifts.

## Moving to the Learn Guides repo

- [ ] The project moves to `adafruit/Adafruit_Learning_System_Guides/FM-1_Flasher`
      (4 November 2026), as `CircuitPython_Turbo` did: notes, tools, tests and
      patches come along. `FM-1_Flasher_Code/` is the guide's Project Bundle,
      laid out as CIRCUITPY. The Learn repo's checks pass (its SPDX script, and
      pylint 2.7.1 on Python 3.10 with its `.pylintrc`; `.github/workflows/learn-checks.yml`
      runs them here). `tools/` and `tests/` are marked `.circuitpython.skip`.
      The PR also adds `LICENSES/GPL-3.0-only.txt` at the Learn repo's top
      level. Then `jedgarpark/FM-1_Flasher` is archived with a pointer, so the
      upstream links, the tags and the `firmware-20261102` release keep working.

## Upstream and the hub

- [x] Ask for a Metro P4 board-level enumeration buffer (512, or 4096 like
      Fruit Jam), so v2 runs on stock CircuitPython: adafruit/circuitpython#11751
      (4 November 2026), the one line in `patches/cp11-metro-p4-enum-bufsize.diff`.
      Merged the same day (66688d5d05, approved by mikeysklar): CircuitPython
      `main` from then on, and the next 11.x release, mount the FM-1 on the
      Metro with no patch.
- [ ] Once a CircuitPython build with 66688d5d05 is out, try it on the
      Metro without the TinyUSB fix: installs are expected to fail (a
      timed-out read isn't cancelled), but a test settles it for the guide.
- [x] The TinyUSB DWC2 abort fix (`patches/tinyusb-dwc2-abort.diff`):
      reported as hathach/tinyusb#4405, and proposed as hathach/tinyusb#4430
      (4 November 2026, the same change rebased onto master; tested on the
      Metro only on the version CircuitPython pins). The bot reviews
      (CodeRabbit, Greptile) asked for the abort comment to say what happens
      when the wait for the halt times out; two comment-only commits did
      that (head 853253566), and both bots approved (6 November 2026). CI
      passes (56 checks, 1 skipped). On 8 November hathach added six
      commits after his own review: hub (split) transactions finish before
      an aborted channel is retired, the wait also stops after 8 ms, and
      SETUP/clear-stall are refused while an abort waits. That head
      (e848a1b15), on the TinyUSB CircuitPython pins, passed V15, SLOOP and
      community installs on the Metro, direct and through a USB hub
      (8 November). HiFiPhile proposed folding it into his
      hathach/tinyusb#4265, which rewrites the same abort code, and closing
      #4430; we agreed and offered to rerun the installs against the
      #4265 head. Hathach agreed too (9 November): the commits move to
      #4265 with authorship kept, `Fixes #4405` with them, and #4430 closes
      once #4265 carries the change. Ported the same day (our commit
      e4c01c9e3 plus his adaptations; #4265 now says it fixes #4405).
      CircuitPython builds cleanly against #4265's head (faedfe71d, 314
      commits past its pinned TinyUSB), and on the Metro ChoralRoot, V15,
      SLOOP and Skiff installs all passed, direct and through a USB hub
      (reported on #4265, 9 November). #4265 merged on 10 November
      (squashed as bab06c109 on TinyUSB master, "Fixes #4405"); #4405 and
      #4430 are closed. CircuitPython re-pin of `lib/tinyusb` to
      12611f81a (TinyUSB master with bab06c109): adafruit/circuitpython#11836,
      opened 10 November after mikeysklar's 8-board farm run (USB serial
      and CIRCUITPY, no errors) and FM-1 installs on the Metro; it also
      turns off audiopwmio on two ESP32-S2 boards that ran out of internal
      RAM. Merged 11 November (92da735b06). Next: the stock build replaces
      the custom UF2.
      His list for the port
      includes a timing issue behind a hub (the abort wait is only ~1 ms
      there, so an aborted split can still be aborting when the next SETUP
      comes), worth watching in the rerun; the hub's TT buffer recovery is
      left to hathach/tinyusb#4455. His hardware tests don't reach the
      #4405 case itself, so the FM-1 installs are its only test so far.
      Once it's merged, CircuitPython still has to update its pinned
      TinyUSB; until then the flasher needs the custom build.
      That build is a ready-made UF2 for the guide (4 November 2026):
      `main` at 66688d5d05 plus the fix, tested on the Metro with installs
      between V15 and community firmwares (`patches/README.md`).
- [ ] Tell the hub's maintainer that flashers will download from the hub
      directly, and ask about the pictures (PNG CORS/BMP/JPEG).
