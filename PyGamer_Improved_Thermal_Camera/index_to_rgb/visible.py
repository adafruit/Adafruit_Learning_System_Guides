# SPDX-FileCopyrightText: Copyright (c) 2022 JG for Cedar Grove Maker Studios
#
# SPDX-License-Identifier: MIT
"""
`cedargrove_rgb_spectrumtools.visible`
================================================================================

A Spectral Index to Visible (Rainbow) Spectrum RGB Converter Helper

Based on original 1996 Fortran code by Dan Bruton:
physics.sfasu.edu/astro/color/spectra.html

* Author(s): JG

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/CedarGroveStudios/CircuitPython_RGB_SpectrumTools.git"


def index_to_rgb(index=0, gamma=0.5):
    """
    Converts a spectral index to rainbow (visible light wavelength)
    spectrum to an RGB value. Spectral index in range of 0.0 to 1.0
    (violet --> white). Gamma in range of 0.0 to 1.0 (1.0=linear),
    default 0.5 for color TFT displays.

    :param float index: The normalized index value, range 0 to 1.0. Defaults to 0.
    :param float gamma: The gamma color perception value. Defaults to 0.5.

    :return: Returns a 24-bit RGB value
    :rtype: integer
    """

    wavelength = (index * 320) + 380

    if wavelength < 440:
        intensity = 0.1 + (0.9 * (wavelength - 380) / (440 - 380))
        red = ((-1.0 * (wavelength - 440) / (440 - 380)) * intensity) ** gamma
        grn = 0.0
        blu = (1.0 * intensity) ** gamma
    if 440 <= wavelength < 490:
        red = 0.0
        grn = (1.0 * (wavelength - 440) / (490 - 440)) ** gamma
        blu = 1.0**gamma
    if 490 <= wavelength < 510:
        red = 0.0
        grn = 1.0**gamma
        blu = (-1.0 * (wavelength - 510) / (510 - 490)) ** gamma
    if 510 <= wavelength < 580:
        red = (1.0 * (wavelength - 510) / (580 - 510)) ** gamma
        grn = 1.0**gamma
        blu = 0.0
    if 580 <= wavelength < 645:
        red = 1.0**gamma
        grn = (-1.0 * (wavelength - 645) / (645 - 580)) ** gamma
        blu = 0.0
    if wavelength >= 645:
        intensity = 0.3 + (0.7 * (700 - wavelength) / (700 - 645))
        red = (1.0) ** gamma
        grn = (1.0 - intensity) ** gamma
        blu = (1.0 - intensity) ** gamma

    return (int(red * 255) << 16) + (int(grn * 255) << 8) + int(blu * 255)
