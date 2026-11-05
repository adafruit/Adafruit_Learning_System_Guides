# FM-1 Flasher

A portable CircuitPython device that installs alt firmwares on the M-VAVE FM-1, with no computer needed. It keeps the firmwares on a microSD card, downloads new ones from the [FM-1 Firmware Hub](https://thefirmwarehub.com/) over WiFi, and installs them over USB MIDI SysEx. Plug the FM-1 into the flasher, pick a firmware on the touchscreen, and tap Install.

## Hardware

- [Adafruit Metro ESP32-P4](https://www.adafruit.com/product/6536), running the flasher's CircuitPython 11 build (a ready-made UF2 from the guide, or built with the changes in [`patches/`](patches/README.md)). Stock CircuitPython can't run the flasher yet.
- [Adafruit 2.8" TFT Touch Shield, capacitive](https://www.adafruit.com/product/1947) (ILI9341 320x240, FT6206 touch), stacked on the Metro. No jumpers or wiring.
- A microSD card in the Metro's own slot, for the firmwares. Any FAT card works; an empty one fills itself from the hub.
- The FM-1 plugs into the Metro's USB-A host port with an ordinary USB cable.
- Power from USB-C, the barrel jack, or a LiPo on the Metro's battery connector.

## What it does

- **Browse** the firmwares on the card as picture cards or a two-column list. Swipe between pages, or drag them with Settings > Scroll pages on. Filter by type (synth, drums, sequencer and so on) or favourites, and sort A-Z, New (newest on the hub) or RcntUp (most recently updated).
- **Details** for each firmware: the picture, author, version, license and description (drag up and down for long ones), a favourite heart, and Remove, which takes it off the card after asking. M-VAVE's stock V15 can't be removed: it's the way back to the factory firmware.
- **Install:** tap Connect FM-1, then Install. The flasher checks the package, puts the FM-1 into its loader, writes the firmware and waits for the FM-1 to restart. V15 → SLOOP takes about 50 s, SLOOP → V15 with the factory voices about 46 s.
- **Catalog:** downloads new firmwares and new versions from the hub over WiFi. Details lists what it would fetch, with tick boxes, All and None, a type filter and an Info button for each. Firmwares are only ever added or updated: one the hub drops, or one you removed, is never deleted or brought back by itself.
- **Settings:** WiFi (scan, type a password on the on-screen keyboard, up to 8 saved networks), Scroll pages, and Credits.

Installs from V15 and to community firmwares that use a different loader (such as Skiff) are handled. Firmwares the hub sends to their own installer page (such as FIZZ) aren't downloaded, because their package alone isn't enough.

## Setting it up

1. **CircuitPython.** Download the flasher's UF2 from the guide (or build it, following [patches/README.md](patches/README.md)). For the METROP4BOOT drive, tap Reset, wait for the LED to turn purple, and tap Boot while it's still purple. Copy the UF2 to the drive. [patches/README.md](patches/README.md) also covers a Metro that has no TinyUF2 bootloader yet.
2. **The flasher.** `FM-1_Flasher_Code/` is laid out as CIRCUITPY: `code.py`, `lib/` (the flasher's own `fm1ui` and `fm1*` modules), `fonts/` and `splash.bmp`. Either copy it with the guide's Project Bundle, which also brings the libraries from the CircuitPython bundle (`adafruit_ili9341`, `adafruit_focaltouch`, `adafruit_bus_device`, `adafruit_usb_host_descriptors`, `adafruit_requests`, `adafruit_connection_manager`), or, with those libraries already on the board, deploy from this folder:

   ```sh
   python3 tools/deploy.py --mpy-cross path/to/circuitpython/mpy-cross/build/mpy-cross
   ```

   `deploy.py` compiles `lib/` to `.mpy` with the mpy-cross from your CircuitPython build, which saves RAM and start-up time, and copies `code.py`, the fonts and the splash.
3. **settings.toml.** Add `CIRCUITPY_SDCARD_USB = false` (`deploy.py` does it for you), so the card doesn't show up over USB while the flasher uses it. Take the card out and use a card reader to look at it from a computer. It takes effect after a reset.
4. **WiFi.** Join a network in Settings > WiFi, or put `CIRCUITPY_WIFI_SSID` and `CIRCUITPY_WIFI_PASSWORD` in CIRCUITPY's `settings.toml`.
5. **Firmwares.** Put in a microSD card and tap Catalog. A card with no firmware on it starts there.

Flashing firmware carries a risk of leaving the FM-1 unbootable. Keep both devices powered during an install.

## Documentation

- [docs/PLAN-v2.md](docs/PLAN-v2.md): the plan and status for the Metro flasher.
- [DEVNOTES.md](DEVNOTES.md): what we tried and learned, with evidence (mostly from the Feather version).
- [fm1-firmware-flasher-brief.md](fm1-firmware-flasher-brief.md): the FM-1's update protocol and package format.
- [patches/README.md](patches/README.md): the CircuitPython build.
- The project's history up to its move here, with its pull requests and tags: [jedgarpark/FM-1_Flasher](https://github.com/jedgarpark/FM-1_Flasher).

The folders: `FM-1_Flasher_Code/` goes on the board; `tools/` (deploy, the simulator, making SD cards, fonts and the splash) and `tests/` run on a computer, and `tools/device/` holds REPL scripts from the bring-up. `tools/` and `tests/` are left out of the Learn Guides lint check (`.circuitpython.skip`).

## Development

```sh
git clone https://github.com/m-vave/fm1_open ref/fm1_open    # reference updater and stock V15 (gitignored)
git -C ref/fm1_open checkout 4c7496daac04a95ff10d1afdcc8f9ead2dbabc41
python3 -m unittest discover -s tests                         # protocol, package, and simulated install tests
FM1_TEST_PKGS=path/to/fwsc/folder python3 -m unittest discover -s tests   # also run real packages
node tests/make_golden.mjs                                    # regenerate golden vectors from WebUpdate.js
```

### Trying the UI on the desktop

`tools/ui_sim.py` runs the same `FM-1_Flasher_Code/lib/fm1ui` screens in a window, with the mouse as your finger: tap, and drag sideways to swipe. The FM-1 is faked and an install only animates the progress screen, so nothing is flashed. It needs the dev venv with the Blinka displayio packages, pygame and Pillow (see the script's docstring).

```sh
.venv/bin/python tools/make_sd.py --out sd_out/full --catalog     # once, and to refresh: a local copy of the card
.venv/bin/python tools/ui_sim.py                                  # reads sd_out/full/firmware
.venv/bin/python tools/ui_sim.py --root /Volumes/FMFLASH/firmware # or a card in a reader
.venv/bin/python tools/ui_sim.py --identity none                  # start with no FM-1 plugged in
.venv/bin/python tools/ui_sim.py --root copy/of/firmware --hub    # with Catalog and Settings, using the real hub (writes to --root)
```

Keys in the window (the title bar shows the FM-1's state):

| Key | What it does |
|---|---|
| `f` | Plug or unplug the FM-1. Then tap Connect FM-1. After an install it answers as the new firmware. |
| `x` | Fail the install that's running, to see the error screen. |
| `s` | Stall: the FM-1 doesn't come back after its restart, so the install waits there and shows the power-cycle hint after 20 s. Press `s` again to let it finish. |
| `h` | List the keys in the terminal. |

Favourites and the list view are saved in `flasher-sim.json` next to the firmware folder, apart from the card's `flasher.json`. The simulator draws the Metro's 320x240 screen. It doesn't model the device's speed.

With `--do` steps it runs without a window and saves screenshots, for checking a layout change: `--do "tap 100,100" --do "shot detail.png"`.

### Preparing a card from a computer

The flasher fills its own card, but `tools/make_sd.py` can also write one from a computer, through a card reader (it needs Pillow for the card pictures):

```sh
tools/make_sd.py --out /Volumes/SDCARD --catalog                 # every firmware on the hub, plus M-VAVE V15
tools/make_sd.py --out /Volumes/SDCARD --catalog sloop felucca   # just these
tools/make_sd.py --out /Volumes/SDCARD --fwsc ref/fm1_open/sdk/firmware/FM-1_015.fwsc \
    --name "M-VAVE V15 (stock)" --author M-VAVE --slug stock-v15
```

Each firmware goes in `firmware/<slug>/` as the `.fwsc` and a `meta.json`, and `firmware/index.txt` lists them. Every package is checked the same way the device checks it. Packages already on the card are kept when their SHA-256 still matches the catalogue, so a rerun only downloads what's new or changed.

## The Feather version (deprecated)

The first flasher ran on an Adafruit Feather RP2040 USB Host (and later a Feather RP2350 with the MAX3421E USB Host FeatherWing) with the 3.5" TFT FeatherWing V2. It worked, but V15 needed a long USB cable on its PIO host port, the SD card shared a bus with the display, and it had no WiFi. The Metro replaced it. Its last tested version is the tag [`v1-feather-final`](https://github.com/jedgarpark/FM-1_Flasher/tree/v1-feather-final), with its hardware notes, patches and [PLAN.md](PLAN.md); DEVNOTES.md has the evidence.

## License

GPL-3.0. The update protocol is ported from M-VAVE's `WebUpdate.js` (GPL-3.0-only WITH GPL-3.0-linking-exception). Each firmware keeps its own license.
