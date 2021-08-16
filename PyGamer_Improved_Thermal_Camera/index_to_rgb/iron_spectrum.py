# iron_spectrum.py
# 2021-05-27 version 1.2
# Copyright 2021 Cedar Grove Studios
# Temperature Index to Iron Pseudocolor Spectrum RGB Converter Helper

def map_range(x, in_min, in_max, out_min, out_max):
    """
    Maps and constrains an input value from one range of values to another.
    (from adafruit_simpleio)
    :return: Returns value mapped to new range
    :rtype: float
    """
    in_range = in_max - in_min
    in_delta = x - in_min
    if in_range != 0:
        mapped = in_delta / in_range
    elif in_delta != 0:
        mapped = in_delta
    else:
        mapped = 0.5
    mapped *= out_max - out_min
    mapped += out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)

def index_to_rgb(index=0, gamma=0.5):
    """
    Converts a temperature index to an iron thermographic pseudocolor spectrum
    RGB value. Temperature index in range of 0.0 to 1.0. Gamma in range of
    0.0 to 1.0 (1.0=linear), default 0.5 for color TFT displays.
    :return: Returns a 24-bit RGB value
    :rtype: integer
    """

    band = index * 600  # an arbitrary spectrum band index; 0 to 600

    if band < 70:  # dark gray to blue
        red = 0.1
        grn = 0.1
        blu = (0.2 + (0.8 * map_range(band, 0, 70, 0.0, 1.0))) ** gamma
    if band >= 70 and band < 200:  # blue to violet
        red = map_range(band, 70, 200, 0.0, 0.6) ** gamma
        grn = 0.0
        blu = 1.0 ** gamma
    if band >= 200 and band < 300:  # violet to red
        red = map_range(band, 200, 300, 0.6, 1.0) ** gamma
        grn = 0.0
        blu = map_range(band, 200, 300, 1.0, 0.0) ** gamma
    if band >= 300 and band < 400:   # red to orange
        red = 1.0 ** gamma
        grn = map_range(band, 300, 400, 0.0, 0.5) ** gamma
        blu = 0.0
    if band >= 400 and band < 500:  # orange to yellow
        red = 1.0 ** gamma
        grn = map_range(band, 400, 500, 0.5, 1.0) ** gamma
        blu = 0.0
    if band >= 500:  # yellow to white
        red = 1.0 ** gamma
        grn = 1.0 ** gamma
        blu = map_range(band, 500, 580, 0.0, 1.0) ** gamma

    return (int(red * 255) << 16) + (int(grn * 255) << 8) + int(blu * 255)
