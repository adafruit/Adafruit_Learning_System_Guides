# Draft: CircuitPython issue / PR (not posted)

**Title:** USB host: 288-byte `CFG_TUH_ENUMERATION_BUFSIZE` rejects common composite audio+MIDI devices

**Body:**

On boards with USB host, `supervisor/shared/usb/tusb_config.h` sets

```c
#ifndef CFG_TUH_ENUMERATION_BUFSIZE
#define CFG_TUH_ENUMERATION_BUFSIZE (284 + 4)
#endif
```

That's sized to CircuitPython's own configuration descriptor. TinyUSB aborts enumeration when a device's `wTotalLength` exceeds the buffer (`TU_ASSERT(total_len <= CFG_TUH_ENUMERATION_BUFSIZE)` in `usbh.c`), so these devices never appear in `usb.core.find()`. There's no error, and the device isn't listed.

Example: an M-VAVE FM-1 synth on its stock firmware (VID 0x4C4A, PID 0xC755) has a 293-byte configuration descriptor: UAC1 audio control, isochronous out and in, plus a MIDI streaming interface. A class-compliant USB audio+MIDI device is common, and these regularly pass 288 bytes.

Tested on an Adafruit Feather RP2040 USB Host with 11.0.0-alpha.0 (8f94f74a7c):
- Stock build: the FM-1 is never enumerated. The device list is empty, with 5 V present on the port (the device shows it's charging).
- With `CFLAGS += -DCFG_TUH_ENUMERATION_BUFSIZE=512` in the board's `mpconfigboard.mk`: TBD (result pending, to be filled in after testing).

**Proposal:** raise the default to 512 when `CIRCUITPY_USB_HOST` is enabled. The cost is about 224 bytes of RAM, and `_usbh_epbuf` goes from 296 to 520 bytes. Alternatively, make it easy to set per board. A clearer failure would help too, for example a debug log line when a descriptor is too large.
