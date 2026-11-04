# FM-1 Flasher: plan

> **Deprecated (3 November 2026).** This is the plan for the v1 Feather flasher, kept for reference. Work continues on the Metro ESP32-P4: see [docs/PLAN-v2.md](docs/PLAN-v2.md). The last version tested on the Feather is the tag `v1-feather-final`.

See `fm1-firmware-flasher-brief.md` for the protocol and package format, and
**`DEVNOTES.md` for the history: what we tried, what we learned, and the
evidence**. This file is the plan and the current status.

Guiding idea: prove the protocol from a computer first, so USB-host problems and protocol problems are never debugged at the same time.

## Hardware

- **Main setup: Adafruit Feather RP2350 + MAX3421E USB Host FeatherWing ([PID 5858](https://www.adafruit.com/product/5858)) + TFT FeatherWing V2**, on CircuitPython 11 with `cp11-feather-rp2350-max3421e.diff`. Works with a short cable:
  - 9 of 9 FM-1 power cycles, about 400 KB free from the REPL (DEVNOTES §6.15).
  - Six installs from the touchscreen, with 338 KB free: V15 → SLOOP → V15, Choralroot → Grimm, Grimm → Golana → Grimm, Grimm → DRIFT (§6.16–6.18).
  - With `CIRCUITPY_SDCARD_USB = false` (set by `tools/deploy.py`), package checks take 1.3 s (§6.18).
  - The wing stays stock (CS D10, IRQ D9). The TFT's CS and DC jumpers are cut and wired to D11 and the D4 position (`board.D12`), since every Adafruit TFT FeatherWing uses D9/D10.
  - The shared-SPI-bus fix in that patch is merged upstream ([adafruit/circuitpython#11695](https://github.com/adafruit/circuitpython/pull/11695)), so once it's in a release only the board settings need a custom build: MAX3421E on, built-in USB host off, 512-byte enumeration buffer.
- **Alternative: Adafruit Feather RP2040 USB Host.** The CircuitPython build must include the TinyUSB enumeration retry and the 512-byte enumeration buffer (`patches/`). Its built-in PIO port needs a long cable or a pigtail (below).
- **USB host for the FM-1**, one of:
  - **The Feather's built-in PIO USB-A port with a long cable** (2 m tested, Adafruit 6279), on CircuitPython 11 with `cp11-feather-pio.diff` and `pico-pio-usb-cp11-idle-disconnect.diff`. A short cable leaves the FM-1 silent, stuck in USB host role (DEVNOTES §6.6–6.7).
  - **A USB-A jack pigtail on D11/D12** (Adafruit 4449, 30 cm), with `cp11-feather-pigtail.diff` instead. Frees the built-in socket.
  - **Adafruit USB Host FeatherWing, MAX3421E ([PID 5858](https://www.adafruit.com/product/5858))**, on CS D10, IRQ D9 and `board.SPI()` (DEVNOTES §4.8). Fine with short cables. Used by the main setup.
- **TFT FeatherWing V2 3.5" 480x320, capacitive touch ([PID 5872](https://www.adafruit.com/product/5872)):** HX8357 display, touch, and microSD. Its TFT CS (D9) and DC (D10) clash with the MAX3421E wing, so the main setup rewires them; with the PIO port or the pigtail it stays stock.
- An M-VAVE FM-1. Before any write, the recovery path is ready (see "Recovery").
- Later: Fruit Jam port. Its USB-A ports hang off a CH334F hub, so the FM-1 would see a real host port rather than a bare PIO port; worth a bench test for the short-cable problem. Optional: 2.4" FeatherWing support behind the same display abstraction.

## Status

| Phase | Status |
|---|---|
| 0: protocol, parser, simulator, SD prep (CPython) | Done (DEVNOTES §2) |
| 1: desktop flasher on real hardware | Done: V15 ↔ SLOOP both ways, rescue path tested (§3) |
| 2: hardware spikes on the Feather | Done: FM-1 enumeration fixed, USB host on the built-in PIO port (MAX3421E also works), long SysEx verified (§4–6.8) |
| 3: install path on device | Done: V15 → SLOOP 70 s, SLOOP → V15 + voices 73 s, V15 → ChoralRoot 69 s (§6). Packages read from microSD |
| 4: UI | Done: touch UI lists, filters and installs the card's firmwares (§6.9–6.11). Open items below |
| 5: hardening, extras | Not started |

## Phase 0: Desk work on CPython, no hardware (done)

`lib/fm1proto.py` (framing, package parsing, streaming reads), `lib/fm1update.py` (install state machine), `tools/fake_fm1.py` (simulator), `tools/make_sd.py` (firmware folders + `meta.json`), and `tests/`. Both install routes, `open`/`stock` and `community`, are implemented; `meta.json` `kind` is `open`, `stock` or `community`.

## Phase 1: Reference flasher on desktop (done)

`tools/flash_cli.py` (python-rtmidi): `ports`, `probe`, and `install DIR` with `--dry-run`/`--force`/`--yes` and a JSONL request log in `logs/`. It installed stock V15 → SLOOP 2.8 in 43 s and SLOOP → V15 with the factory voice restore in 33 s.

## Phase 2: Hardware spikes on the Feather (done)

- **USB host:** the MAX3421E wing with patched CircuitPython 10.3.1, or **on CircuitPython 11 the built-in PIO port** with the 512-byte buffer, 120 MHz and the Pico-PIO-USB disconnect check (`patches/README.md`). TinyUSB on 11 retries enumeration itself. On the PIO port the FM-1 needs a long cable (2 m tested) or the 30 cm D11/D12 pigtail: with a short cable it goes silent in USB host role (DEVNOTES §6.6–6.7). Full installs worked both ways.
- **`fm1usb`:** USB-MIDI SysEx over `usb.core`, since `adafruit_usb_host_midi` can't write SysEx.
- **Long SysEx:** verified with the stress test.
- **`hashlib`:** sha256 is available only as `hashlib.new("sha256")`, which `fm1proto` handles.
- **TFT FeatherWing:** works next to the PIO port. Display, touch and full installs with the console on the screen (DEVNOTES §6.8).
- **Not yet checked:**
  - **Battery operation.** Partly checked on the RP2350 + wing (DEVNOTES §6.19): on a LiPo alone, DRIFT → FOMAJAM installed in 54 s, and the Feather's resets in the first minutes of that session haven't been seen since the white-screen fix (§6.20).

## Phase 3: Install path on device (done)

The touch UI runs installs now (Phase 4). From the REPL, `device/fm1_install.py` still works after `device/fm1_max_setup.py`:
1. verify the package
2. dry run
3. `run(folder, go=True)`

It uses 64-byte paced writes with adaptive slow-down, and prints a ring of recent messages on failure.

Open items:
- [x] Read packages from microSD instead of CIRCUITPY.
- [x] Trust the package checks `make_sd.py` ran when the whole-file SHA-256 matches. The check went from 16–27 s to about 4 s (DEVNOTES §6.10).
- [x] Handle a missing FM-1: Connect FM-1 says when none answers, and a failed install says to power-cycle the FM-1.
- [x] Retry the V15 voice restore once when V15 re-enumerates after its first boot (DEVNOTES §6.7).
- [ ] CircuitPython 11 `hashlib` can give wrong digests on a fragmented heap (DEVNOTES §6.7, §6.9). Worked around: the UI installs after a soft reload, hashes 1 KB at a time and recomputes a mismatch. Still to file upstream with a repro.
- [ ] Optionally start slowed for community firmware and loaders, to avoid the ~3 s loader retry when a reply is lost.
- [ ] Fix the `RealCommunityPackages` test's folder layout (`FM1_TEST_PKGS`).
- [ ] Update the upstream issue draft in `docs/`: the enumeration retry (TinyUSB) and the buffer size (CircuitPython). Post only after review.

## Phase 4: UI (done)

`device/code.py` starts the touch UI in `lib/fm1ui/` (DEVNOTES §6.9–6.11):
- Firmware list as six picture cards or a two-column text list of 16 names a page, with a tag filter, favourites, and the catalogue's date.
- Details screen, Connect FM-1, a confirm screen naming what gets replaced, and "Back to official V15" by installing M-VAVE V15 from the list.
- The install runs after a soft reload, on a fresh heap. The progress screen shows the phase, a bar, elapsed time, "Waiting for the FM-1 to restart…", and the power-cycle hint after a failure.
- Console printing stays off the screen during installs; it slowed the voice restore from 1.8 s to 6.6 s (DEVNOTES §6.8).

Open items:
- [ ] An extra confirmation for legacy routes.
- [ ] A white screen once after replugging the FM-1 during a failed install (§6.9). Not explained.
- [ ] The Mac calls the SD card's drive unreadable after a hard reset (§6.9). Eject is safe.
- [ ] Optional: build the SD card's firmware folder with a GitHub Action, so refreshing the card needs no command line.
- [x] With the MAX3421E wing, resolve its D9/D10 pin clash with the TFT FeatherWing: the wing stays stock (CS D10, IRQ D9); the TFT's CS and DC jumpers are cut and wired to D11 and the D4 position (`board.D12` on the Feather RP2350; D7 is the red LED). `lib/fm1ui/device.py` picks the pins from the build.
- [x] On the Feather RP2350 + wing: rewire the TFT, deploy the UI, and repeat the V15 → SLOOP → V15 round trip from the touchscreen on a short cable. Done, with a fix to CircuitPython's MAX3421E driver for the shared SPI bus (DEVNOTES §6.16).
- [x] Report the MAX3421E shared-SPI-bus bug upstream (CircuitPython), with the fix from `cp11-feather-rp2350-max3421e.diff`: [adafruit/circuitpython#11692](https://github.com/adafruit/circuitpython/issues/11692).
- [x] Find out why the V15 package check took 22.6 s in the UI on the RP2350 (5.3 s from the REPL). The computer was reading the SD card over USB at the same time; `CIRCUITPY_SDCARD_USB = false` (set by `tools/deploy.py`) brings it to 1.3 s (DEVNOTES §6.18).
- [x] Comment on adafruit/circuitpython#11692 that SD-over-USB was on during those tests ([comment](https://github.com/adafruit/circuitpython/issues/11692#issuecomment-6526961492)), mentioning `sdcardio_sdcard_readblocks()` ignoring a lock timeout.
- [x] Send the shared-SPI-bus fix upstream as a PR: [adafruit/circuitpython#11695](https://github.com/adafruit/circuitpython/pull/11695), merged Oct 30 after mikeysklar's tests (with real SD reads: stuck 10/10 before, 0/10 after). Issue #11692 is closed.
- [x] Ask upstream whether the Feather RP2350 build could enable the MAX3421E and the 512-byte enumeration buffer, so a stock CircuitPython works with the wing: [adafruit/circuitpython#11697](https://github.com/adafruit/circuitpython/issues/11697). The MAX3421E and the PIO host can't be built together (duplicate `hcd_*` symbols), so it would cost the board `usb_host.Port`.
- [ ] Optionally report `sdcardio_sdcard_readblocks()` ignoring a lock timeout as its own issue (FatFs gets stale sectors; DEVNOTES §6.18).
- [ ] Follow #11697 for a stock-firmware path. Long term, tannewt wants one build that supports either host driver ([comment](https://github.com/adafruit/circuitpython/issues/11697#issuecomment-6584031005)); he asked hathach about several host interfaces in TinyUSB and mikeysklar about Zephyr. A custom build is frozen: nothing rebuilds it ([comment](https://github.com/adafruit/circuitpython/issues/11697#issuecomment-6581766327)). Until then the Learn Guide uses the custom UF2 (DEVNOTES §6.21).
- [ ] Raising the default `CFG_TUH_ENUMERATION_BUFSIZE` from 288 to 512 upstream (mikeysklar's suggestion; 224 more bytes of RAM): waiting for tannewt or dhalbert to weigh in on #11697 before offering a PR. Nothing here depends on it, since the custom build sets 512 itself. Without it, the `build-board-custom` workflow can't make a working build: its flags can't set the buffer.
- [x] Build the Learn Guide's firmware: upstream `main` plus three board lines, built locally (DEVNOTES §6.21).
- [ ] Give the UF2 a permanent home (for example a release of this repo) and link it from the guide. Rebuild it the same way when a CircuitPython release includes #11695.
- [ ] Write the UI's install log to the SD card as well, so a failure without a computer attached leaves a record (one V15 install in five failed unlogged, §6.21).
- [x] A splash screen at start-up: "FM-1 FIRMWARE FLASHER", purple on black, from `tools/make_splash.py`; shown after a start (not a reload) and held 2 s after the panel's second setup.
- [x] The lower-case "r" in the UI font looks strange and sits above the baseline compared with the other letters. Pillow draws a lone glyph of Inter Bold's r, < and > a pixel high; tools/make_fonts.py now takes each glyph's height from a render in running text.

## Phase 5: Hardening, then extras

- Battery-only operation (DEVNOTES §6.19):
  - [x] An install on a LiPo alone: DRIFT → FOMAJAM in 54 s, no reset during it.
  - [x] ~~Find why the Feather resets in the first minutes on battery~~: not seen again after the white-screen fix and the return to the regular firmware; closed without a cause.
  - [x] Fix the white screen after switching on with EN (DEVNOTES §6.20): after any start (not a reload), send the panel its setup again before the first screen. 9 of 9 power-ons on battery came up, with no added start time; plugging into USB, which reports a reset-pin start, needed it too (3 of 3 after the fix).
- Low-battery warning, and longer soak tests across more catalogue firmwares.
- Then a Fruit Jam port.

## Recovery

- **A failed install before the loader writes** (as seen twice in Phase 3): power-cycle the FM-1. The previous firmware boots.
- **Manual loader:** hold OCT− while powering on.
- **Rescue key:** `F0 22 24 35 7D F7` drops into the ROM UBOOT bootloader ("UBOOT1.00", USB mass storage).
- **Pico FM-1 Transporter:**
  - Build kurogedelic/FM-1-transporter @ `a632d92` with jl-uboot-tool `wl82loader.bin`, and drive it with MvaveFM1Unbricker `fm1_transporter_recover.py` (`info`, `dump`, `recover PACKAGE`).
  - Wiring: GP0 to D+, GP1 to D−, GND, no VBUS.
  - The UF2 is `ref/FM-1-transporter/build-pico/fm1_transporter.uf2`. Tested from macOS (DEVNOTES §3).
- **Plain-cable rescue tools** (`fm1_rescue.py`, `fm1_unbrick.py`) need SCSI pass-through, so Linux or Windows only.
- **Baseline flash dump:** `ref/flash-dumps/fm1-transporter-dump-20261022-213229.bin` (sha256 `8a4d2330…`). Keep a copy of stock `FM-1_015.fwsc`.

## Layout

```
lib/fm1proto.py      # protocol + package parsing (CPython and CircuitPython)
lib/fm1update.py     # install state machine over a transport (CPython and CircuitPython)
lib/fm1usb.py        # USB-MIDI host transport (CircuitPython)
lib/fm1ui/           # touch UI: screens, drawing, catalogue and state, device glue (CircuitPython)
device/              # code.py (UI entry point) and on-device scripts: installer, MAX3421E setup, diagnostics
fonts/               # bitmap fonts for the UI
tools/               # make_sd.py, flash_cli.py, fake_fm1.py (simulated FM-1), usb_descriptors.py
tests/               # CPython unit tests
patches/             # CircuitPython / TinyUSB / Pico-PIO-USB patches (see patches/README.md)
docs/                # upstream issue drafts
ref/                 # upstream clones, builds, flash dumps (gitignored)
```

## Workflow

- `main` stays working. Each feature gets a branch (for example `phase0-proto`), merged by PR.
- License: GPL-3.0, because the protocol logic is ported from `WebUpdate.js` (GPL-3.0-only WITH GPL-3.0-linking-exception).
