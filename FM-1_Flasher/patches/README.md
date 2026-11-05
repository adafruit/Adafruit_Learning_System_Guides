# CircuitPython for the FM-1 flasher

The flasher runs on an Adafruit Metro ESP32-P4 with a CircuitPython 11 build
that has two changes. Stock CircuitPython can't run it yet.

## The ready-made build

Until the TinyUSB fix below is in a CircuitPython release, download the
flasher's build from the guide:

- `adafruit-circuitpython-adafruit_metro_esp32p4-11.0.0-alpha.2-85-g85d56a51a6-fm1-tinyusb4430.uf2`
  (3,149,312 bytes, SHA-256
  `7237c49a7e8a41da14690993a245f817ad44872ead4c9f899d3f852c6fdf60ea`).
  The guide may host it under a shorter name.
- It's CircuitPython `main` at 66688d5d05, which includes the enumeration
  buffer, plus `tinyusb-dwc2-abort.diff` committed in `lib/tinyusb` (local
  commit 85d56a51a6). Once installed, `boot_out.txt` reads
  "Adafruit CircuitPython 11.0.0-alpha.2-85-g85d56a51a6".
- Tested on a Metro ESP32-P4 with an FM-1: browsing, Catalog downloads and
  installs between V15 and community firmwares.

To install it:

1. Put the Metro in its bootloader: tap **Reset** and wait for the LED to
   turn purple. As soon as it turns purple, tap **Boot**, while the LED is
   still purple. The METROP4BOOT drive appears.
2. Copy the `.uf2` to METROP4BOOT. The Metro restarts into CircuitPython
   (macOS may say "fchmod failed" during the copy; that's harmless).
3. Copy the flasher to CIRCUITPY (the guide's Project Bundle).

The CircuitPython libraries in the Project Bundle are built for CircuitPython
11, which this is. Once the fix is in a CircuitPython release, use the stock
build from circuitpython.org instead.

## The patches

| Patch | Applies in | What it does | Needed? |
|---|---|---|---|
| `cp11-metro-p4-enum-bufsize.diff` | CircuitPython root | `CFG_TUH_ENUMERATION_BUFSIZE=512` for the Metro ESP32-P4. The FM-1's configuration descriptor is 293 bytes and the default buffer is 288, so the stock build never mounts it. Merged upstream as adafruit/circuitpython#11751 (66688d5d05, 4 November 2026). | Only before 66688d5d05 |
| `tinyusb-dwc2-abort.diff` | `lib/tinyusb` | DWC2 host: retire an aborted non-periodic DMA channel when it halts. Without it, reads from the FM-1 time out after a transfer is aborted. Reported as hathach/tinyusb#4405; fix proposed as hathach/tinyusb#4430. | **Yes** |

## Building it yourself

This builds the same thing as the ready-made UF2:

```sh
git clone https://github.com/adafruit/circuitpython && cd circuitpython
git checkout 66688d5d05
python3 tools/ci_fetch_deps.py espressif
(cd lib/tinyusb && git apply /path/to/patches/tinyusb-dwc2-abort.diff)
./ports/espressif/esp-idf/install.sh esp32p4
source ./ports/espressif/esp-idf/export.sh
pip install -r requirements-dev.txt "ninja<1.13"   # newer ninja breaks the IDF build
make -C mpy-cross                                  # also what tools/deploy.py needs
make -C ports/espressif BOARD=adafruit_metro_esp32p4 build-adafruit_metro_esp32p4/firmware.uf2
```

Install `firmware.uf2` as above. For a commit before 66688d5d05 (from
2b8803867c, after adafruit/circuitpython#11726), also
`git apply /path/to/patches/cp11-metro-p4-enum-bufsize.diff` in the
CircuitPython root.

A Metro without TinyUF2 shows no purple LED and no METROP4BOOT drive. It
needs TinyUF2 first: hold **Boot** while tapping **Reset** for the ESP32-P4's
ROM loader, then `esptool` writes TinyUF2's `combined.bin` at 0x0.

`docs/PLAN-v2.md` ("Upstream and the hub") tracks both changes upstream, so
the flasher can run on stock CircuitPython.

The Feather v1 flasher's patches (PIO-USB, MAX3421E, TinyUSB enumeration
retry) are at the tag `v1-feather-final`, with the evidence in `DEVNOTES.md`
§4–5.
