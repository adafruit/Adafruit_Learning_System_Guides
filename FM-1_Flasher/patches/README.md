# CircuitPython for the FM-1 flasher

The flasher runs on an Adafruit Metro ESP32-P4 with stock CircuitPython 11.
Both changes it needed are now in CircuitPython `main`, so no custom build or
patch is needed any more.

## Installing CircuitPython

Use a build from `main` at 92da735b06 or later
(`boot_out.txt` reads "11.0.0-alpha.2-152-g92da735b06" or a later version).
Until 11.0.0-alpha.3 or a later release is out, that's the
**Absolute Newest** build on the
[Metro ESP32-P4 page](https://circuitpython.org/board/adafruit_metro_esp32p4/)
of circuitpython.org. After that, use the release.

1. Put the Metro in its bootloader: tap **Reset** and wait for the LED to
   turn purple. As soon as it turns purple, tap **Boot**, while the LED is
   still purple. The METROP4BOOT drive appears.
2. Copy the `.uf2` to METROP4BOOT. The Metro restarts into CircuitPython
   (macOS may report an error at the end of the copy; that's harmless).
3. Copy the flasher to CIRCUITPY (the guide's Project Bundle).

Tested with `adafruit-circuitpython-adafruit_metro_esp32p4-en_US-20261111-main-PR11836-92da735.uf2`
on a Metro ESP32-P4 with an FM-1: installs between ChoralRoot, V15, SLOOP and
Skiff, directly and through a USB 2.0 hub.

A Metro without TinyUF2 shows no purple LED and no METROP4BOOT drive. It
needs TinyUF2 first: hold **Boot** while tapping **Reset** for the ESP32-P4's
ROM loader, then `esptool` writes TinyUF2's `combined.bin` at 0x0.

## The patches (history)

These are kept as a record of the changes the flasher needed. Both are
upstream, so neither is needed with a current build.

| Patch | Applies in | What it does | Upstream |
|---|---|---|---|
| `cp11-metro-p4-enum-bufsize.diff` | CircuitPython root | `CFG_TUH_ENUMERATION_BUFSIZE=512` for the Metro ESP32-P4. The FM-1's configuration descriptor is 293 bytes and the default buffer is 288, so the build before it never mounts the FM-1. | adafruit/circuitpython#11751 (66688d5d05, 4 November 2026) |
| `tinyusb-dwc2-abort.diff` | `lib/tinyusb` | DWC2 host: retire an aborted non-periodic DMA channel when it halts. Without it, reads from the FM-1 time out after a transfer is aborted, and installs fail partway (hathach/tinyusb#4405). | TinyUSB: hathach/tinyusb#4265 (bab06c109, carrying #4430). CircuitPython: adafruit/circuitpython#11836 (92da735b06, 11 November 2026) |

From 4 to 11 November the guide hosted a custom UF2,
`adafruit-circuitpython-adafruit_metro_esp32p4-11.0.0-alpha.2-85-g85d56a51a6-fm1-tinyusb4430.uf2`:
`main` at 66688d5d05 plus `tinyusb-dwc2-abort.diff`. A current stock build
replaces it.

`docs/PLAN-v2.md` ("Upstream and the hub") has the full history of both
changes.

The Feather v1 flasher's patches (PIO-USB, MAX3421E, TinyUSB enumeration
retry) are at the tag `v1-feather-final`, with the evidence in `DEVNOTES.md`
§4–5.
