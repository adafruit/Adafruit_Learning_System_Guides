# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Forecast lookup and moon phase maths.

Open-Meteo is free and needs no API key. It reports no lunar data, so
the moon phase is computed here from the date in the response.
"""

import ssl

import adafruit_requests
import socketpool
import wifi

INTERVAL = 1800  # seconds between fetches


# Open-Meteo is free and needs no API key. Coordinates come from
# settings.toml so the guide does not hardcode a location.
HOST = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = "temperature_2m,weather_code"
DAILY_FIELDS = "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"


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
    return WMO_CODES.get(code, f"Code {code}")


def clock_time(stamp):
    """Turn an ISO timestamp into a short 12 hour clock time."""
    try:
        hour = int(stamp[11:13])
        minute = stamp[14:16]
    except (ValueError, IndexError, TypeError):
        return None
    suffix = "a" if hour < 12 else "p"
    hour = hour % 12 or 12
    return f"{hour}:{minute}{suffix}"


def fetch(ssid, password, latitude, longitude, use_fahrenheit=True):
    """Pull a short forecast from Open-Meteo. Returns a dict or None.

    WiFi is brought up only for the fetch and shut down afterwards: the
    ESP32-S3 radio sits close to the LoRa front end, and there is no
    reason to keep it running between updates.
    """
    if not ssid:
        print("weather: no wifi credentials in settings.toml")
        return None
    if not latitude or not longitude:
        print("weather: set LATITUDE and LONGITUDE in settings.toml")
        return None

    unit = "fahrenheit" if use_fahrenheit else "celsius"
    url = (
        f"{HOST}?latitude={latitude}&longitude={longitude}"
        f"&current={CURRENT_FIELDS}&daily={DAILY_FIELDS}"
        f"&temperature_unit={unit}&timezone=auto&forecast_days=3"
    )

    try:
        wifi.radio.enabled = True
        if not wifi.radio.connected:
            wifi.radio.connect(ssid, password)
        session = adafruit_requests.Session(
            socketpool.SocketPool(wifi.radio), ssl.create_default_context()
        )
        response = session.get(url, timeout=20)
        data = response.json()
        response.close()
    except (RuntimeError, OSError, ValueError) as error:
        print("weather fetch failed:", error)
        return None
    finally:
        wifi.radio.enabled = False

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
    except (KeyError, TypeError, IndexError) as error:
        print("weather parse failed:", error)
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
