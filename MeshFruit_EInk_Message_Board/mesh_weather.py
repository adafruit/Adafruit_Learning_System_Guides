# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Forecast lookup and moon phase maths.

Open-Meteo is free and needs no API key. It wants coordinates, so a
ZIP is resolved once through Zippopotam, which is also keyless.
Neither service reports moon data, so the phase is computed here.
"""

import os

WEATHER_INTERVAL = 1800  # seconds between fetches


# Open-Meteo is free and needs no API key. Coordinates come from
# settings.toml so the guide does not hardcode a location.
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=%s&longitude=%s"
    "&current=temperature_2m,weather_code"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
    "&temperature_unit=%s&timezone=auto&forecast_days=3"
)


# Open-Meteo wants coordinates, so a ZIP is resolved once per boot
# through Zippopotam, which is also free and keyless.
ZIP_URL = "https://api.zippopotam.us/us/%s"


# Condensed WMO weather codes. Full table at open-meteo.com/en/docs
WMO_CODES = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Showers",
    81: "Showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Severe storm",
}


def describe_code(code):
    """Human readable form of a WMO weather code."""
    return WMO_CODES.get(code, "Code %s" % code)


def clock_time(stamp):
    """Turn an ISO timestamp into a short 12 hour clock time."""
    try:
        hour = int(stamp[11:13])
        minute = stamp[14:16]
    except (ValueError, IndexError, TypeError):
        return None
    suffix = "a" if hour < 12 else "p"
    hour = hour % 12 or 12
    return "%d:%s%s" % (hour, minute, suffix)


location = None


def resolve_location(session):
    """Return (latitude, longitude) as strings, or None.

    Explicit coordinates win. Otherwise a ZIP is looked up once and
    cached for the rest of the session.
    """
    global location  # pylint: disable=global-statement
    if location is not None:
        return location

    latitude = os.getenv("LATITUDE")
    longitude = os.getenv("LONGITUDE")
    if latitude and longitude:
        location = (latitude, longitude)
        return location

    zip_code = os.getenv("ZIP_CODE")
    if not zip_code:
        print("weather: set ZIP_CODE or LATITUDE/LONGITUDE in settings.toml")
        return None

    try:
        response = session.get(ZIP_URL % zip_code, timeout=20)
        data = response.json()
        response.close()
        place = data["places"][0]
        location = (place["latitude"], place["longitude"])
        print("weather: %s resolved to %s" % (zip_code, place["place name"]))
        return location
    except Exception as zip_error:  # pylint: disable=broad-except
        print("zip lookup failed:", zip_error)
        return None


def fetch_weather(use_fahrenheit=True):  # pylint: disable=too-many-locals
    """Pull a short forecast from Open-Meteo. Returns a dict or None.

    WiFi is brought up only for the fetch and shut down afterwards:
    the ESP32-S3 radio sits close to the LoRa front end, and there is
    no reason to keep it running between updates.
    """
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid:
        print("weather: no wifi credentials in settings.toml")
        return None

    try:
        import wifi  # pylint: disable=import-outside-toplevel
        import socketpool  # pylint: disable=import-outside-toplevel
        import ssl  # pylint: disable=import-outside-toplevel
        import adafruit_requests  # pylint: disable=import-outside-toplevel

        wifi.radio.enabled = True
        if not wifi.radio.connected:
            wifi.radio.connect(ssid, password)
        session = adafruit_requests.Session(
            socketpool.SocketPool(wifi.radio), ssl.create_default_context()
        )

        coords = resolve_location(session)
        if coords is None:
            return None

        url = WEATHER_URL % (
            coords[0],
            coords[1],
            "fahrenheit" if use_fahrenheit else "celsius",
        )
        response = session.get(url, timeout=20)
        data = response.json()
        response.close()
    except Exception as weather_error:  # pylint: disable=broad-except
        print("weather fetch failed:", weather_error)
        return None
    finally:
        try:
            wifi.radio.enabled = False
        except Exception:  # pylint: disable=broad-except
            pass

    try:
        current = data["current"]
        daily = data["daily"]
        return {
            "now": round(current["temperature_2m"]),
            "code": current["weather_code"],
            "highs": [round(v) for v in daily["temperature_2m_max"]],
            "lows": [round(v) for v in daily["temperature_2m_min"]],
            "codes": daily["weather_code"],
            "sunrise": clock_time(daily["sunrise"][0]),
            "sunset": clock_time(daily["sunset"][0]),
            "date": current.get("time") or daily["sunrise"][0],
        }
    except (KeyError, TypeError, IndexError) as parse_error:
        print("weather parse failed:", parse_error)
        return None


MOON_NAMES = (
    "New moon",
    "Waxing crescent",
    "First quarter",
    "Waxing gibbous",
    "Full moon",
    "Waning gibbous",
    "Last quarter",
    "Waning crescent",
)

# Days between new moons.


# Days between new moons.
SYNODIC_MONTH = 29.530588853


def days_since_epoch(year, month, day):
    """Days from 2000-01-01 to the given date, via a Julian day count."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    julian = (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )
    return julian - 2451544.5


def moon_phase(stamp):
    """Fraction through the lunar cycle, 0 at new moon, from an ISO date."""
    try:
        year = int(stamp[0:4])
        month = int(stamp[5:7])
        day = int(stamp[8:10])
    except (ValueError, IndexError, TypeError):
        return None
    # 2000-01-06 was a new moon, five days past the epoch above.
    age = (days_since_epoch(year, month, day) - 5.0) % SYNODIC_MONTH
    return age / SYNODIC_MONTH


def moon_name(phase):
    """Name the phase, snapping to the exact quarters."""
    return MOON_NAMES[int((phase * 8) + 0.5) % 8]
