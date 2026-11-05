# FM-1 Flasher: development notes

How we got here: what we tried, what we expected, what happened, and what we
concluded, dead ends included. `PLAN.md` has the plan and the current status;
this file has the story and the evidence. Dates are 2026.

**Contents**
1. [Where things stand](#1-where-things-stand)
2. [Protocol work (Phase 0, Oct 22)](#2-protocol-work-phase-0-oct-22)
3. [Desktop flasher and rescue path (Phase 1, Oct 22)](#3-desktop-flasher-and-rescue-path-phase-1-oct-22)
4. [Getting the FM-1 to enumerate on the Feather (Phase 2, Oct 22–26)](#4-getting-the-fm-1-to-enumerate-on-the-feather-phase-2-oct-2226)
5. [Patch verdicts](#5-patch-verdicts)
6. [Installing from the Feather (Phase 3, Oct 26–27)](#6-installing-from-the-feather-phase-3-oct-2627)
7. [Tools and techniques worth reusing](#7-tools-and-techniques-worth-reusing)
8. [Superseded conclusions](#8-superseded-conclusions)
9. [Open questions](#9-open-questions)

---

## 1. Where things stand

- A Feather RP2040 USB Host with the **MAX3421E USB Host FeatherWing** installs
  FM-1 firmware with no computer involved. Each run took about 70 s and lost no replies:
  - stock V15 → SLOOP 2.8: 70 s
  - SLOOP → V15 with factory voices: 73 s
  - V15 → ChoralRoot 0.27: 69 s

  The Mac's desktop flasher does the same in 33–43 s.
- It needs a **custom CircuitPython 10.3.1** with two changes, a TinyUSB
  enumeration retry and a 512-byte enumeration buffer (`patches/`, see
  [§5](#5-patch-verdicts)).
- The Feather's **built-in USB-A host port** (PIO-USB) works too, on a
  custom CircuitPython 11 (512-byte buffer, 120 MHz, Pico-PIO-USB disconnect
  check), **if the FM-1's cable is long enough**. With a 2 m cable: 10 of 10
  power cycles and two full installs. With a short cable the FM-1 goes
  silent: it switches to USB host role
  ([§6.6](#66-what-the-silent-state-is-oct-27),
  [§6.7](#67-cable-length-decides-it-oct-27)). A 30 cm USB-A pigtail on D11/D12
  works the same way, which leaves D9/D10 free. It's probably the cable's
  resistance rather than its length, and it's V15 that goes silent: SLOOP
  connected on every short cable tried
  ([§6.12](#612-cables-again-not-length-alone-and-v15-is-the-picky-one-oct-29)). A powered USB hub in between doesn't help
  ([§6.13](#613-a-powered-usb-hub-doesnt-help-v15-oct-29)).
- **A Feather RP2350 with the MAX3421E wing handles V15 on a short cable.**
  On the yellow cable (0.15 Ω), alone: 9 of 9 FM-1 power cycles, V15 → SLOOP
  in 55 s and SLOOP → V15 with voices in 47 s, with no lost replies and about
  400 KB free
  ([§6.15](#615-feather-rp2350--max3421e-wing-v15-on-a-short-cable-oct-29)).
  With the TFT rewired to D11/D12 and the touch UI, the same round trip
  worked from the touchscreen, after a fix to CircuitPython's MAX3421E driver
  for the SPI bus it shares with the display and SD card
  ([§6.16](#616-the-touch-ui-on-the-rp2350--wing-and-a-shared-spi-bus-fix-oct-29)).
  Grimm ↔ ChoralRoot and Grimm ↔ Golana worked too. The SD errors, the slow
  package checks and the frozen first list were the computer reading the
  card over USB at the same time; `CIRCUITPY_SDCARD_USB = false` fixes them
  (package check 1.3 s), and `tools/deploy.py` sets it
  ([§6.18](#618-the-computer-was-reading-the-sd-card-too-circuitpy_sdcard_usb-oct-30)).
  On a LiPo alone it installed DRIFT → FOMAJAM in 54 s, but the Feather
  reset six times in the first minutes, probably the supply sagging when the
  FM-1 attaches
  ([§6.19](#619-on-a-lipo-alone-an-install-works-but-the-feather-resets-at-first-oct-30)).
- **The touchscreen UI (Phase 4) installs firmware** on the TFT FeatherWing
  V2 3.5", over the PIO port with the 2 m cable. From the touchscreen:
  V15 → SLOOP, SLOOP → V15 with voices, V15 → MONK-1 and MONK-1 → V15, each
  in 84–98 s ([§6.9](#69-first-install-from-the-touch-ui-oct-28)). With the
  MAX3421E wing instead, its D9/D10 must be moved, because the TFT
  FeatherWing uses the same pins.

---

## 2. Protocol work (Phase 0, Oct 22)

**Sources.** `m-vave/fm1_open` @ `4c7496da` (`sdk/WebUpdate.js`), the Firmware
Hub catalogue (`https://thefirmwarehub.com/catalog.json`) and its installer.

**What we learned:**
- **SysEx framing:** `F0`, then a 7-bit-packed stream of
  `00 59 cmd len_lo len_hi 0 payload… checksum`, then `F7`. The checksum is
  `~sum(payload) & 0xFF`.
- **Commands:** 17 identity, 49 capability, 50 arm, 48 read request/reply,
  33/34 factory bank begin/write, 0 ack.
- **The update is request-driven.** After a kick (`F0 22 24 35 7F F7`) the
  device asks for package bytes by address. The host only answers, and a
  stage ends at the finish addresses 0xE0000000 and 0xF0000000.
- **Two install routes:**
  - **Open/stock** (`WebUpdate.js`): tagged, legacy, migration and loader
    modes; arm and capability where the firmware supports them.
  - **Community** (Firmware Hub, Felucca family):
    - wait 2 s after the kick, 10 ms between blocks, 3 s before looking for
      the restarted device
    - the loader identity is hard-coded `ota-FM-1_9xx`
    - verify by identity only, since there is no build hash

  Hub timing applies whenever either the package or the running firmware is a
  community one.
- **Trimmed packages.** Felucca-family packages drop the 32-byte alignment
  padding from `ota.bin`, so its stored length runs past the end of the file,
  and `WebUpdate.js` rejects them. `inspect(strict=False)` accepts exactly that
  case. All 84 catalogue packages at the time parse and complete a simulated
  install.
- **Progress.** The web updater's bar stalls near 86 %. Measuring against the
  blocks each stage actually reads fixes it.
- **Catalogue.** It's updated nightly and CORS-open. Entries carry `id`,
  `name`, `author`, `version`, `product`, `pkg`, `size`, `sha256`,
  `source`/`release`, `loader` and `kind` (a genre). They carry no license,
  `build_id` or `loader_sha256`; `make_sd.py` computes the loader hash.
  Firmwares listed with `loader: "mvave"` (e.g. Bubba) use the vendor
  `ota-FM-1_015` loader instead of `ota-FM-1_9xx`.

**Built:**
- `lib/fm1proto.py`: framing, package parsing and streaming reads.
- `lib/fm1update.py`: the install state machine over any transport.
- `tools/fake_fm1.py`: the simulator.
- `tools/make_sd.py`: prepares and verifies firmware folders.
- `tests/test_fm1.py`.

---

## 3. Desktop flasher and rescue path (Phase 1, Oct 22)

`tools/flash_cli.py` (python-rtmidi) proved the protocol on real hardware
before any CircuitPython work:

**Stock V15 → SLOOP 2.8 in 43 s.**
- Stage 1 sent 23 requests: 0x0–0x600, one block at 0x4400, then the loader.
- The loader came up as `ota-FM-1_900`.
- Stage 2 sent 1180 in-order 512-byte requests.
- The simulator now plays this exact pattern.

**SLOOP → V15 in 33 s,** plus 36 factory voice-bank writes in 0.6 s.
- The vendor loader `ota-FM-1_015` skips image 0x600–0x4400.
- Image address = flash address + 0x400, and loaders never touch the boot
  head.

**USB IDs:**

| Firmware | VID:PID | Product name |
|---|---|---|
| Stock V15 | 4C4A:C755 | "FM-1" |
| Felucca/SLOOP app | 1209:0001 | "Felucca" |
| Felucca/SLOOP loader | 1209:0002 | "Felucca Update" |
| V15's update loader (`ota-FM-1_015`) | 4D4A:4155 | "USB Composite Device" (manufacturer "Jieli Technology") |

**Rescue.** A Raspberry Pi Pico running kurogedelic's FM-1 Transporter
(`a632d92`, with jl-uboot-tool's `wl82loader.bin`), driven by MvaveFM1Unbricker's
`fm1_transporter_recover.py`, read the whole flash from macOS.
- **Wiring:** GP0 to D+, GP1 to D−, GND to GND, no VBUS.
- **Baseline dump:** `ref/flash-dumps/` (sha256 `8a4d2330…`).
- **Quirk:** the first `info` can report `uboot=0`; run it again.

---

## 4. Getting the FM-1 to enumerate on the Feather (Phase 2, Oct 22–26)

This took most of the effort. The order below is the order things happened.

### 4.1 The descriptor is too big (Oct 22)

The first probe from the Feather (CircuitPython 11.0.0-alpha) never saw the
FM-1 in `usb.core.find()`. A pyusb dump on the Mac
(`tools/usb_descriptors.py`) showed why it might not:
- **Stock V15's configuration descriptor is 293 bytes:** 5 interfaces, made up
  of UAC1 audio control, iso out, iso in, and MIDI streaming on interface 4
  with bulk 0x84/0x04.
- **CircuitPython's limit:** it sets `CFG_TUH_ENUMERATION_BUFSIZE` to 288
  (`supervisor/shared/usb/tusb_config.h`), and TinyUSB aborts enumeration when
  `wTotalLength` is larger.

So we built 10.3.1 with `-DCFG_TUH_ENUMERATION_BUFSIZE=512`. That fix is real
and still required, but it wasn't the blocker yet.

Along the way:
- `adafruit_usb_host_midi` has no `write()` and loses SysEx boundaries, so
  `lib/fm1usb.py` does USB-MIDI 1.0 SysEx packetizing and reassembly on
  `usb.core`.
- `hashlib` on CircuitPython only has the `hashlib.new("sha256")` form.

### 4.2 "It never attaches" (Oct 25)

We got TinyUSB debug logs out of the Feather (`CIRCUITPY_DEBUG_TINYUSB=2`, the
console UART on TX, read by the Pico on GP5 with `device/uart_log.py`).
- **A Keychron keyboard** on the same port gave a full "Device Attach …
  Enumeration complete: success = 1".
- **The FM-1** gave **no attach event at all**, in either USB-C orientation,
  before or after replugging.

Things tried and what we thought at the time:

| Try | Result | What we concluded then |
|---|---|---|
| Multimeter on D+/D− | 0.3 V on both with the FM-1 plugged in, 0 V without | FM-1 thinks it's on a charger? |
| Adafruit USB-C CC fixer at the FM-1 | Attached 3 times; enumeration failed each time (status stages, Set Address) | Attach depends on USB-C termination |
| 120 MHz build | Keyboard perfect, FM-1 still no attach | Clock isn't the problem |
| Pico-PIO-USB reply timeout 3 µs → 20 µs | One full FM-1 enumeration (293-byte descriptor read) | Timeout too tight? (later disproved, §5) |

The clock row is a real finding even though it wasn't the cause.
CircuitPython runs the Feather at 125 MHz (an SDK default), which makes
Pico-PIO-USB's clock dividers fractional. 120 MHz gives whole-number dividers.

Most of the "concluded then" column turned out to be wrong; see [§8](#8-superseded-conclusions).

### 4.3 The long-wait experiment

**The suggestion:** give the reply wait a couple of seconds. We built a Feather
firmware with long TinyUSB enumeration waits:

| Wait | Stock | Long build |
|---|---|---|
| Debounce after attach | 150 ms | 2000 ms |
| Root port reset | 50 ms | 100 ms |
| After reset ends | 2 ms | 50 ms |
| Reset recovery | 10 ms | 500 ms |
| Set Address recovery | 2 ms | 100 ms |

**Results:**
- **First boot with the FM-1 plugged in:** it attached and answered identity
  `FM-1_015` in 34 ms, the first SysEx round trip from the Feather. It didn't
  answer cmd 49, which is normal for stock.
- **Replugs:** in a 3-minute test, one detach and then nothing. No re-attach.
- **Feather resets with the FM-1 plugged in:** the log showed Device Attach →
  2000 ms → reset → Device Removed, about 8 times in a row.
- **Adding a 20-frame disconnect debounce in Pico-PIO-USB:** resets then
  enumerated 2 of 3 times, but hot-plugs still produced zero attach events.
- **Cycling the host 5 V through GPIO18 (2 s and 5 s off):** no effect. VBUS
  really was off: the TPS61023 boost turns its output fully off when EN is
  below 0.4 V (§4.7).

### 4.4 Ruling out the pull-downs

A second Pico ran the same firmware with **15 kΩ pull-downs** on D+/D− and
VBUS taken straight from the Mac.
- **Hot-plugs:** zero attaches.
- **Pico resets with the FM-1 plugged in:** 2 of 3 enumerated, the same pattern
  as the Feather.

So the pull-downs weren't the cause, and "reset with it plugged in works,
hot-plug doesn't" held on both boards.

### 4.5 Watching the lines: the FM-1's role-detect loop

With **no USB host running**, `device/fm1_lines.py` read GP0/GP1 as plain
inputs with pull-downs and logged every change while the FM-1 was hot-plugged.
After a hot-plug the FM-1 cycles forever, about every 3.6 s:

| Phase | Lines | Duration |
|---|---|---|
| J | D+ up (full-speed device) | **2.05 s, every cycle** |
| K | D− up | 0.02–0.5 s |
| SE0 | both low | ~1.2 s |

It presents as a device for 2.05 s, then probably checks whether it should be
the host (JieLi chips do OTG). **Once a host has enumerated it, it holds J
steadily,** even after the host goes away. That is why "reset with it plugged
in" worked: the FM-1 was already sitting in device mode.

This explained everything up to that point:
- **The 2 s debounce** expired exactly as the FM-1 left its 2.05 s J phase.
  Lengthening the wait made things worse.
- **The K phase looks like a low-speed device attaching.** Pico-PIO-USB
  "connected" to it. When the lines then went idle, nothing checked for a
  disconnect while the port waited for its bus reset (the disconnect check only
  runs while the bus is active), so the port stayed marked connected and never
  reported another attach. Those were the "no attach event at all" runs.

### 4.6 Root cause and fix

With stock timing plus a disconnect check while waiting for reset, hot-plugs
produced attach events every time, and the log showed the real failure.
**After the first bus reset in its J phase, the FM-1 switches into device mode
but can't answer that first enumeration:**

| Reset recovery | What the FM-1 does |
|---|---|
| 10 ms (stock) | ACKs the SETUP for Get Device Descriptor, never returns the data |
| 200 ms | Doesn't even ACK the SETUP |

After that one failed attempt it holds J and waits as a normal device. Reading
the raw GPIO input register through `memorymap` while the host was running
confirmed steady J. **TinyUSB never retries a failed enumeration**, so the port
stays stuck until the next unplug.

**Fix:** retry a failed root-port enumeration while the device is still
connected (`patches/tinyusb-enum-retry.diff`).

| Board | Hot-plugs mounted |
|---|---|
| Pico, with the 15 kΩ pull-downs | 5 of 5 |
| Pico, pull-downs removed | 5 of 5 |

Every time, attempt 1 failed and the retry succeeded.

### 4.7 The Feather's built-in port: the "silent" FM-1

The same firmware on the unmodified Feather:
- **Hot-plugs:** about 7 of 10 mounted over two runs, each through one retry.
  The rest were a **different failure**. The FM-1 went silent: both lines held
  SE0 indefinitely, with no role-detect loop and no attach. That's the 0.3 V
  state from §4.2.
- **Replugging at the FM-1's USB-C end instead of the Feather's USB-A end:**
  about as bad.
- **Power-cycling the FM-1 with the cable seated:** 8 of 10 mounted. The other 2
  went silent, and a later power cycle brought it back.
- **Recovery from silent:**
  - Turning the FM-1 off and on works. A plain replug sometimes does too.
  - Cycling GPIO18 (the boost enable) doesn't.

**The Feather schematic** (adafruit/Adafruit-Feather-RP2040-USB-Host-PCB):
- **USB-A VBUS** comes from a **TPS61023 boost** (EN on GPIO18, 100k pull-up).
  Its input is the higher of USB 5 V through a Schottky diode or the LiPo.
- **Between the boost and the jack:** 44 µF, then an unrated 0805 **fuse**.
- **D+/D−:** GPIO16/17 through 22 Ω. No pull-downs, no ESD protection.

**The VBUS tests were valid.** The TPS61023 datasheet says the output is
turned fully off when EN is below 0.4 V. GPIO18 driven low holds EN near 0 V
against the 100k pull-up, so the GPIO18 tests removed VBUS for 2–5 s.
- **A silent FM-1 stays silent** with VBUS removed and restored.
- **A working FM-1 stays on the bus** through it: the host still saw it 0.4 s
  after power returned, and it answered identity.

The FM-1 runs on its battery, so losing VBUS doesn't reset its USB state. Only
its own power switch does.

### 4.8 The MAX3421E wing settles it

The Adafruit USB Host FeatherWing (MAX3421E, product 5858) has a real
full-speed transceiver, 15 kΩ host pull-downs built in, and its own 5 V boost.
We stacked it on the same Feather (CS D10, IRQ D9) with a build that enables
`max3421e` and disables the PIO host (`patches/feather-max3421e.diff`).

**15 of 15 attaches** (10 power cycles and 5 hot-plugs), each about 6 s after
the FM-1 came back, with no silent state. Every attach still needed the
enumeration retry, so that is FM-1 behaviour, not PIO-USB behaviour.

**The SysEx stress test** (`device/fm1_sysex_stress.py`, long messages under
manufacturer 0x7D, which the FM-1 ignores, with identity checks between
batches):

| | PIO port | MAX3421E |
|---|---|---|
| Identity latency (avg) | 10.4 ms | 12.8 ms |
| 603-byte messages | 21.3 KB/s | 29.5 KB/s |
| Install-like stream | 24.3 ms/msg | 20.6 ms/msg |
| Errors | 0 | 0 |

**Conclusion:** the silent state comes from the built-in port's electrical
side, most likely its power path or termination. The FM-1's firmware and our
timing aren't the cause. **The flasher uses the MAX3421E wing.**

---

## 5. Patch verdicts

`device/fm1_stats.py` reads counters that an instrumented build keeps in RAM
(`patches/*-stats.diff`). It covered the stress test, hot-plugs and power
cycles on the Feather, about 17,400 transactions.

| Change | Where | Verdict | Evidence |
|---|---|---|---|
| Root-port enumeration retry | TinyUSB `usbh.c` | **Required on 10.3.1; built in on 11** | 11/11 attaches failed once, then succeeded on retry (and 15/15 on MAX3421E). CircuitPython 11's TinyUSB has its own retry (`CFG_TUH_ENUM_ATTEMPT_MAX` = 2) |
| `CFG_TUH_ENUMERATION_BUFSIZE=512` | board `mpconfigboard.mk` | **Required** | 293-byte descriptor > 288 default |
| Disconnect check while waiting for reset | Pico-PIO-USB | **Required** (PIO only), on 10.3.1 and 11 | Guards the stuck-"connected" race from §4.5. On CircuitPython 11 without it, the port never enumerated a role-detecting FM-1; with it, 4 firings in one 2 m-cable run (§6.7) |
| 20-frame disconnect debounce | Pico-PIO-USB | Keep (PIO only) | Absorbed one 1-frame SE0 glitch on a live connection |
| FS reply timeout 3 → 20 µs | Pico-PIO-USB | **Not needed** | Longest wait 1 µs; none over 3 µs |
| 120 MHz system clock | board CFLAGS | **Required** on the PIO port | At the stock 125 MHz, ~30 % of OUT writes fail on CircuitPython 11; 0/100 at 120 MHz (§6.5) |
| Long enumeration waits | TinyUSB `usbh.c` | **Harmful**, reverted | 2 s debounce misses the J window; 200 ms recovery stops the SETUP ACK |

None of this was posted upstream from the Feather work. The retry is the
finding most worth proposing to TinyUSB. The buffer size later went upstream
for the Metro ESP32-P4 (adafruit/circuitpython#11751, docs/PLAN-v2.md).

---

## 6. Installing from the Feather (Phase 3, Oct 26–27)

`device/fm1_install.py` runs `fm1update` on the device:
- **The flow:** verify the package sha256, dry run (identity and capability
  only), then install with `go=True`.
- **Package location:** `CIRCUITPY/firmware/<slug>/` for now; SD later.

### 6.1 The loader that wouldn't take our replies

**First attempt, V15 → SLOOP:**
- Stage 1, served by the stock app, worked.
- In SLOOP's loader (`1209:0002`) the install stalled after 3 requests.
  "Device stopped requesting data" came after 180 s.
- **Power-cycling the FM-1 brought back stock V15.** The loader hadn't written
  anything yet, and that was true for both failed attempts.

To see what happened, `fm1_install` now keeps a RAM ring of the last 80 SysEx
messages and prints it on failure, so logging doesn't change the timing.
- The loader asked for block 0 and we replied (605 bytes of SysEx, 808 bytes
  of USB-MIDI, sent as one bulk write of 13 packets).
- It **asked for the same block again** 3 s later, then 5 s after that, then
  gave up.
- One-packet messages, identity and the kick, got through fine.
- The Mac sends the identical bytes successfully.

**Fix:** send each reply as 64-byte writes. With a 1 ms gap the install
succeeded at the first try (109 s).

Our best guess at the cause: the loader NAKs while busy, and the MAX3421E
driver's NAK-then-resend handling on OUT loses data. That's unproven.

### 6.2 Back to V15: two bugs only the device could find

- **Transient read errors.** With SLOOP running, its sequencer streams MIDI
  notes over USB, and a bulk IN read on the MAX3421E occasionally fails once
  with `USBError`. The transport took the first one as an unplug. It now needs
  3 in a row.
- **MemoryError in the voice restore.** The firmware install had already
  succeeded, but `Package.factory_bank()` grew a bytearray to 16 KB and copied
  it twice, which failed on a heap fragmented by the long install. It now
  allocates once (output identical, sha256 `ecad0b86…`), and
  `restore_factory()` runs `gc.collect()` first. A later full install with the
  restore inside it worked.

### 6.3 Lost replies: slow down instead of re-sending

The serve loop always re-sent repeated requests, but identical bursts kept
getting lost. Now:
- **Detection:** a repeat arriving **≥ 1 s after our reply** (`lost_reply`)
  counts as a lost reply. Quick repeats are part of normal read plans; the
  stock app asks for 0x800 three times within ~100 ms.
- **Response:** the link slows down (`Link.slow_down()` →
  `USBMidiTransport.slow_down()`): 64-byte writes with a 1 ms gap, then the gap
  doubles up to 8 ms.
- **Carry-over:** `Updater.slow_level` reapplies the setting to new links, so
  it survives re-enumeration into the loader.
- **Simulator:** it now models lossy links and the loader's
  retry-twice-then-silence, with 4 tests.

On hardware this recovered one lost reply in each direction:
- In SLOOP's loader at 0x200.
- In the SLOOP *app* at 0x0, so busy community firmware loses bursts too, not
  only loaders.

### 6.4 Speed: most of the time was Python, not USB

Measured on the Feather for one 512-byte reply:

| Step | Before | After |
|---|---|---|
| `frame` + `pack7` | 16.9 ms | 9.3 ms (7-byte groups with fixed shifts, one buffer) |
| `encode_sysex` | 10.1 ms | 7.0 ms (indexed stores, no slices) |
| Send, one write | 13.2 ms | — |
| Send, 64-byte writes, no gap | 16.9 ms | **new default** |
| Send, 64-byte writes, 1 ms gap | 30.1 ms | (adaptive fallback) |

Both rewrites are byte-identical to the old code at every length.

The serve loop now builds the reply first and sleeps only what's left of the
hub's 10 ms pacing. The minimum gap is unchanged, but building the reply
already uses it up.

With 64-byte writes and no gap as the default:

| Install | Before | After | Lost replies |
|---|---|---|---|
| V15 → SLOOP 2.8 | 114 s | 70 s | 0 |
| SLOOP → V15 + voices | 119 s | 73 s | 0 |
| V15 → ChoralRoot 0.27 | — | 69 s | 0 |

ChoralRoot (from the catalogue through `make_sd.py --catalog choralroot`) ships
its own loader build (sha256 `ab3242c8…`, against SLOOP's `7024be59…`). It also
reports as `ota-FM-1_900`.

### 6.5 CircuitPython 11 on the built-in port (Oct 27)

We retested on **CircuitPython 11.0.0-alpha.2**, the latest release. Its TinyUSB
(`efab607`) and Pico-PIO-USB (`9e502a5`) match `main` on that day. The FM-1 was on
the Feather's own USB-A port.

**What changed upstream:**
- **TinyUSB now retries enumeration itself.** In `usbh: add control
  transfer timeout and enumeration retry (#3862)`, a failed enumeration
  transfer tears down and restarts from a fresh port reset after the 150 ms
  debounce. `CFG_TUH_ENUM_ATTEMPT_MAX` defaults to 2 (one retry). That is
  exactly what the FM-1 needs, so **our retry patch isn't needed on 11**.
- **The enumeration buffer is still 288 bytes,** so 512 is still required. Stock
  V15 (293-byte descriptor) enumerated with it.
- **Pico-PIO-USB still has no disconnect check while waiting for reset.**
  Nothing in these tests needed it, but §6.7 did: it's still required.

**Results with only the 512-byte change, at the stock 125 MHz:**
- Power cycles and hot-plugs (FM-1 running ChoralRoot): about 12 of 15 mounted,
  similar to patched 10.3.1. The rest were the silent state.
- **Installs fail.** The first 605-byte reply errors out of `device.write()`.
  A write test against the FM-1 (messages it ignores) failed about 30 % of the
  time at every length, even single 16-byte packets, and the failures landed on
  random 64-byte pieces.

**At 120 MHz: 100 of 100 writes succeeded** at every length.
- At 125 MHz Pico-PIO-USB's 48 MHz bit clock needs a fractional divider
  (≈2.60). Enough packets go bad that a 13-packet reply rarely survives.
- **So 120 MHz is required** on the PIO port. §5 had it as "untested
  without"; 10.3.1 only worked because all our builds already ran at 120 MHz.

**ChoralRoot → V15 at 120 MHz:**
- Stage 1, served by ChoralRoot's updater: done, 76 requests.
- Stock loader: all 1244 requests with no lost replies. The write phase took
  47 s, faster than through the MAX3421E (53 s).
- The FM-1 then restarted into V15 and **came back silent**, so the install
  timed out waiting before the voice restore. The screen confirmed V15.
- **Two FM-1 power cycles didn't recover it** (lines at SE0). **A Feather reset
  with the FM-1 left plugged in did:** it enumerated as `4C4A` "FM-1" right
  away. The voice restore then ran on its own in 5.1 s.

So **host-side re-initialization can clear the silent state**, where VBUS
cycling can't. That looked like a lead on its cause, and a possible recovery
that doesn't need the user. §6.6 shows it doesn't hold up.

**ChoralRoot handles a failed update cleanly.** When the first attempt died in
stage 1, it showed an "update failed" screen and returned to normal play by
itself (reported by John). The earlier assumption that it was stuck waiting
was wrong.

**Device code hardened along the way:**
- `USBMidiTransport.send` retries a failed write up to 3 times. It resends the
  whole message, and the leading F0 restarts the device's parser.
- `finder()` tries each device twice before skipping it.
- `fm1_install` prints its message ring for any exception.
- `fm1_replug.py` recognises the Felucca-family `1209:xxxx` IDs.

### 6.6 What the silent state is (Oct 27)

**Trying to wake it from software** (`device/fm1_wake.py`), without a reset,
when an FM-1 came back silent after a power cycle:

| Nudge | Woke it? |
|---|---|
| Float D+/D− (pull-downs off) for 50 ms, 500 ms and 2 s | No |
| Pull D+ up (internal pull-up), D− floating, 100 ms | No |
| Pull D+ up, D− pulled down, 500 ms | No |
| VBUS off (GPIO18 low) plus lines floating, 2 s | No |
| FM-1 power cycles | 0 of 10 |
| `microcontroller.reset()` | 2 of 2 |

**A/B test of the host side.** Two debug builds of 11.0.0-alpha.2 (512-byte
buffer, 120 MHz, TinyUSB log level 2 on the console UART, read by a Pico) with
counters in Pico-PIO-USB (`patches/pico-pio-usb-cp11-stats.diff`):
- **A:** stock Pico-PIO-USB.
- **B:** plus the disconnect check while waiting for reset (`FM1_IDLE_DISCONNECT=1`).

`device/fm1_cycle_watch.py` logged every attach, detach and SILENT with the counters.

| | A | B |
|---|---|---|
| Start | Attached | Silent, even after reflashing the Feather |
| Power cycles | 10: silent from the first, never came back | About 10: never attached |
| Pico-PIO-USB connects | 0 | 0 |
| TinyUSB log | One "Device Removed", then nothing | Nothing |
| Lines | SE0 throughout | SE0 throughout |

TinyUSB never saw an attach, so nothing was enumerated, retried or failed.
Pico-PIO-USB correctly reported an empty port, so B's check had nothing to act
on. **Neither is the cause.** Two Feather resets (one through the UF2
bootloader, one plain) didn't wake it either this time, so the 2 of 2 above
was luck.

**Narrowing it down,** with the FM-1 silent:

| Test | Result |
|---|---|
| Unplug the cable at the Feather for 5 s, replug | Still silent |
| Lines for 10 s after that replug | Solid SE0, no role-detect loop (§4.5) |
| FM-1 charging icon | On, so VBUS reaches it |
| Same cable into the Mac | Enumerates at once as `4C4A:C755` "FM-1" |
| Straight back into the Feather | Silent again |
| RP2040 internal pull-up on D+, FM-1 connected | D+ stays low |
| Same, nothing connected | D+ goes high; D− likewise |

**Conclusion: a silent FM-1 is in USB *host* role.** Something on the FM-1's
side pulls D+ down harder than the RP2040's ~50 kΩ pull-up. A device would
have a 1.5 kΩ pull-up on D+ instead; a host has ~15 kΩ pull-downs. So the
FM-1 sits waiting for a device, and the Feather's pins, socket, cable and host
stack are all fine. The J/K/SE0 loop of §4.5 is its dual-role (OTG) detection;
silent is that detection settling on "host". A standard host (Mac, MAX3421E)
gets it back into device mode.

**Why only the built-in port?** Unproven. The likely difference is
termination: the port has no 15 kΩ pull-downs, only the RP2040's weak internal
ones. But the Pico runs in §4.4/4.6 with and without 15 kΩ pull-downs never
went silent either, so that isn't the whole story; the Feather's power path is
still a suspect too. A possible fix for the built-in port, **untested**: 15 kΩ
from D+ and D− to ground on the Feather.

**For the flasher:** no host software fix exists; it's the FM-1's role
decision. The MAX3421E wing stays the hardware (§4.8). (§6.7: a longer cable
avoids it.)

### 6.7 Cable length decides it (Oct 27)

**Setup.** CircuitPython 11.0.0-alpha.2 with the 512-byte buffer, 120 MHz and
the Pico-PIO-USB disconnect check (`patches/pico-pio-usb-cp11-idle-disconnect.diff`).
For other pins, the board doesn't claim GPIO16/17 at boot and the script
calls `usb_host.Port(board.D11, board.D12)` (`patches/cp11-feather-pigtail.diff`).
`device/fm1_cycle_watch.py` takes `FM1_DP` for the pin. The FM-1 was power-cycled
with its cable seated, as in §6.6.

**A USB-A jack pigtail on D11/D12** (Adafruit 4449: a 30 cm, 28 AWG cable with
a jack on one end and jumper sockets on the other, no parts):

| Power | Series resistors | FM-1 firmware | Power cycles back | Silent |
|---|---|---|---|---|
| Mac 5 V (Feather USB pin) | none | V15 | 15 of 15 | 0 |
| Boost, through a USB-A plug breakout (Adafruit 3628) in the Feather's socket | none | V15 | 13 of 13 | 0 |
| Boost | 22 Ω | SLOOP | 5 of 5 | 0 |
| Boost | 22 Ω | V15 | 14 of 14 | 0 |

Installs over the pigtail: V15 → SLOOP in 72 s, and SLOOP → V15 in 69 s.
The V15 voice restore had to be rerun separately, see below.

Without the disconnect check, on boost power, the FM-1 ran its role-detect
loop while the port sat "connected" from the first K phase and never
enumerated it (§4.5). **So CircuitPython 11 still needs the disconnect check**
on the PIO port, contrary to §6.5. In the long-cable run below it fired 4 times.

**The built-in socket, with a second Feather** (a different board, same build
but with the host port on GPIO16/17). All with the same FM-1 on V15:

| Into the USB-A socket | Result |
|---|---|
| The usual short cable (with a ferrite bead), direct | Silent; D+ held low |
| A known-good short cable, direct, from a state cleared on the Mac | Silent at once |
| The same, with the socket's shell clipped to GND | Silent |
| Bead cable → 4449 jack → jumpers → 3628 plug → socket | 10 of 10, then 5 of 5 with the good cable |
| **A 2 m cable (Adafruit 6279), direct** | **10 of 10** |

A third, plain cable (the yellow one) seemed to be charge-only: the Mac didn't
see the FM-1 through it either. Its runs are left out. **It does carry data**
(§6.12): the FM-1 was probably already in host role.

Over the 2 m cable on the built-in port: V15 → ChoralRoot 0.27 in 71 s, and
ChoralRoot → V15 in 69 s.

**What this rules out:**
- the individual board (two Feathers behave alike)
- the boost and fuse (fine through the pigtail and the 2 m cable)
- the socket, its traces, GPIO16/17 and the 22 Ω resistors (fine through the
  chain and the 2 m cable)
- the 22 Ω resistors on their own (fine on the pigtail)
- the cable's shield: the socket's shell lugs (MT1/MT2) are unconnected in
  the board file, but grounding the shell didn't help
- the FM-1 firmware (V15 and SLOOP both fine)

What's left is **length**: every PIO-port setup that worked had at least ~30 cm
more cable between the socket and the FM-1, and every short direct cable failed.
That changes capacitance and inductance on all four lines, the data pair and
VBUS/GND alike. Which one matters, and how, is unmeasured. Two things don't
fit yet:
- the MAX3421E wing was fine with the short bead cable (§4.8)
- on earlier days that bead cable worked 7–8 times in 10 on this port (§4.7),
  where today it never did

**Cable readings** (TREEDIX cable tester, end to end):

| Cable | CC1 | CC2 | VBUS–GND | Shell–GND | On the PIO port |
|---|---|---|---|---|---|
| Short, ferrite bead | 56k up | open | ~0.2 Ω | short | Silent, stays silent |
| Short, yellow (carries data, §6.12) | 56k up | open | ~0.2 Ω | short | Not run |
| Blue 1 m (Adafruit, 1 m version of 6279) | 56k up | 56k up | 0.36 Ω | open | Went silent once, then recovered on a later power cycle (two detaches logged) |
| Blue 2 m (Adafruit 6279) | 56k up | 56k up | 1.3 Ω | open | 10 of 10 |

The blue cables put the 56k Rp on both CC lines, so the FM-1 sees it in
either orientation. That suggested a CC-orientation cause: the FM-1 sensing
one CC pin and falling back to D+/D− role detection without Rp. **Ruled out:**
- the bead cable went silent on the Feather with the USB-C end either way round;
- on the Mac it enumerated either way round;
- the 1 m blue cable, with the same CC wiring as the 2 m, still went silent.

The shield doesn't track success either: the bead cable ties it to GND, the
blue cables leave it open.

So the effect grows with cable length and resistance: short cables stay silent,
1 m recovers, 2 m and the +30 cm chain never go silent. A silent FM-1 on the
Mac also came back only after a USB-C replug, not on its own.

**V15 re-enumerates once after its first boot.** In both V15 installs (pigtail
and 2 m cable), the FM-1 came back as `FM-1_015`, answered the installer's
identity check, then dropped off the bus about 4 s later. The voice restore's
first query failed with a `USBError`. Run separately, the restore took 1.8 s.
`Updater` now retries the restore once after waiting for V15 to come back
(`_restore_after_boot`), with a simulator test (`reenum_after_boot`). On the
device (2 m cable): SLOOP → V15 with voices in one run, 82 s; V15 was found
again 7 s after it dropped, and the restore took 1.8 s.

**CircuitPython 11's `hashlib` gave wrong SHA-256 digests** on a fragmented
heap. The package check failed with "invalid factory voice data" although the
same file and code passed on the Mac. Repeated runs of `prepare` failed after
the first; once, a `gc.collect()` between two `update()` calls gave a wrong
digest. After a soft reset, 24 of 24 cases passed. 11.0.0-alpha.2 moved
`hashlib` to mbedtls 4.2's PSA API, and `shared-module/hashlib/Hash.c` ignores
the return codes of `psa_hash_update` and `psa_hash_clone`, so a failure would
be silent. Workaround: soft-reset before an install. Needs a proper repro
before an upstream issue.

### 6.8 The TFT FeatherWing next to the PIO host (Oct 27)

The TFT FeatherWing V2 3.5" (5872) on Feather 2, with the FM-1 on the 2 m
cable and the built-in PIO port. `device/tft_check.py` drew colour bars,
mirrored the console and read touches; nothing it uses (SPI, D5, D6, D9, D10,
I2C) touches GPIO16–18.

- **Display:** HX8357 at 480x320 on `board.SPI()`, CS D9, DC D10, 24 MHz.
- **Touch:** FT5336 at I2C 0x38. Points come back in the panel's native
  portrait frame (x up to ~320, y up to ~480), so landscape needs a swap and
  flip.
- **RAM:** about 128 KB free with the display up, 122 KB after an install.
- **Installs with the console on the screen:** V15 → ChoralRoot in 85 s
  (71 s without the display) and ChoralRoot → V15 with voices in 103 s
  (82 s), both with no resends or slow-downs. V15 re-enumerated after its first
  boot and `_restore_after_boot` handled it. The extra time is the console
  scrolling: the voice restore, which prints a line per step, took 6.6 s
  instead of 1.8 s. A real UI that redraws a progress bar should cost less.

### 6.9 First install from the touch UI (Oct 28)

Feather 2, TFT FeatherWing, 2 m cable, built-in PIO port. The UI starts an
install by saving the slug in NVM and soft-reloading, so the install runs on
a fresh heap. Three failures before V15 → SLOOP worked (84.4 s, no resends):

- **After a soft reload the FM-1 misses the first query or two.** It isn't
  reset by the reload and stays enumerated. The installer's two identity
  tries ran out: "no FM-1 answered". Watching from the REPL: no answer to
  the first two queries, then every one answers.
- **Reopening the endpoints each try never gets an answer.** A wait loop
  that opened a transport, queried, then released it (`deinit()`) got no
  reply in 15 s. Without a reload, fresh transports answer at once, even
  after `deinit()`. Unproven guess: a data-toggle mismatch that each reopen
  restores. The fix keeps one transport for the whole wait (answered on
  query 3) and hands it to the installer.
- **A garbage-collected `usb.core.Device` closes the endpoints it opened,**
  and endpoints belong to the device address, not the object
  (`shared-module/usb/core/Device.c`, `__del__` → `tuh_edpt_close`). Device
  objects dropped by an earlier probe were collected 2 s into staging and
  closed endpoint 0x04 under the installer: Pico-PIO-USB printed
  `no endpoint 0x04` and the reply write failed with `USBError`. The
  transport's `close()` now calls `device.deinit()`, and nothing drops a
  Device it has used without closing it.

Then SLOOP → V15 with factory voices, 84.5 s, no resends. SLOOP answered
the first identity query after the reload, so the missed queries may be
V15's.

Also seen:
- **"invalid factory voice data" in the package check: `hashlib` returned an
  all-zero digest.** First seen on the first SLOOP → V15 attempt. Once the
  three checks behind that message said which one failed, two MONK-1 → V15
  attempts in a row both failed the voice bank's **SHA-256**, with ~53 KB
  free. The bank's CRC had passed just before, and so had the whole-file and
  loader SHA-256s. Recomputing didn't help: three tries in a row gave
  `0000…0000`. So the hash failed outright and `hashlib` reported no error
  (`shared-module/hashlib/Hash.c` ignores the PSA return codes, §6.7).
  The bank was hashed as one 16 KB `update()`. The other hashes go 2–4 KB at a
  time and never failed. Feeding the bank 1 KB at a time, MONK-1 → V15 passed
  first try (97.2 s, voices restored), with the same free RAM. Likely cause,
  not confirmed in the source: mbedtls's PSA layer copies each update's input
  to a temporary buffer, and a 16 KB block doesn't fit a fragmented heap. That
  also fits the REPL passing with 74 KB free. All three SHA-256 checks now
  recompute after a mismatch (`check_sha256`: a wrong digest can't match by
  chance), and the log says "failed" for an all-zero digest. For an upstream
  issue: a 16 KB `update()` on a fragmented heap → silent all-zero digest.
- **The package check takes 11–30 s.** Slow checks went with the failures,
  but the passing V15 run above also took 26.8 s, so slowness alone isn't
  the fault. Explained and cut to about 4 s in 6.10.
- **White screen:** once after replugging the FM-1 during a failed install.
  The code was still running (Ctrl-C found it polling touch). Not explained.
- **Serial input stops if Ctrl-C arrives during a soft reboot.** Sending
  Ctrl-D, then Ctrl-C ~0.6 s later, left `code.py` and the UI running but
  the console accepting no input (writes time out). CIRCUITPY was still
  readable. Only a reset cleared it. This happened twice, both from my
  scripted keys, and it explains the earlier "unresponsive Feather". Wait
  for `code.py` to start before sending Ctrl-C.
- **Unreadable disk prompt:** after a hard reset the Mac called the SD card's
  drive unreadable (Eject is safe). Probably shown over USB before `code.py`
  mounts the card.

### 6.10 Why the package check was slow (Oct 28)

Timed on the Feather from the REPL, on a fresh heap, for V15 (700 KB):

| Step | Time |
|---|---|
| Whole-file SHA-256 | 1.75 s (4.2 s on the first pass after mounting) |
| Entry CRCs (622 KB) | 8.4 s |
| Factory voice bank (decode + CRC + SHA-256) | 3.9 s |

- **Reading the file is not the cost.** A pass over the whole file takes
  about 1 s, at any read size from 2 to 16 KB. `hashlib` hashes 640 KB of
  RAM in 0.7 s.
- **The CRCs are pure Python.** CircuitPython's `binascii` has no `crc_hqx`,
  so CRC-16 runs at about 93 KB/s. Viper isn't enabled in this build.
- **The factory bank read 32 bytes at a time.** That was 2,289 separate
  reads, each with a seek and new buffers. It also ran twice per V15
  install: once in the check, and again for the voice restore.

The fixes:
- **`prepare(..., checked=True)` (the touch UI).** It keeps the whole-file
  SHA-256. Once that matches, it skips the entry CRCs and the factory-bank
  checks. `make_sd.py` ran those checks on the same bytes before writing
  `meta.json`, and a wrong digest can't match by chance (6.9). Without
  `hashlib` it still runs everything. `make_sd.py`, the desktop and
  `flash_cli.py` run the full checks as before.
- **`factory_bank()`.** It reads 1 KB at a time and decodes the 32-byte
  blocks in place.

Results: the V15 check takes 4.1 s and SLOOP's 1.6 s, and the voice-restore
extraction drops from 3.9 s to 2.5 s. Most of what's left is the per-byte
decode and CRC of the 73 KB voice entry.

### 6.11 A deleted attribute stays alive (Oct 28)

In the two-column text list, most taps on a firmware failed to open its
details: a MemoryError of 0.7–1 KB while building the description lines,
caught by the app's safety net, which returned to the list. Measured on the
Feather from the REPL:

- **Releasing the list freed almost nothing.** Free RAM was 58 KB before
  building the text list, 32 KB with it on screen, and still 31 KB after
  `Screen.release()` and `gc.collect()`. The card view held back 19 KB the
  same way. The amount varied from build to build.
- **The cause is MicroPython's dict deletion.** `release()` drops a
  screen's displayio handles with `delattr`. MicroPython's map removal
  marks the slot deleted but leaves the old value pointer in the table, and
  the GC scans the whole table. So every deleted attribute (`cards`, the
  buttons, the row groups, and through them the screen's whole group) stayed
  alive until a later insert happened to reuse the slot.
- **The fix:** set the attribute to `None`, then delete it. Release now
  returns the full 26 KB (57 KB free afterwards). A stress test of 60
  list → details trips across all pages had 0 failures in either view (5 of
  60 before), with at least 37.5 KB free on the details screen (22–31 KB
  before).
- **This probably explains earlier trouble:** the MONK crash (6.9) and the
  eight-card limit ran into the same retained screens.
- **Also:** the details screen now makes its description lines first,
  while the heap's large gaps are still free. The safety net prints a
  traceback, which is how the failing line was found.
- **Rule for this codebase:** to drop a large object held in a dict or
  instance attribute on CircuitPython, overwrite it before deleting it.

### 6.12 Cables again: not length alone, and V15 is the picky one (Oct 29)

Feather 2, TFT FeatherWing, built-in PIO port, the touch UI's Connect FM-1
button (6 s wait). The serial log, with a note at each swap, is
`logs/cable-test-20261029.log`. "0 queries" in a failure means the FM-1
never appeared on the bus: the silent state of §6.6.

**V15 on the FM-1:**

| Between the Feather and the FM-1 | Connects |
|---|---|
| 2 m blue (6279) | 5 of 5 |
| 1 m blue + panel-mount socket (14 cm lead) | 1 of 1 |
| 1 m blue + the §6.7 chain (4449 pigtail, 30 cm 28 AWG → jumpers → 3628 plug) | 1 of 1 |
| 22 cm cable + the chain | 1 of 1 |
| Ferrite bead cable + the chain | 1 of 1, then V15 → SLOOP in 83 s, no resends |
| 1 m blue alone, from a known-good FM-1 | 1 of 5 |
| 22 cm cable + panel-mount socket | 0 of 1 |
| Ferrite bead cable + panel-mount socket | 0 of 1 |
| Ferrite bead cable alone, either angle | 0 of 2 |

**SLOOP on the FM-1:**

| Between the Feather and the FM-1 | Connects |
|---|---|
| 1 m blue alone (2 with the Feather end plugged first, 1 with the FM-1 end first) | 4 of 4 |
| Ferrite bead cable alone | 1 of 1 |
| Yellow cable alone | 1 of 1 |
| Yellow cable + the chain | 1 of 1 |

SLOOP → V15 with factory voices over the 2 m cable: 93.5 s, no resends.

**What this shows:**
- **Length alone doesn't decide it.** 22 cm plus the chain (about 55–60 cm,
  much of it 28 AWG and jumpers) works, the 1 m cable alone mostly doesn't,
  and 22 cm plus the 14 cm panel-mount lead doesn't. The chain is thin wire
  and four extra contacts, so it adds far more **resistance** per cm than a
  normal cable. Resistance fits every row: the 1 m (0.36 Ω VBUS–GND, §6.7)
  is borderline, and the 2 m (1.3 Ω) never fails. Two more VBUS–GND
  readings (same TREEDIX tester): the yellow cable alone 0.151 Ω (§6.7 read
  about 0.2 Ω), and the yellow cable + the chain 0.48 Ω, so the chain adds
  about 0.33 Ω. Neither has been run with V15 directly on the Feather (only
  the bare cable behind a hub, §6.13); if resistance decides it, the chain
  version should mostly connect and the bare cable shouldn't. **Unmeasured:** the loop resistance of the other combinations.
- **The firmware matters.** Every cable worked with SLOOP, including the
  three short ones that fail with V15. §6.7 cleared the firmware, but only on
  the long pigtail, where both work.
- **Plug order doesn't explain it.** With SLOOP both orders worked. With
  V15 on the 1 m the Feather end first worked once, then the FM-1 end first
  failed, then the Feather end first failed too.
- **A failed attempt doesn't trap the FM-1.** After each short-cable failure
  from a good state, the 2 m connected at once with no power cycle (4 checks).
- **The yellow cable carries data.** It's the "charge-only" cable of §6.7.
  The Mac probably didn't see the FM-1 through it then because the FM-1 was
  already in host role (below).

**The stuck state, once.** At the start the FM-1 (V15) failed 8 times on the
1 m and then on the 2 m too. That was through FM-1 power cycles, a USB-C
replug at the FM-1 and a Feather reset. The Mac didn't list it either at
first. A power cycle while plugged into the Mac brought it back as `FM-1`
(vendor `0x4C4A`), and the 2 m then connected at once. What put it there is
unknown. It may have been stuck before the session started.

**Why SLOOP doesn't care: it never asks to be the host.** From SLOOP
2.8.3's source (the hub's mirror, `src/sloop-2.8.3.tar.gz`), its USB driver
works at register level (`firmware/hal/fm1_usb.h`, `firmware/src/usb.c`).
`usb_start()` resets the USB block, waits 25 ms and calls
`fm1_usb_attach()`, which turns the PHY on and sets the D+ pull-up
(`/* D+ pull-up: attach */`). There's no role check. If no host answers, it
retries once a second (`usb_retry`). So SLOOP is a device whatever the
cable does. V15 is M-VAVE's closed build on JieLi's SDK, which does dual
role, and it runs the role-detect loop of §4.5 (probably recorded with V15
on the FM-1). The silent state is that check settling on host. The FM1 Open
engine library has a `fixed_usb_device_mode` function.

**Only V15 does it: the community firmwares are device-only.** 98 of the
hub's 115 firmwares have mirrored source (`src/*.tar.gz`). Each one's USB
start-up, read in the source (not the binaries):

| How it brings up USB | Firmwares | Role check |
|---|---|---|
| Own copy of the Felucca / felucca-bsp driver: reset, then the D+ pull-up | 83 | No |
| fm1-base + felucca-bsp, USB code outside the archive (AMB, Berlinan, CTL, Delrio, Frasil, Loom, Modelar, Polly, Midimon) | 9 | No: felucca-bsp's `chip/usb.c` is the same attach (checked on GitHub) |
| Felucca, EMB, FIZZ, Kitten, Mycelium: Felucca / SLOOP / ChoralRoot code, USB code not in the archive | 5 | No, by code family (Kitten and Mycelium from their READMEs only) |
| Bubba: JieLi's SDK stack, V15's family | 1 | `detect_mode = OTG_SLAVE_MODE`, "USB0 solo como dispositivo" |

USB host mode exists only as an opt-in (felucca-bsp's `FELUCCA_USB_HOST`,
in J6, Melodee and Midimon): a menu switch, and every boot is a device
("every boot is a device, so the update paths always work", Melodee). Not
checked: the 17 without mirrored source (zp12, jiant, rainbow, winampfm,
tribe, cs1, hyp1, tonitor, vector37, tuna, kawa, nmsfm, morpheus, flyfish,
carnac, s1vave, ptfm). Only SLOOP has been tried on short cables.
**Consequences:**
- A first install from V15 needs the long cable, and so does going back to V15.
  After the write, V15 boots and must enumerate again for the check and the
  factory voice restore. On a short cable that step may fail, though the new
  V15 still boots.
- Between device-only firmwares a short cable should be fine. Shown for SLOOP
  only.

The question left is electrical: what about a short, low-resistance cable on
this port makes V15's check pick host?

**A working theory, untested:** when the FM-1 connects, its input
capacitance and charger draw a surge from the Feather's 5 V. A low-resistance
cable lets VBUS dip or ring at the FM-1. V15 reads that as the host going
away, reruns its role detection and settles on host. More series resistance
softens the surge. This fits resistance over length, and passive parts
helping. It also fits the Mac and the MAX3421E never doing it (stiffer
supplies) and SLOOP not minding (a different USB start-up). It doesn't
explain the 1 m's occasional success, except as a borderline case. To test,
in order of cost:
1. Measure the VBUS–GND loop resistance of each combination above.
2. Try a short cable with ~1 Ω in series in VBUS only. If it then works,
   the cause is power, not the data lines.
3. Scope VBUS at the FM-1 on plug-in, with a short cable and with the 2 m.
4. Try 15 kΩ pull-downs on D+/D−, the other suspect (§6.6).

**Also seen:**
- **The package check took 9.3 s for SLOOP and 22.8 s for V15.** §6.10
  measured 1.6 s and about 4 s. The SLOOP install also took 19 s from the
  reload to the start of the check; the V15 one took 5 s. Not yet looked at.
- **One more failed connect, at 22:46:55,** after the last note. It's unlabelled
  and left out of the tables.

### 6.13 A powered USB hub doesn't help V15 (Oct 29)

**Idea.** Put a hub between the PIO port and the FM-1, so the FM-1 sees a
proper USB 2 hub port instead of the Feather's: real 15 kΩ pull-downs and
VBUS from a stiff supply. If V15's role check is reacting to the Feather's
port, a short cable behind the hub should work.

**Setup.** Feather 2 with the TFT FeatherWing, CircuitPython 11.0.0-alpha.2 as
in §6.9, the built-in PIO port. The hub is the Raspberry Pi USB 3 hub
(Adafruit 6012: Infineon CYUSB3304, 8 cm captive upstream cable, four USB-A
ports), powered from its USB-C input. CircuitPython builds with
`CFG_TUH_HUB 2`. The PIO port runs at full speed, so the hub runs as a
full-speed USB 2 hub. The FM-1 ran V15 throughout.

**The hub only appears if the Feather powers up with it attached.** Plugged
into a running Feather, nothing enumerated, not even the hub, and neither
re-creating `usb_host.Port` nor `microcontroller.reset()` changed that. After a
full power cycle of the Feather with the hub in place, it worked.
`usb.core.find` never lists the hub itself, only the devices behind it.

| Hub to FM-1 | How the FM-1 got there | Result |
|---|---|---|
| 2 m (6279) | Feather power cycle | Connected (`4c4a:c755`), steady for 10 s; "Connect to FM-1" worked |
| Short yellow cable | Swapped in with everything running | Nothing in 10 s |
| Short yellow cable | Feather power cycle | Connected, steady for 10 s; "Connect to FM-1" worked |
| Short yellow cable | FM-1 power cycles, Feather running (about 10) | **Silent from the first, never came back** |

The watcher polled `usb.core.find` every 0.25 s and flagged an FM-1 that
hadn't returned 12 s after a detach. It logged one detach, at the first
power-off, then nothing. After the run the port still saw no device.

**What this shows:**
- **The hub doesn't fix V15 on a short cable.** Its only short-cable
  successes came when the Feather powered up. With the FM-1 power-cycling on
  its own, as it does during every install, V15 went silent as it does
  directly on the PIO port (§6.12).
- **It weakens the Feather-port suspects.** The hub's port has the 15 kΩ
  pull-downs the PIO port lacks (§6.6) and is fed from the hub's own supply,
  not the Feather's boost and fuse, yet V15 still picked host. So the
  termination and the Feather's power path aren't the whole story; the
  cable's own resistance still fits (§6.12). One cable and one run, though.
- **Not tested:** the 2 m cable behind the hub through FM-1 power cycles, and
  an install through the hub.

### 6.14 Stuck in V15's loader, and V15 on the breakout chain (Oct 29)

**V15 over the yellow cable + the chain (0.48 Ω, §6.12).** Installed from
the touch UI, directly on the PIO port, no hub. V15 went on, but the factory
voice restore failed. The firmware it replaced, the error text and the
console weren't recorded. Rerun from the REPL over the 2 m cable
(`find_fm1`, then `Updater.restore_factory()`), the restore took 5.4 s. A
first REPL attempt with a fresh `fm1usb.finder` got "no FM-1 answered", the
§6.9 missed-queries quirk. So V15 got through at least one restart on this
chain. The likely failure is its re-enumeration after the first boot (§6.7),
unconfirmed. Borderline, like the 1 m blue.

**Clipper → V15 through a second hub: stuck in V15's loader.** An Anker
A8365 6-in-1 USB-C PD hub, externally powered, on the PIO port through a
USB-C to USB-A adapter, then Adafruit's 1 m purple USB-A to C cable to the
FM-1. The install never wrote V15: the FM-1 was left in V15's update loader.
No console log. On the Mac:
- It enumerated as `4d4a:4155`, "USB Composite Device" from "Jieli
  Technology", at 12 Mb/s, with a MIDI interface.
- `flash_cli.py probe`: identity `ota-FM-1_015`, kind loader.
- `flash_cli.py install sd_out/firmware/stock-v15` connected in resume mode
  and installed V15 with factory voices in 12 s (the write about 9 s, the
  restore under 1 s).
  Log: `logs/install-20261029-093211-FM-1_015.jsonl` (gitignored).

**What probably happened.** From a community firmware, the stock route
stages V15's loader, the FM-1 restarts into it, and the installer waits for
`ota-FM-1_015` (`Updater.install`, `lib/fm1update.py`). So staging finished
and the restart happened, but the loader never reached the Feather or never
answered. **Hypothesis:** the loader is M-VAVE's code on JieLi's SDK, like
V15, and runs the same role check, which settled on host behind this hub on
the 1 m cable. Unproven: the Feather side wasn't watched, and the purple
cable's resistance isn't measured. It fits that the Mac saw it at once.

**Consequences:**
- Installs back to V15 need the long cable for the loader step too, not
  only for V15's first boot.
- An FM-1 that looks dead after an install may be sitting in a loader. Look
  on the Mac for `4d4a:4155` (V15's loader) or `1209:0002` (Felucca's) and
  resume from there with `flash_cli.py install`. No Pico rescue needed.

### 6.15 Feather RP2350 + MAX3421E wing: V15 on a short cable (Oct 29)

**Why.** The MAX3421E wing never produced the silent state (§4.8), and the
RP2040's RAM is the UI's tightest limit (about 25–31 KB free with the UI up,
§6.10–6.11). The Feather RP2350 (no PSRAM) has 520 KB of SRAM.

**Build.** CircuitPython 11.0.0-alpha.2 for `adafruit_feather_rp2350` with
`patches/cp11-feather-rp2350-max3421e.diff`: `CIRCUITPY_MAX3421E = 1`,
`CIRCUITPY_USB_HOST = 0` and `CFG_TUH_ENUMERATION_BUFSIZE=512`, at the
default clock (the 120 MHz was for PIO-USB). 483 KB of RAM left for stack
and heap at build time. CircuitPython 11's own enumeration retry, no TinyUSB
patch.

**Setup.** The wing on CS D10, IRQ D9 (`device/fm1_max_setup.py`), no TFT,
its 5V jumper open. The FM-1 on V15, on the **yellow cable alone (0.151 Ω)**,
the lowest-resistance cable we have. Driven from the REPL over the USB
console. Once the wing started, V15 attached within 1–2 s. Free RAM: 424–432
KB at the REPL, 397–408 KB before each install.

**Power cycles** (`device/fm1_max_watch.py`, which also counts V15's loader
`4D4A:4155`): **9 of 9 back**, each 2.8–4.0 s after power-on, none SILENT.
Log: `logs/rp2350-max-watch-20261029.log`.

**Installs** (`device/fm1_install.py`, full package checks, 64-byte sends):

| Install | Total | Package check | Loader found after the restart | Write | Lost replies |
|---|---|---|---|---|---|
| V15 → SLOOP 2.8 | 55.1 s | 3.9 s | 3.1 s (`ota-FM-1_900`; 3 s is the installer's own wait) | 41.6 s, 1203 reads | 0 |
| SLOOP → V15 + voices | 47.0 s | 5.3 s | 0.6 s (`ota-FM-1_015`) | 30.4 s, 1244 reads | 0 |

In the V15 install, V15 came back 1.8 s after the write and the voice
restore finished first time in 1.2 s; the installer waited for V15 only
once. V15 stayed attached afterwards. Logs:
`logs/rp2350-max-install-v15-sloop-20261029.log` and
`logs/rp2350-max-install-sloop-v15-20261029.log` (gitignored).

**What this shows:**
- **The wing gets V15 and its loader through on a short cable** where the
  RP2040's PIO port didn't (§6.12–6.14). It's one run of each, but it covers
  every step that has failed: power cycles, V15's loader, and V15's first
  boot with the voice restore.
- **Faster than the RP2040.** The full package check took 3.9–5.3 s; on the
  RP2040 even the reduced check took 9.3–22.8 s (§6.12). Installs were
  47–55 s, against 70–103 s on the RP2040 and 33–43 s from the Mac.
- **Still untested** at this point: the TFT and the touch UI on this board
  (done in §6.16); more cables and more runs.

**Setup snags:**
- A `code.py` that set up a display left D10 claimed in the REPL ("D10 in
  use"); `displayio.release_displays()` freed it.
- `fm1usb` needs `adafruit_usb_host_descriptors` (0.6.0 from PyPI, compiled
  with mpy-cross 11). Missing, the import fails before anything is sent.

### 6.16 The touch UI on the RP2350 + wing, and a shared-SPI-bus fix (Oct 29)

**Wiring.** The wing stays stock (CS D10, IRQ D9). On the TFT FeatherWing V2
3.5", the TCS and DC jumpers are cut and wired to **D11** (TFT CS) and the
**D4** pin (DC). D4 sits where other Feathers have pin 12, so CircuitPython
calls it `board.D12` (or `IO4`); there is no `board.D4`. D7 (`board.D13`) is
the red LED, so it stays free. SD CS stays on D5, touch on I2C. Display,
touch, SD and the wing all worked together from the REPL; `TOUCH_CAL` still
maps the corners to within a few pixels.

**Code.** `lib/fm1ui/device.py` picks the pins from the build: with
`max3421e` present the display uses D11/D12 and `host_setup()` starts the
wing; without it (the RP2040's PIO build) nothing changes. `code.py` calls
`D.host_setup(spi)` after the display. With the UI up: 338 KB free (the
RP2040 had 25–31 KB).

**The bug: no FM-1 in the UI, then a hard fault.** On stock CircuitPython 11
the UI's Connect found no USB device at all (`connect: None after 6.0 s, 0
queries`), even after an FM-1 power cycle, and once the board hard-faulted
into safe mode (`SafeModeReason.HARD_FAULT`) while starting up with the FM-1
attached. The REPL with the host alone found V15 in 0.5 s; the host plus
nonstop SD reads never found it in 30 s, and the host stayed stuck after.
Cause, in `shared-module/max3421e/Max3421E.c`: TinyUSB's host task runs as a
background task, and background tasks also run in the middle of SD and
display SPI transfers, while those hold the bus lock. Then
`tuh_max3421_spi_cs_api()` can't get the lock, returns without selecting the
chip, and `tuh_max3421_spi_xfer_api()` returns false; TinyUSB's MAX3421E
driver ignores that and acts on register values and FIFO lengths it never
read. Only the interrupt callback checked the lock first.

**Fix** (in `patches/cp11-feather-rp2350-max3421e.diff`): a new
`max3421e_spi_busy()`, and `usb_background()` runs `tuh_task()` only when
the bus is free, otherwise it reschedules itself. After it, the host found
V15 within the first ~100 of 7,627 SD reads in 30 s and kept it, and through
a 20 s display refresh loop. The same bug should affect any CircuitPython
board that shares the wing's SPI bus with a display or SD card; worth
reporting upstream.

**Round trip from the touchscreen** (yellow cable, 0.15 Ω; firmware from
the SD card; log `logs/rp2350-max-ui-20261029.log`):

| Install | Total | Package check | Loader found after the restart | Write |
|---|---|---|---|---|
| V15 → SLOOP 2.8 | 55.1 s | 3.3 s | 3.1 s (`ota-FM-1_900`) | 42.7 s |
| SLOOP → V15 + voices | 66.1 s | 22.6 s | 0.7 s (`ota-FM-1_015`) | 31.4 s |

Both Connects answered on the first query, the FM-1 answered at once after
each reload, and the voice restore finished first time. The V15 package
check took 22.6 s here against 5.3 s from CIRCUITPY in §6.15; not looked
into yet (SD reads competing with the host, or the UI's heap).

Reported upstream as
[adafruit/circuitpython#11692](https://github.com/adafruit/circuitpython/issues/11692).

### 6.17 An SD error after a Grimm install, and the wing's floating CS (Oct 29)

**What happened.** After a V15 → Grimm install from the touchscreen (Grimm
installed fine), the UI crashed on its next start, building the list:

```
File "code.py", line 51 → app.py 44 (App.__init__) → catalog.py 91 (tags) → catalog.py 55 (_lines)
OSError: [Errno 5] Input/output error: /firmware/index.txt
```

The path is relative to the SD card's mount, so it's `/sd/firmware/index.txt`.
The reset reason was `RESET_PIN`, and the REPL came up at once, so the UI had
crashed again on the start after the reset. `/sd/flasher.json` was **0
bytes**: the state save at the end of the install had opened the file, then
the write failed. Favourites and the installed firmware were lost; the UI
copes with an empty file. Read from the REPL with no host running, the card
was fine: `index.txt` read whole (4,914 bytes, no NULs).

**A panic at host start.** In the same REPL session (no reset after the UI's
crash), starting the wing with `fm1_max_setup.py` printed `*** PANIC ***`
(the SDK's `panic()`, `ports/raspberrypi/supervisor/port.c`) and hard-faulted
into safe mode. The message after it was lost when USB dropped. Not seen
after a clean reset.

**The wing's CS floats low.** With no `Max3421E` object, D10 reads low: the
MAX3421E is selected and drives MISO, and `sdcardio.SDCard()` fails (`no SD
card`, `EAGAIN`). A failed `SDCard()` also leaves D5 claimed ("D5 in use")
until a reset. With D10 driven high the card answered 5 of 5. The UI starts
the host before it mounts the card, so it holds D10 high; REPL scripts that
use the card without the host must drive D10 high themselves.

**Not the supply.** The FM-1 runs on its internal battery while attached. With
the host started first and the card mounted read-only, nonstop reads of
`index.txt` through 4 FM-1 power cycles on Grimm (`1209:0001`): **6,621
reads in 150 s, 0 errors**, every attach seen
(`logs/rp2350-max-sd-cycle-20261029.log`).

**Then from the touchscreen**, after a clean reset and `flasher.json`
restored (`logs/rp2350-max-ui2-20261029.log`):

| Install | Total | Package check | Write |
|---|---|---|---|
| Grimm → ChoralRoot | 63.9 s | 12.7 s | 41.9 s |
| ChoralRoot → Grimm | 59.7 s | 7.8 s | 42.7 s |

No errors, `flasher.json` saved both times, every Connect and every return
answered on the first query. The I/O error didn't come back. The UI felt
unresponsive for a while when looking for Grimm in the list; the console
shows nothing for it (the UI only logs connects and installs). All of this
turned out to be the computer reading the card over USB (§6.18).

### 6.18 The computer was reading the SD card too: `CIRCUITPY_SDCARD_USB` (Oct 30)

**Symptom.** On the RP2350 + wing the UI's first list after every start took
~19 s, and package checks in the UI took 7.8–22.6 s (3.3–5.3 s from the
REPL). After a reset, SD reads took 1.2–3.8 s each instead of 12 ms, in
steps of 250 ms, sometimes for 10–25 s and sometimes for as long as
watched (96 s), and file reads came back as `ENOENT` or `Errno 5`.

**Not the FM-1.** It looked tied to the FM-1 enumerating, because every test
began with a reset. A debug build (`patches/cp11-feather-rp2350-max3421e-stats.diff`,
read with `device/fm1_max_stats.py`; console and panics also on TX through
the Pico, `device/uart_log_cdc.py`) showed the USB host idle and cheap: 1,000
frame interrupts a second, `tuh_task()` ~2.8 ms of CPU a second, 35–54 NAKs
in all (endpoint 0, during enumeration). Raw `readblocks()` of 64 sectors
stayed correct and fast (~110 ms) through enumeration. A counter on
`common_hal_busio_spi_wait_for_lock()` timeouts, with the address of the
lock's last taker, named the taker: `wait_for_lock()` itself, which its
comment says is "used by SD card access from USB".

**Cause.** CircuitPython 9+ shows a card mounted with `storage.mount()` to
the computer as a second USB drive (`CIRCUITPY_SDCARD_USB`, default true);
`diskutil` listed it as a 15.9 GB disk. After every reset or remount the Mac
probed it, from the board's background tasks, while the board's own code
held the bus: each side waited out the other's 250 ms lock timeout. The
read path FatFs uses, `sdcardio_sdcard_readblocks()`, ignores a lock
timeout ("No caller actually uses this value") and leaves the buffer as it
was, so FatFs got stale sectors: the slow reads, `ENOENT`, `Errno 5`. A
write with stale FAT sectors damages the card: this is the likely cause of
the empty `flasher.json` (§6.17), and while timing the UI with the card
mounted read-write (a view switch saved `flasher.json`), the card lost its
whole `firmware/` folder and its FAT showed the card as nearly empty. The
card was reformatted (FAT32) and refilled from `sd_out/full/firmware`;
`.metadata_never_index` on it keeps Spotlight out when it's in the Mac.

**Fix.** `CIRCUITPY_SDCARD_USB = false` in `settings.toml`, read at boot
(no rebuild); `tools/deploy.py` now sets it. With it, the card no longer
appears on the Mac and the three-reset test had 0 lock timeouts. The UI's
`host_setup()` doesn't need a settle wait (tried, removed).

**From the touchscreen after the fix** (`logs/rp2350-max-ui3-20261030.log`):

| Install | Total | Package check | Write |
|---|---|---|---|
| Grimm → Golana | 84.4 s | 1.3 s | 73.2 s |
| Golana → Grimm | 52.6 s | 1.3 s | 42.0 s |

Browsing felt fast; page turns are ~0.75–0.9 s (about 0.45 s of it the
full-screen refresh, and ~12 ms per `index.txt` open, 16 a list page). Every
Connect and return answered on the first query. The Golana write took 31 s
longer than Grimm's for the same size package (610 KB), the same loader and
no resends; one run, not explained.

**What this changes:**
- **The shared-SPI-bus driver fix (§6.16) still stands**, but its two
  motivating failures (no FM-1 in the UI, the hard fault) may partly have
  been this collision too: SD-over-USB was on throughout.
- **The wing's floating CS (§6.17) is real** and separate.
- **The RP2040 builds expose the card the same way**, so the slow package
  checks there (§6.12) may have had the same cause; untested.

### 6.19 On a LiPo alone: an install works, but the Feather resets at first (Oct 30)

**Setup.** The RP2350 + wing + rewired TFT, the FM-1 on the short cable, on
DRIFT. The regular firmware plus a console on TX (GPIO0): the two
`CIRCUITPY_CONSOLE_UART` lines from the stats patch's `mpconfigboard.h`,
nothing else. The Pico logged it (`device/uart_log_cdc.py`,
`logs/rp2350-max-battery-20261030.log`). The UI was started on USB, then the
Mac's USB unplugged. The LiPo's size and charge weren't recorded; the CHG
LED was off on USB.

**What happened.** Unplugging gave an instant white screen: backlight on,
panel never set up, no NeoPixel. The wing's 5 V LED stayed green. The UART
log showed **six hardware resets** (a fresh boot banner, no traceback),
each 1–4 s after the UI came up, sometimes before it finished:

| Time | Event |
|---|---|
| 17:15:24 | Boot on unplugging; UI up at :33 |
| 17:15:36, 17:15:44 | Resets; after the second, a white screen until the reset button |
| 17:18:30 | Reset button (NeoPixel: the usual yellow safe-mode window); UI up at :33 |
| 17:18:33, 17:18:37 | Resets; UI up at :40 and stable |
| 17:20:22 | One more reset, ~50 s after a Connect; the next Connect took 5.8 s to answer instead of 0.0 s |

**Then an install on battery worked:** DRIFT (`FM-1_999`) → FOMAJAM
(`FM-1_961`) in **54.1 s**: package check 1.3 s, loader by 7.8 s, write
43.2 s, the new app found at 54.1 s. No reset during it, through the FM-1's
two reboots, or at the UI's restart after it (338 KB free).

**Likely cause, unconfirmed: the supply sags when the FM-1 attaches.** The
backlight and the wing's 5 V boost run straight from the LiPo and stayed
on; the Feather's 3.3 V side is what dropped out. On battery the LiPo feeds
the Feather, the backlight and, through the wing's boost, the FM-1, which
charges its own battery from VBUS while attached. The resets came just after
the host started and the FM-1 attached, and stopped after a few minutes, as
a charging current easing off would. Not yet ruled out: a weak or small
LiPo. To confirm: start on battery with the FM-1 unplugged; measure BAT
during a reset.

**If it is the FM-1's load:** a larger or fresher LiPo; or switch the wing's
5 V on only for the FM-1 (its `5V_EN` pad, or the solder jumper to the
MAX3421E's GPOUT0).

**Not seen again (closed, Oct 30).** After the white-screen fix (§6.20)
and the switch back to the regular firmware, no resets on battery: 9 of 9
EN power-ons, then 3 of 3 more, all reached the UI and stayed up. What
caused the six resets wasn't found. If they come back, start with BAT during
a reset and the LiPo's size and charge.

**Aside.** One soft reload after a Ctrl-C into the running UI reported
207 KB free instead of 338 KB; a hard reset gave 338 KB again. Not seen
after installs.

### 6.20 A white screen after switching on with EN (Oct 30)

**Pattern.** On battery, switching the Feather on with the TFT FeatherWing's
ENABLE switch gave a white screen every time. Waiting a couple of seconds
and pressing reset usually brought the UI up. **The same with the FM-1
unplugged**, so it isn't the FM-1's load (§6.19 suspected that for the
resets). The UART log showed each power-on as a clean boot that reached the
UI (`free RAM: 338416`): the code ran; the panel didn't show it.

**The panel's reset isn't the Feather's.** In the TFT V2's board file
(Adafruit-3.5in-Capacitive-Touch-TFT-FeatherWing-PCB), the HX8357's reset
(`TFT_RST`) comes from its own voltage supervisor (IC1, APX80x), which holds
the panel in reset while 3.3 V is below its threshold and releases it a
moment later. The Feather's reset button doesn't reach it. A reset panel
shows white until it gets its setup again. So the likely sequence: the setup
is sent, then the panel is reset again as the supply settles at power-on,
and the UI keeps drawing to a panel that's waiting for its setup. Pressing
reset later sends the setup to a settled panel. (The ENABLE switch ties the
Feather's EN to the backlight driver's enable, `LCD_LITE`.)

**Mitigation** (`lib/fm1ui/device.py`), on the first run after any start
(`RunReason.STARTUP`; the install's reloads and auto-reloads are
unchanged): `display_redo()`, called in
`code.py` just before the first screen, sends the panel its setup again. It
replays `adafruit_hx8357._INIT_SEQUENCE` over `display.bus` (0.8 s, most of
it the sequence's own delays) instead of rebuilding the display.

**Tuning.** The first version waited 2 s before the first setup and resent
it 3 s after: 3 of 3 power-ons came up, but about 10 s from switching on to
the list. With the resend moved to after the App loads, both waits were cut
to 0 (set from `settings.toml` for the test): **9 of 9 power-ons with EN on
battery came up**, the first setup 1.5 s into `code.py` and the resend at
3.3 s, every time. About 5 s from switching on to the list, as before the
fix. The waits are gone from the code. Reloads still start at once.

**Plugging into USB, too.** With the mitigation limited to power-ons,
plugging the Feather into the Mac gave the same white screen. That start
reports `ResetReason.RESET_PIN`, not `POWER_ON`, so the resend was
skipped. Now it runs on every `RunReason.STARTUP` and skips only reloads.
3 of 3 USB plug-ins and 3 of 3 EN power-ons on battery came up. A
reset-button start pays the 0.8 s resend too, which is harmless.

### 6.21 The Learn Guide's firmware: a custom build from upstream `main` (Nov 2)

**Why custom.** Stock CircuitPython for the Feather RP2350 has the PIO USB
host on and the MAX3421E off; the two can't be built together (duplicate
`hcd_*` symbols). Upstream (#11697) prefers a custom build for now and, long
term, one build that supports either driver. A custom UF2 is frozen: nothing
rebuilds it.

**What it is.** Upstream `main` at `bf9a1fc492` (after 11.0.0-alpha.2; it
includes the shared-SPI-bus fix, #11695, which no release has yet) plus
three lines in `ports/raspberrypi/boards/adafruit_feather_rp2350/mpconfigboard.mk`:

```
CIRCUITPY_MAX3421E = 1
CIRCUITPY_USB_HOST = 0
CFLAGS += -DCFG_TUH_ENUMERATION_BUFSIZE=512
```

Built locally (`make BOARD=adafruit_feather_rp2350`), on the local branch
`fm1-feather-rp2350-max3421e` (commit `4de5615a2b`). It reports
`11.0.0-alpha.2-62-g4de5615a2b`. UF2 sha256 `30a848ab059873ac131e659f8c6ef56829fe978f2820a452efdf988ba8f7895e`.
The map has the MAX3421E driver and no PIO host. 231 KB of flash free.

The `build-board-custom` workflow can't make this build from flags alone:
they go to `make` as variables, and the buffer size is a `CFLAGS` define.
Without the 512 buffer the FM-1 (293-byte configuration descriptor) never
mounts, with no error.

**Tests on the bench** (RP2350 + wing + rewired TFT, FM-1 on the short
cable): 337 KB free after a hard reset, as on the old build; the panel resend
of §6.20 runs; the FM-1 connects. Installs: DUB-1 5 of 5; V15 4 of 5, with
the voices restored each time it passed. The one failure was the first V15
install, unlogged: the touchscreen said "Install failed", yet V15 had
installed, so it most likely failed at V15's restart or the voice restore
(§6.7). The logger wasn't the difference: three of the passes ran without
it. Not explained.

---

## 7. Tools and techniques worth reusing

- **TinyUSB host logs from CircuitPython:**
  - Build with `CIRCUITPY_DEBUG_TINYUSB 2` and `CIRCUITPY_CONSOLE_UART_TX/RX` in
    `mpconfigboard.h`, plus `CORE1_CHECK_ROOTS=` on the make line. Debug builds
    fail the core1 flash check otherwise.
  - Read the log with a second board: `device/uart_log.py`, or
    `device/uart_log_cdc.py`, which copies it to `usb_cdc.data`.
  - Don't `print()` a log that arrives on the same board's console UART. It
    echoes back into itself.
- **Line state without claiming the pins.** In `memorymap.AddressRange(start=0xD0000004, length=4)`,
  read with `bytes(r[0:4])` (IO registers need aligned 4-byte access).
  Pico-PIO-USB inverts its pad inputs, so `1` means low.
- **RAM counters read from Python.** Put a `volatile uint32_t` array with a
  magic word in the C code, find its address with `arm-none-eabi-nm`, and read
  it through `memorymap` (`device/fm1_stats.py`).
- **Line watcher** (`device/fm1_lines.py`): plain GPIO inputs with pull-downs,
  logging J, K and SE0 changes while a device is plugged in. This is what
  found the role-detect loop.
- **Replug and power-cycle harness** (`device/fm1_replug.py`): logs each
  attach and detach with an identity probe. `fm1_replug_log.py` adds the
  TinyUSB log and line samples.
- **SysEx stress test** (`device/fm1_sysex_stress.py`): long host-to-device
  messages the device ignores (manufacturer 0x7D), with identity checks in
  between.
- **Lossy-link simulator** (`tools/fake_fm1.py`):
  - `lossy_over` and `lossy_modes` drop long host messages until the
    transport slows down.
  - `retry_ms` and `retries` model the loader's repeat-then-silence.
- **CircuitPython build recipe:**
  - `make -C ports/raspberrypi BOARD=… BUILD=build-<name> -j10` with the cp
    venv on PATH.
  - Apply `patches/` to a 10.3.1 checkout.
  - 120 MHz: `-DSYS_CLK_HZ=120000000 -DPLL_SYS_VCO_FREQ_HZ=1440000000 -DPLL_SYS_POSTDIV1=6 -DPLL_SYS_POSTDIV2=2`.

---

## 8. Superseded conclusions

These appeared in `PLAN.md` or in our reasoning at the time, and are wrong:

| Earlier claim | What's actually true |
|---|---|
| The descriptor size was the blocker (Oct 22) | Needed, but the FM-1 wasn't even attaching yet |
| The FM-1 treats the port as a charger because of weak pull-downs (Oct 25) | 15 kΩ pull-downs changed nothing; the FM-1 runs a role-detect loop |
| Attach depends on USB-C power/termination, not host software (Oct 25) | It was TinyUSB not retrying, plus a Pico-PIO-USB stuck-connected bug |
| Longer waits help | The 2 s debounce made it worse; longer reset recovery made it worse |
| The 20 µs reply timeout was needed | The FM-1 answers within 1 µs |
| The GPIO18 tests may not have removed VBUS, because the boost might not disconnect its output | It does disconnect (EN < 0.4 V turns the output fully off), so the tests were valid: removing VBUS for 2–5 s doesn't wake a silent FM-1 |
| VBUS is not involved at all | Removing VBUS from a silent FM-1 doesn't help, but only the built-in port (boost + fuse) produces the silent state; the Pico on Mac 5 V and the MAX3421E don't. Conditions at plug-in or power-on are still a suspect, though unproven |
| A host reset clears the silent state; the host side is stuck (§6.5) | The host is fine: the silent FM-1 is in USB host role with D+ pulled down. Feather resets work only sometimes (§6.6) |
| The silent state comes from the port's power path or termination (§4.8) | It's the FM-1 choosing host role (§6.6), and on the PIO port it happens with short cables. The boost, the 22 Ω resistors and the board are cleared (§6.7) |
| CircuitPython 11 doesn't need the Pico-PIO-USB disconnect check (§6.5) | It does: without it the port can stay "connected" to a role-detecting FM-1 and never enumerate it (§6.7) |
| Grounding the cable shield at the host end prevents the silent state (Oct 27 hypothesis) | It didn't; the cable's length is what mattered (§6.7) |
| Cable length decides it (§6.7) | Not length alone: 55–60 cm with thin wire and extra contacts works, 1 m of normal cable mostly doesn't. Resistance fits better (§6.12) |
| The FM-1 firmware doesn't matter (§6.7) | It does on short cables: V15 runs a host/device role check that can settle on host, SLOOP is device-only and connected on all of them (§6.12). On a long cable both work |
| The yellow cable is charge-only (§6.7) | It carries data; the FM-1 was probably already in host role (§6.12) |

---

## 9. Open questions

- **Why does a short cable make V15's role check pick host** on the PIO port
  (§6.12)? SLOOP has no role check, so it isn't affected. It tracks resistance
  better than length. A powered hub's port, with proper pull-downs and its
  own supply, didn't help (§6.13).
  Is it a VBUS surge or the data lines? Why is the MAX3421E fine with a short
  cable, and why did the same short cable work 7–8 times in 10 on earlier
  days? Next: measure each combination's VBUS–GND loop resistance, then try
  a short cable with ~1 Ω in series in VBUS only (§6.12).
- **Does V15's update loader run V15's role check** (§6.14)? An FM-1 stuck
  in it behind a hub on a 1 m cable suggests so. Watch the loader come up on
  the PIO port with a short cable. (On the MAX3421E wing it came up in 0.6 s
  on a short cable, §6.15.)
- **Was the slow package check on the RP2040** on Oct 29 (9.3 s for SLOOP,
  22.8 s for V15, against 1.6 s and 4 s in §6.10) the computer reading the
  card over USB too? On the RP2350 that was the cause (§6.18): 1.3 s with
  `CIRCUITPY_SDCARD_USB = false`.
- **What caused the panic at host start** after the UI's crash (§6.17)? Its
  message was lost; the debug build now also prints to TX.
- **Why did the Grimm → Golana write take 73 s** against 42 s for the same
  size package (§6.18)?
- **CircuitPython 11 `hashlib`** wrong digests on a fragmented heap (§6.7):
  needs a standalone repro for an upstream issue.
- **Why does the MAX3421E lose multi-packet OUT bursts** to the FM-1's loaders
  and the busy SLOOP app, when the Mac doesn't? The NAK-handling theory is
  unproven.
- **What gets a host-role FM-1 back into device mode?** The Mac does it at
  once; a Feather reset only sometimes, and FM-1 power cycles not at all.
- **Phase 4 hardware:** the MAX3421E wing (CS D10, IRQ D9) and the 3.5" TFT
  FeatherWing (TFT CS D9, DC D10) clash. Resolved on the RP2350 by rewiring
  the TFT's CS and DC to D11 and D4 (§6.16).
