# CircuitPython patches for the FM-1 flasher

The flasher runs on an Adafruit Metro ESP32-P4 with a CircuitPython 11 build
that has two changes. Both are against CircuitPython `main` at 2b8803867c
(after adafruit/circuitpython#11726; 11.0.0-alpha.2 and later).

The enumeration buffer is upstream since 66688d5d05
(adafruit/circuitpython#11751, 4 November 2026): a build of `main` from
then on needs only the TinyUSB fix.

| Patch | Applies in | What it does | Needed? |
|---|---|---|---|
| `cp11-metro-p4-enum-bufsize.diff` | CircuitPython root | `CFG_TUH_ENUMERATION_BUFSIZE=512` for the Metro ESP32-P4. The FM-1's configuration descriptor is 293 bytes and the default buffer is 288, so the stock build never mounts it. Merged upstream as adafruit/circuitpython#11751 (66688d5d05). | Only before 66688d5d05 |
| `tinyusb-dwc2-abort.diff` | `lib/tinyusb` | DWC2 host: retire an aborted non-periodic DMA channel when it halts. Without it, reads from the FM-1 time out after a transfer is aborted. Reported as hathach/tinyusb#4405; fix proposed as hathach/tinyusb#4430. | **Yes** |

## Building

```sh
git clone https://github.com/adafruit/circuitpython && cd circuitpython
git checkout 2b8803867c
python3 tools/ci_fetch_deps.py espressif
git apply /path/to/patches/cp11-metro-p4-enum-bufsize.diff
(cd lib/tinyusb && git apply /path/to/patches/tinyusb-dwc2-abort.diff)
./ports/espressif/esp-idf/install.sh esp32p4
source ./ports/espressif/esp-idf/export.sh
pip install -r requirements-dev.txt "ninja<1.13"   # newer ninja breaks the IDF build
make -C mpy-cross                                  # also what tools/deploy.py needs
make -C ports/espressif BOARD=adafruit_metro_esp32p4 build-adafruit_metro_esp32p4/firmware.uf2
```

Copy `firmware.uf2` to the board's METROP4BOOT drive (double-click reset).
A Metro without TinyUF2 needs it first: BOOT + reset for the ROM loader,
then `esptool` writes TinyUF2's `combined.bin` at 0x0.

`docs/PLAN-v2.md` ("Upstream and the hub") tracks asking for both changes
upstream, so the flasher can run on stock CircuitPython.

The Feather v1 flasher's patches (PIO-USB, MAX3421E, TinyUSB enumeration
retry) are at the tag `v1-feather-final`, with the evidence in `DEVNOTES.md`
§4–5.
