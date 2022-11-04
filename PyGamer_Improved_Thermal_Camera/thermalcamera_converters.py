# SPDX-FileCopyrightText: 2022 Jan Goolsbey for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`thermalcamera_converters`
================================================================================
Celsius-to-Fahrenheit and Fahrenheit-to-Celsius converter helpers.
"""


def celsius_to_fahrenheit(deg_c=None):
    """Convert C to F; round to 1 degree C"""
    return round(((9 / 5) * deg_c) + 32)


def fahrenheit_to_celsius(deg_f=None):
    """Convert F to C; round to 1 degree F"""
    return round((deg_f - 32) * (5 / 9))
