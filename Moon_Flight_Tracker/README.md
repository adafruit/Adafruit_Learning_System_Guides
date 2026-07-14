# LUNA TRANSIT — hardware build

Flight tracker that filters to planes likely to cross the moon, for the
**Adafruit Qualia ESP32-S3 + 2.1" round 480×480 touch TFT** (product 5792).

## Install

1. Flash CircuitPython 9.x for **Qualia ESP32-S3 RGB666**.
2. Copy to `CIRCUITPY/`:
   - `code.py`
   - `moon_ephem.py`
   - `tl021wvc02.py` (display init sequence)
   - your standard `settings.toml` with WiFi credentials
     (`CIRCUITPY_WIFI_SSID` / `CIRCUITPY_WIFI_PASSWORD`), as in other
     WiFi projects. Optional: `UTC_OFFSET = "-4"` pins the rise/set
     timezone manually — normally unnecessary; the device looks up a
     DST-aware offset for your ZIP automatically.
3. Copy these libraries from the CircuitPython bundle into `CIRCUITPY/lib/`:
   - `adafruit_display_text/`
   - `adafruit_display_shapes/` (RoundRect — rounded panel outlines)
   - `adafruit_bus_device/` (raw CST8xx touch poller)
   - `adafruit_requests.mpy`
   - `adafruit_connection_manager.mpy`
   - `adafruit_ntp.mpy`

   The display is initialized directly (TL021WVC02 init codes in `code.py`);
   the `adafruit_qualia` package is NOT required. Touch uses a built-in raw
   CST8xx I2C poller at 0x15 (the stock focaltouch driver rejects some panel
   revisions' chip IDs).

## Data sources (no API keys)

- **Aircraft**: `opendata.adsb.fi` v2 within 15 nm, every `FETCH_S` (15 s)
- **Routes**: `api.adsbdb.com` callsign lookup, on tap, cached per callsign
- **Location**: ZIP → lat/lon via `api.zippopotam.us` (saved to NVM)
- **Timezone**: `timeapi.io` DST-aware offset (fallback: longitude estimate)
- **Moon**: computed on-device (`moon_ephem.py`, ~0.3° accuracy), NTP for time

## How it decides "transit candidate"

Each plane's az/el (from your location, using baro altitude) is compared
against the moon's az/alt now and stepped 5 min forward along its
track/groundspeed. Minimum angular separation:

- **< 0.5°** (`SEP_HIT`) → **pink** bezel + `TRANSIT` banner — right over the disc
- **< 2°** (`SEP_NEAR`) → **cyan** bezel + `NEAR` banner — half-moon-in-frame shot
- Banner fires when ETA ≤ 90 s; alerts gated off while moon alt ≤ 5°

## UI map (matches the design prototype)

- **RAD** — radar, moon centered (label carries real alt/az), dotted bearing
  line at the moon's azimuth, per-plane min-sep readout, chip toggles
  5 mi ↔ 300 mm (3.1 mi)
- **LIST** — candidates sorted by separation; tap a row for flight detail
- **DETAIL** — type, route (origin → destination), alt/gs/dist/trk, sep/ETA;
  edge arrows page through the list
- **MOON** — phase render (dotted outline at new moon), illumination %,
  alt/az, rise/set in local 12-hour time
- **LOC** — keypad: 5 digits + OK = ZIP; `90`/`180`/`270`/`0` + OK = screen
  rotation (persisted to NVM, touch remapped); `67` + OK = demo mode

## Demo mode (filming/testing)

`67` + OK on the LOC keypad: a fake plane (DEMO67) crosses the radar twice —
30 s dead over the moon (pink TRANSIT), then 30 s offset (cyan NEAR) — then
live data resumes. Each pass animates incrementally at several fps.

## Knobs (top of code.py)

`FETCH_S`, `LOOKAHEAD_S`, `SEP_HIT`, `SEP_NEAR`, `NM_RADIUS`, `PX_PER_MI`,
`DISPLAY_FREQ` (pixel clock — raise toward 16 MHz if your panel is stable),
`DEBUG_TOUCH` (serial tap logging)

## Hardware notes

- WiFi TX power is capped at 8 dBm to reduce RGB-panel jitter during
  fetches; raise it in `code.py` if your AP is far and requests time out.
- Touch: taps landing entirely within a blocking fetch (~1–2 s every 15 s)
  can still be missed — the CST8xx has no event buffer. Everything else is
  press-edge triggered with wake retries.
- If rotated 90/270 and left/right taps feel swapped, swap those two cases
  in `rotate_touch()`.
