# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MatrixPortal S3 Analog Clock

An analog clock for the Adafruit MatrixPortal S3 with a 32x32 RGB LED
matrix panel. The clock displays hour and minute hands over a gradient
background that shifts through four color palettes across the day.
Designed for use with a diffuser panel for a soft, blurred aesthetic
inspired by LED artwork behind thick resin.

## Hardware

- [Adafruit MatrixPortal S3](https://www.adafruit.com/product/5778)
- [32x32 RGB LED Matrix - 4mm Pitch (PID 607)](https://www.adafruit.com/product/607)
- LED matrix diffuser panel (optional, recommended)
- USB-C power supply

No Address E jumper is needed for the 32x32 panel.

## CircuitPython Libraries

Install the following from the
[CircuitPython Library Bundle](https://circuitpython.org/libraries)
into the `/lib` folder on your CIRCUITPY drive:

- `adafruit_ntp.mpy`

These are only required for WiFi/NTP mode. The clock also runs in
offline manual mode without them.

## Installation

1. Install [CircuitPython](https://circuitpython.org/board/adafruit_matrixportal_s3/)
   on the MatrixPortal S3
2. Copy the required libraries to `/lib` on the CIRCUITPY drive
3. Copy `settings.toml` and `code.py` to the root of the CIRCUITPY drive
4. Edit `settings.toml` with your WiFi credentials and standard UTC
   offset (e.g. `-5` for US Eastern, `-8` for US Pacific)

## Usage

### Boot Modes

**WiFi mode** — If valid WiFi credentials are in `settings.toml`, the
clock connects to WiFi, syncs time via NTP, and starts the clock
automatically. Time re-syncs every hour.

**Offline mode** — If no WiFi credentials are found or the connection
fails, the display shows a message and enters a manual time-set screen:

- **UP button (short press)** — Increment the blinking value
- **DOWN button (short press)** — Toggle between hours and minutes
- **Long press either button (1.5s)** — Confirm time and start clock

### Controls (Clock Running)

- **UP button (short press)** — Toggle wave animation speed (calm / fast)
- **UP button (long press 1.5s)** — Cycle display rotation (0° → 90° →
  180° → 270°) for different USB cable mounting directions
- **DOWN button** — Cycle background palettes (morning → day → evening →
  night → auto)

### Time Periods

The background gradient changes automatically based on the time of day:

| Period  | Hours       | Gradient                        | Hand Color |
|---------|-------------|---------------------------------|------------|
| Morning | 6 AM–12 PM  | Purple → Gold → Olive Green     | Cyan       |
| Day     | 12 PM–5 PM  | Blue → Pale Blue → Sandy Tan    | Orange     |
| Evening | 5 PM–8 PM   | Teal → Salmon → Periwinkle      | Yellow-Green |
| Night   | 8 PM–6 AM   | Pink → Purple → Blue            | Yellow     |

Color palettes are inspired by the Florida Arts License Plate.

### Daylight Saving Time

US Daylight Saving Time is computed automatically from the NTP date
(2nd Sunday in March through 1st Sunday in November). Set
`TZ_STD_OFFSET` in `settings.toml` to your standard UTC offset (e.g.
`-5` for Eastern) and `DST_AUTO = "true"`. The clock adds +1 hour
during DST with no external API dependency.

For non-US timezones or locations that don't observe DST, set
`DST_AUTO = "false"` and use the correct fixed offset.

### Features

- Animated wave effect on the background gradient
- Radial glow vignette (brighter center, dimmer edges)
- Soft glow halo around clock hands
- Twinkling yellow stars during nighttime mode
- Plus-shaped hour markers at each 5-minute position
- NTP time sync with offline fallback
- Manual time set for use without WiFi

## Customization

Key values to adjust at the top of `code.py`:

- `WAVE_SPEED` / `WAVE_SPEED_FAST` — Animation speeds
- `WAVE_AMP` — Wave intensity (row displacement)
- `GRAD_*` — Background gradient color stops per period
- `HAND_*` — Hand colors per period
- `MARKER_*` — Hour marker colors per period
- `MORNING_HOUR`, `DAY_HOUR`, `EVENING_HOUR`, `NIGHT_HOUR` — Period
  boundaries (24-hour format)
- `BG_MULTS` — Radial glow brightness tiers
- `GLOW_RADIUS` — How far the center glow extends
- `STARS` — Star positions and twinkle phase offsets

Key values in `settings.toml`:

- `TZ_STD_OFFSET` — Standard UTC offset (e.g. `-5` for Eastern)
- `DST_AUTO` — Enable/disable US DST computation
- `DISPLAY_ROTATION` — Default rotation (0, 90, 180, 270)
