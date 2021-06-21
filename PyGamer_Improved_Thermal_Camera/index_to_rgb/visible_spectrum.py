# visible_spectrum.py
# 2021-05-27 version 1.2
# Copyright 2021 Cedar Grove Studios
# Spectral Index to Visible (Rainbow) Spectrum RGB Converter Helper
# Based on original 1996 Fortran code by Dan Bruton:
#   physics.sfasu.edu/astro/color/spectra.html

def index_to_rgb(index=0, gamma=0.5):
    """
    Converts a spectral index to rainbow (visible light wavelength)
    spectrum to an RGB value. Spectral index in range of 0.0 to 1.0
    (violet --> white). Gamma in range of 0.0 to 1.0 (1.0=linear),
    default 0.5 for color TFT displays.
    :return: Returns a 24-bit RGB value
    :rtype: integer
    """

    wl = (index * 320) + 380

    if wl < 440:
        intensity = 0.1 + (0.9 * (wl - 380) / (440 - 380))
        red = ((-1.0 * (wl - 440) / (440 - 380)) * intensity) ** gamma
        grn = 0.0
        blu = (1.0 * intensity) ** gamma
    if wl >= 440 and wl < 490:
        red = 0.0
        grn = (1.0 * (wl - 440) / (490 - 440)) ** gamma
        blu = 1.0 ** gamma
    if wl >= 490 and wl < 510:
        red = 0.0
        grn = 1.0 ** gamma
        blu = (-1.0 * (wl - 510) / (510 - 490)) ** gamma
    if wl >= 510 and wl < 580:
        red = (1.0 * (wl - 510) / (580 - 510)) ** gamma
        grn = 1.0 ** gamma
        blu = 0.0
    if wl >= 580 and wl < 645:
        red = 1.0 ** gamma
        grn = (-1.0 * (wl - 645) / (645 - 580)) ** gamma
        blu = 0.0
    if wl >= 645:
        intensity = 0.3 + (0.7 * (700 - wl) / (700 - 645))
        red = (1.0) ** gamma
        grn = (1.0 - intensity) ** gamma
        blu = (1.0 - intensity) ** gamma

    return (int(red * 255) << 16) + (int(grn * 255) << 8) + int(blu * 255)
