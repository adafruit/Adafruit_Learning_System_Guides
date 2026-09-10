# MeshFruit E-Ink Message Board

Off-grid LoRa mesh message board on a 4.2" tri-color e-ink panel.
Receives and decodes messages compatible with the Meshtastic protocol,
and shows a weather forecast, air quality and battery runtime.

Receive only. This board does not transmit and will not appear in the
mesh node list.

## Hardware

* Adafruit ESP32-S3 Feather, 4MB flash 2MB PSRAM (5477)
* eInk Feather Friend (4446)
* 4.2" 300x400 tri-color eInk display (6382)
* RFM95W LoRa breakout, 915MHz (3072)
* STCC4 + SHT41 CO2, temperature and humidity sensor (6478)
* Soft tactile button (3101)
* 2000mAh LiPo battery

## Wiring

The radio shares the display's SPI bus:

| RFM95W | Feather |
|--------|---------|
| VIN    | 3V      |
| GND    | GND     |
| SCK    | SCK     |
| MOSI   | MOSI    |
| MISO   | MISO    |
| CS     | D11     |
| RST    | D12     |
| G0     | A5      |

G0 is the packet interrupt. It lets the board light sleep between
packets instead of polling, which roughly doubles battery life.

Button between A0 and GND. Sensor on the STEMMA QT port.

D5, D6, D9 and D10 belong to the eInk Feather Friend. Leave the
display's `reset` and `busy_pin` as `None`: the Feather Friend does not
bring those out, and claiming D7 and D8 corrupts the I2C bus and knocks
the STEMMA sensor offline.

## Libraries

Install with `circup`:

    circup install adafruit_meshfruit adafruit_rfm9x adafruit_ssd1683 \
        adafruit_display_text adafruit_bitmap_font adafruit_debouncer \
        neopixel adafruit_requests adafruit_max1704x adafruit_stcc4

## Files

| File | What it holds |
|------|---------------|
| `code.py` | Setup, sensors, display layout, packet handling, main loop |
| `mesh_icons.py` | Weather glyphs drawn with `vectorio`, no bitmap assets |
| `mesh_weather.py` | Forecast lookup and moon phase |

Bring the sensors up before the display, radio or NeoPixel.
`board.STEMMA_I2C()` claims and manages `I2C_POWER` itself, and if
another peripheral gets there first the bus comes up with no pull ups,
which reports as a wiring error rather than a power one.

## Setup

Add these to `settings.toml` on the CIRCUITPY drive:

```toml
CIRCUITPY_WIFI_SSID = "your-network-name"
CIRCUITPY_WIFI_PASSWORD = "your-network-password"
LATITUDE = "40.7128"
LONGITUDE = "-74.0060"
```

Then add the fonts, see `fonts/README.txt`.

## Outside the US

Three things are region specific.

**Radio frequency.** The settings in `code.py` are for the US 915MHz
band, at 906.875 MHz. Other regions use different bands and different
slot spacing, so `FREQUENCY` has to change to match whatever the nodes
around you are using. Check the frequency your own node reports rather
than trusting a table: with the Meshtastic CLI, `meshtastic --info`
prints the operating frequency for your region and modem preset.

**Temperature units.** `USE_FAHRENHEIT` in `code.py`. Set it to
`False` for Celsius, which also switches the forecast request.

One further limitation: the fonts are trimmed to printable ASCII to
save space, so accented characters will not render. If you need them,
keep the Latin-1 range when trimming and expect the font files to grow.

## Using it

Short press cycles weather and messages. Hold for a second to see the
node list.

The panel enforces a 180 second cooldown between refreshes, so this is
a bulletin board rather than a live chat. The NeoPixel carries the fast
feedback the display cannot: blue for a button press, amber when the
change is queued behind the cooldown, green for a new message, and
purple while the panel updates.
