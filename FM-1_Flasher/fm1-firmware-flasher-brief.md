# FM-1 Firmware Flasher: project brief

A portable CircuitPython device that stores M-VAVE FM-1 alt firmwares on a microSD card and installs them over USB MIDI SysEx, no computer needed. Plug the FM-1 into the flasher, pick a firmware on the touchscreen, tap Install.

This brief comes from a research conversation with Claude (October 22, 2026). Items are marked **[verified]** when they were read directly from source code or files, and **[unverified]** when they are assumptions to test early.

---

## 1. Background

- **M-VAVE FM-1**: an inexpensive FM synth with a large alt-firmware scene (40+ firmwares). Its chip is a JieLi **AC791N**. [verified: the updater checks for the string `AC791N` in the package header]
- **The Firmware Hub** (https://thefirmwarehub.com/) installs open-source FM-1 firmwares from Chrome/Edge over Web MIDI. It says it uses "the same update protocol as M-VAVE's own updater: first the running firmware stages the new package's update loader, then the loader writes the firmware," and that "the update path is Felucca's, as sloopDX carries it."
- **M-VAVE's official SDK**: https://github.com/m-vave/fm1_open (the commit read for this brief was `4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`, Oct 21 2026).
  - `sdk/WebUpdate.js` is the reference browser updater.
  - `sdk/firmware/FM-1_015.fwsc` is stock V15 (699,956 bytes). The SDK ships it under Apache-2.0.
- **License**: `WebUpdate.js` is `SPDX: GPL-3.0-only WITH GPL-3.0-linking-exception` [verified]. Porting its logic to Python is fine if the flasher is released as GPL-3.0. Each firmware is under its own license (mostly GPL-3.0), so a preloaded SD card should include source links for each project, as the hub does.

## 2. Hardware

Primary target:
- **Adafruit Feather RP2040 USB Host**: native USB-C for CIRCUITPY, plus a USB-A host port driven by PIO USB.
- **TFT FeatherWing**, either 2.4" (320×240) or 3.5" (480×320). Both have resistive or capacitive touch screen (need to specify which version/model) and a **microSD slot**, and share SPI between the TFT and SD with separate CS pins. The 3.5" is the better pick: room for the list, details, and a progress bar. But we should build both.
- LiPo battery on the Feather for portability. The FM-1 has its own battery.

Alternative: **Fruit Jam** (RP2350; has USB host ports, microSD, and display output).

Hardware items to check first:
- **[unverified] VBUS on battery.** Does the Feather's USB-A host port supply 5 V when the Feather runs from LiPo? The FM-1 may not enumerate without VBUS. If it doesn't, add a 5 V boost converter feeding the host port's VBUS.
- **[unverified] Pin conflicts.** Confirm the PIO USB host pins don't collide with the FeatherWing's TFT CS, DC, SD CS, or touch pins.
- **[unverified] `hashlib`.** Check whether the RP2040 CircuitPython build includes `hashlib` with sha256. Fallbacks: `adafruit_hashlib` (pure Python, slow on ~700 KB), or verify packages on a computer when preparing the SD card and skip the on-device check.

## 3. Firmware packages (`.fwsc`)

Sizes: FM-1 flash is 1 MiB. Stock V15 is 699,956 bytes. The updater accepts packages from 1,024 to 2,097,152 bytes, and the flash entry inside must be 16 KB to 1,044,480 bytes and a multiple of 4096. In practice expect roughly **0.5–1 MB per firmware**, so the whole catalogue is about 30–40 MB on SD. **Never load a whole package into RAM** (the RP2040 has 264 KB); stream from SD.

### Package layout [verified, from `inspectPackage()` in WebUpdate.js]

1. **First 960 bytes = 20 rows × 48 bytes.** Each row is 47 data bytes plus 1 marker byte.
   - Marker for row `i`: if it equals `125` (`}`), the name has ended. Otherwise `char = (marker - i - 1) & 0xFF`, a printable ASCII character of the **product name** (identity string, e.g. `FM-1_015`).
   - The **image** is the 47 data bytes of each row concatenated (940 bytes), followed by `bytes[960:]`. So `len(image) = len(file) - 20`.
2. **Image header**: `image[0:64]` passed through `decodeHeader()` (see below).
   - `le16(h,0) == crc16(h[2:])`
   - `le32(h,4) == len(image)`
   - `h[16:32]` ASCII == `"AC791N"`
   - `count = le16(h,8)`, between 1 and 12
   - `le16(h,2) == crc16(raw_table)`, where `raw_table = image[64 : 64+count*80]`. The CRC covers the table before decoding.
3. **Entry table**: `count` entries of 80 bytes each, each decoded with `decodeHeader()`. Fields (little-endian):
   - `type = le16(e,0)`: 0 is flash, 100 is the loader, 50 named `USR` is factory voice banks (stock only)
   - `crc = le16(e,4)`
   - `offset = le32(e,8)`
   - `size = le32(e,12)`
   - `stored = le32(e,16)`
   - `encrypted = le32(e,24)`
   - `name = ascii(e[64:])`
   - Unencrypted entries must satisfy `crc16(image[offset:offset+size]) == crc`. There must be exactly one flash entry and one loader entry.

Helper functions (port exactly):
```js
// CRC16-CCITT, nibble table, init 0
crc16Table=[0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef]
crc16: c=0; for b: c^=b<<8; c=((c<<4)^T[c>>>12])&0xFFFF; c=((c<<4)^T[c>>>12])&0xFFFF
// header de-obfuscation, LFSR XOR, key default 0xFFFF
decodeHeader(p,key=0xFFFF): k=key; for i: p[i]^=k&0xFF; k=((k<<1)^(k&0x8000?0x1021:0))&0xFFFF
```

### Mapping image addresses to file offsets (for SD streaming)

The FM-1 requests **image** addresses, not file offsets:
```python
def file_offset(x):            # x = image address
    if x < 940:
        return (x // 47) * 48 + (x % 47)
    return x + 20
```
A 512-byte request that crosses x = 940, or crosses row boundaries below it, has to be assembled from more than one read. Simplest approach: cache `image[0:940]` in RAM at startup (it's tiny) and `seek()` directly for x ≥ 940.

## 4. The update protocol [verified, from WebUpdate.js]

### SysEx frame
```
F0  pack7([0x00, 0x59, cmd, len & 0xFF, len >> 8, 0x00, *payload, (~sum(payload)) & 0xFF])  F7
```
- Payload is at most 520 bytes. `sum` is the 8-bit sum of the payload bytes.
- `pack7` packs a little-endian bit stream into 7-bit bytes:
  ```js
  value|=byte<<bits; bits+=8; while(bits>=7){out.push(value&127); value>>>=7; bits-=7}
  // after the loop: if(bits) out.push(value&127)
  ```
- **Parse** a reply by unpacking the 7-bit stream back to bytes, then check:
  - `raw[0:2] == [0x00, 0x59]`
  - `le24(raw,3) == len(raw) - 7`
  - the sum of `raw[6:]` (including the checksum byte) `& 0xFF == 0xFF`
  - `cmd = raw[2]`, `data = raw[6:-1]`
  - total SysEx length is between 10 and 608 bytes, and there must be no leftover bits (`bits < 7` and `value == 0`)

### Commands
| cmd | direction | meaning |
|---|---|---|
| 17 | query | Identity: a 27-byte ASCII reply, null-padded, e.g. `FM-1_015`, `FM1_OFFICIAL_OPEN`, `FM1_COMMUNITY_n`, `ota-…` in loader mode |
| 49 | query | Capability (FM1 Open-style firmwares only): a 47-byte reply starting with `"FMC1"`. Checks: `d[4]==1`, `d[5]` = family (≤ 7), `d[6]` = state (0 is ready), `d[7]==1`, `le16(d,8)==512`, `le32(d,10)==1048576`. Build hash is `d[14:46]`. Stock V15 and some third-party firmwares **don't answer**, which is a timeout. |
| 50 | query | Arm ("tagged" mode only): payload `[1, family, n&255, n>>8&255, n>>16&255, n>>24&255, *build_id_32_bytes]`, where `n = len(image)`. The ack must be `[0]`. |
| — | raw | **Kick**: `F0 22 24 35 7F F7` (not a framed message) starts a transfer phase. |
| 48 | device → host | **Read request**, 8 data bytes: `p[0]` = sequence, `address = le32(p,1)`, `nbytes = le24(p,5)` (1–512). The host replies `frame(48, [p[0], *p[1:8], *image[address:address+nbytes]])`. |
| 48 | finish | `address == 0xE0000000` (stage 1 done) or `0xF0000000` (stage 2 done), with `nbytes == 8`. The host replies `frame(48, [p[0], *p[1:8], *b"success\0"])`, then keeps listening for about 600 ms and answers any duplicate finish requests the same way. |
| 33 / 34 | query | Factory voice-bank restore, used only when going back to stock V15 (see §6). |

Queries: clear the receive queue, send, then wait up to about 1.5 s (750 ms for the initial identity probe, retried once) for a reply with a matching `cmd`. Ignore unrelated packets.

### Install sequence
1. **Connect**: send cmd 17 and read the identity.
2. **Choose the mode** (this logic is in `Updater.connect()`):
   - Identity already equals the package's loader identity (`ota-…`): **resume** at stage 2.
   - Identity is stock `FM-1_015`: **legacy** mode. No capability or arm step; requires explicit user confirmation.
   - Otherwise query cmd 49. If it answers and the family matches with state 0, use **tagged** mode. If it times out, use **legacy/migration**, which also needs explicit confirmation.
3. **Stage 1** (skip on resume):
   - Tagged mode: re-query cmd 49, confirm the build differs from the package's build_id, then send cmd 50 (arm) and expect ack `[0]`.
   - Send the kick, then serve read requests until the `0xE0000000` finish arrives.
   - Disconnect. **The FM-1 restarts into its update loader and re-enumerates on USB.**
4. **Wait for the loader**: poll until a device answers cmd 17 with the expected loader identity (or any `ota-…` in legacy/stock cases). Allow up to 40 s, probing every ~600 ms.
   - Loader identity: `ota-FM-1_015` if the package's loader SHA-256 is `ef1f2db89b011fa53e71df363f0122de0ea896618c53fb53e8da676322004541` (the vendor loader); `ota-FM-1_015` for the stock package; otherwise `ota-FM1C_` plus the first 16 hex characters of build_id.
5. **Stage 2**: send the kick and serve read requests until the `0xF0000000` finish. Flash erase and write pauses are long, so allow up to 180 s between requests.
6. **Verify**: disconnect, wait for re-enumeration, and confirm cmd 17 returns the package's product identity (plus a cmd 49 build check for tagged firmwares).

### Timing defaults
`idle 10 s` between requests in stage 1, `writeIdle 180 s` in stage 2, `reconnect 40 s`, `settle 600 ms`, `pace 0`. Overall serve cap: `max(idle*3, 120 s)`. The protocol is **request-driven**: the loader asks for the next block only when it's ready, so no fixed pacing is needed. CircuitPython speed shouldn't be a problem.

A transfer is about 1,400 round trips of 512 bytes for a 700 KB package. The hub quotes "about a minute"; expect 1–2 minutes on the Feather.

### Catalogue metadata the updater expects (from `prepare()`)
`schema:1`, `product` (identity), `build_id` (64 hex characters), `family` (7), `bytes`, `sha256` (whole file), `loader_sha256`, `kind` (`"stock"` for V15). Open identities match `^(FM1_OFFICIAL_OPEN|FM1_COMMUNITY_\d+|FM-1_8\d{6})$`. **[unverified]** where build_id comes from for community firmwares. It may be published in release metadata or the hub's catalogue. Check the hub's JS and Felucca's installer.

## 5. CircuitPython USB host side

- Find the FM-1 with `usb.core.find()` and claim the USB-MIDI streaming interface's bulk IN/OUT endpoints.
- Try Adafruit's USB Host MIDI library first. If it doesn't handle long SysEx, build **USB-MIDI 1.0 event packets** by hand (4 bytes each, cable 0):
  - CIN `0x4`: SysEx start/continue, 3 data bytes
  - CIN `0x5`: ends with 1 byte (or a single `F7`)
  - CIN `0x6`: ends with 2 bytes
  - CIN `0x7`: ends with 3 bytes
  - Reassemble incoming SysEx the same way.
- **Re-enumeration is the hardest part.** Between stages, and after stage 2, the FM-1 drops off the bus and comes back, possibly with a different PID or interface layout in loader mode [unverified]. Release the device, poll `usb.core.find()`, reclaim endpoints, and re-probe with cmd 17.
- Keep a receive queue (the web code caps it at 32 packets) and drop non-matching packets.

## 6. Scope notes and gotchas

- **Back to stock V15** also restores factory voice banks: 16 KB decoded from the package's `USR` entry, written with cmds 33/34 in 512-byte chunks per 4 KB bank (`restoreFactory()` / `factoryCheck()` in WebUpdate.js). That's more work, so consider supporting only open firmwares in v1, or port it later. Include V15 on the SD card either way.
- **Third-party identities**: SLOOP, Felucca, and others may not answer cmd 49 and could report identities outside the open-identity regex, so they go through the legacy/migration route with confirmation. Test the full matrix (stock → open, open → open, community → community, → stock) on real hardware.
- **[unverified]** The hub says the community update path "is Felucca's." Compare the hub's own installer JS and Felucca's web installer against `WebUpdate.js` before assuming they're identical.
- **Out of scope:** rescuing a stuck unit. This flasher only works while the update loader runs. A truly stuck FM-1 needs the ROM bootloader ("UBOOT1.00", USB mass storage) and the hub's `fm1_rescue.py` on Linux, or MvaveFM1Unbricker / Transporter (RP2040).
- Power loss mid-write is the main risk. Warn the user to keep both devices charged or on USB power.

## 7. UX

1. Boot to a list of firmwares from SD (name, author, version, size).
2. Plug in the FM-1. Show "Running: <identity>" from cmd 17.
3. Tap a firmware for details, then tap Install. Require an extra confirmation for legacy/migration routes.
4. Progress bar driven by read-request addresses. Show "Restarting…" during re-enumeration, then "Running: <new identity>".
5. Always offer "Back to official V15."

SD layout suggestion:
```
/sd/firmware/<slug>/<file>.fwsc
/sd/firmware/<slug>/meta.json   # name, author, version, product, build_id, family, bytes, sha256, loader_sha256, kind, source_url, license
```
Generate `meta.json` on a computer, with a small script that parses the package header and pulls release info.

## 8. Suggested milestones

1. **USB host + identity probe**: send cmd 17 to the FM-1 from CircuitPython and print the reply. This proves SysEx framing, `pack7`/parse, and USB-MIDI packetization.
2. **Package parser**: port `inspectPackage()` (row de-interleave, `decodeHeader`, `crc16`, entry table) and run it against `FM-1_015.fwsc` and a couple of community packages. Do this on a computer first with CPython, then on the device.
3. **Capability query (cmd 49)** against an FM1 Open-style firmware.
4. **Stage 1 serve loop** streaming from SD using the image-to-file offset mapping, then handling re-enumeration.
5. **Stage 2** and post-install verification.
6. **UI**: TFT FeatherWing list, touch, progress.
7. **Hardening**: timeouts, duplicate finish handling, abort and resume (re-entry when the FM-1 is already in loader mode), low-battery warning.
8. Optional: stock V15 factory-bank restore.

## 9. References
- FM-1 Firmware Hub: https://thefirmwarehub.com/ (Knowledge Base: https://thefirmwarehub.com/kb/)
- M-VAVE SDK and reference updater: https://github.com/m-vave/fm1_open (`sdk/WebUpdate.js`, `sdk/firmware/FM-1_015.fwsc`)
- Felucca: https://github.com/hugelton/Felucca
- SLOOP: https://github.com/isod89/sloop-fm1
- Rescue tools: https://thefirmwarehub.com/rescue/fm1_rescue.py, https://github.com/Quixotic7/MvaveFM1Unbricker, https://github.com/kagaimiq/jl-uboot-tool
