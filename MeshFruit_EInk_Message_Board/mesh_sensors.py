# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Air quality sensor and battery gauge.

Bring these up before the display, radio or NeoPixel.
board.STEMMA_I2C() claims and manages I2C_POWER itself, and if
another peripheral gets there first the bus comes up with no pull
ups, which surfaces as a wiring error rather than a power one."""

import time

import board

USE_FAHRENHEIT = True


AIR_READ_ATTEMPTS = 3


AIR_READ_RETRY_SECONDS = 1.0


AIR_SETTLE_SECONDS = 1.0

# Below this percent-per-hour the gauge's rate is noise, so no
# runtime estimate is shown.


# Below this percent-per-hour the gauge's rate is noise, so no
# runtime estimate is shown.
BATTERY_RATE_FLOOR = 0.5

# Bring the STEMMA sensor up before anything else touches hardware.
# board.STEMMA_I2C() claims and manages I2C_POWER itself, and if
# another peripheral gets there first the bus comes up with no pull
# ups, which surfaces as a wiring error rather than a power one.


# Bring the STEMMA sensor up before anything else touches hardware.
# board.STEMMA_I2C() claims and manages I2C_POWER itself, and if
# another peripheral gets there first the bus comes up with no pull
# ups, which surfaces as a wiring error rather than a power one.
def open_air_sensor():
    """Bring up the STCC4 on the STEMMA QT port."""
    try:
        import adafruit_stcc4  # pylint: disable=import-outside-toplevel
    except ImportError as import_error:
        print("air sensor library missing:", import_error)
        return None

    try:
        i2c = board.STEMMA_I2C()
        found = adafruit_stcc4.STCC4(i2c)
        # Continuous rather than single shot. Single shot returns
        # "measurement not ready" and then I/O errors on this part;
        # continuous is the pattern proven on the Data Dispenser
        # build with the same sensor.
        found.continuous_measurement = True
        # The sensor needs a moment before its first conversion.
        time.sleep(AIR_SETTLE_SECONDS)
        # Prove it reads here, before the display, radio and pixel
        # come up. If this works and later reads do not, something
        # in the rest of the setup is disturbing the bus.
        try:
            print("air sensor up:", found.CO2, "ppm")
        except (RuntimeError, OSError) as first_error:
            print("air sensor up but first read failed:", first_error)
        return found
    except (ValueError, RuntimeError, OSError) as sensor_error:
        print("air sensor unavailable:", sensor_error)
        return None


sensor = open_air_sensor()


def open_battery():
    """Open the onboard MAX17048 fuel gauge."""
    try:
        import adafruit_max1704x  # pylint: disable=import-outside-toplevel

        gauge = adafruit_max1704x.MAX17048(board.STEMMA_I2C())
        print("battery gauge up")
        return gauge
    except (ImportError, ValueError, RuntimeError, OSError) as gauge_error:
        print("battery gauge unavailable:", gauge_error)
        return None


battery = open_battery()


def restart_air():
    """Put the sensor back into continuous measurement."""
    if sensor is None:
        return
    try:
        sensor.continuous_measurement = True
        time.sleep(AIR_SETTLE_SECONDS)
    except (RuntimeError, OSError) as restart_error:
        print("air restart failed:", restart_error)


def format_hours(hours):
    """Render a duration compactly: 45m, 6h, 2d."""
    if hours < 1:
        return "%dm" % max(round(hours * 60), 1)
    if hours < 48:
        return "%dh" % round(hours)
    return "%dd" % round(hours / 24)


def read_battery():
    """Charge state and estimated time remaining.

    charge_rate is percent per hour, signed. Dividing the remaining
    capacity by it gives a runtime estimate, which matters more than
    a percentage on a board meant to outlast a power cut.
    """
    if battery is None:
        return None
    try:
        percent = min(max(battery.cell_percent, 0), 100)
        rate = battery.charge_rate
    except (RuntimeError, OSError) as gauge_error:
        print("battery read failed:", gauge_error)
        return None

    label_text = "%d%%" % round(percent)

    # Below about half a percent per hour the estimate is noise.
    if rate > BATTERY_RATE_FLOOR:
        return "%s +%s" % (
            label_text,
            format_hours((100.0 - percent) / rate),
        )
    if rate < -BATTERY_RATE_FLOOR:
        return "%s %s" % (
            label_text,
            format_hours(percent / abs(rate)),
        )
    return label_text


def read_air():
    """Read the sensor. Returns a display string, or None.

    Occasional I2C errors are normal here, so retry a couple of times
    before giving up on this refresh cycle.
    """
    if sensor is None:
        return None

    for attempt in range(AIR_READ_ATTEMPTS):
        try:
            # Read CO2 first. The driver fetches the whole
            # measurement on this property, so asking for
            # temperature first reports "measurement not ready".
            co2 = sensor.CO2
            humidity = sensor.relative_humidity
            celsius = sensor.temperature
            degrees = celsius * 9 / 5 + 32 if USE_FAHRENHEIT else celsius
            unit = "F" if USE_FAHRENHEIT else "C"
            return "%d ppm   %d%s   %d%%" % (
                co2,
                round(degrees),
                unit,
                round(humidity),
            )
        except (RuntimeError, OSError) as sensor_error:
            if attempt == AIR_READ_ATTEMPTS - 1:
                print("air read failed:", sensor_error)
                return None
            # A power blip drops the sensor back to idle, where it
            # never produces a measurement and every read reports
            # "not ready". Put it back into continuous mode and
            # give it a conversion to catch up.
            restart_air()
            time.sleep(AIR_READ_RETRY_SECONDS)
    return None


# Nothing here is compute bound, so run the CPU slower.
