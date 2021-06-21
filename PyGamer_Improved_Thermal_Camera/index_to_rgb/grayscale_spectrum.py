# grayscale_spectrum.py
# 2021-05-19 version 1.1
# Copyright 2021 Cedar Grove Studios
# Spectral Index to Grayscale RGB Converter Helper

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

def index_to_rgb(index=0, gamma=0.8):
    """
    Converts a spectral index to a grayscale RGB value. Spectral index in
    range of 0.0 to 1.0. Gamma in range of 0.0 to 1.0 (1.0=linear),
    default 0.8 for color TFT displays.
    :return: Returns a 24-bit RGB value
    :rtype: integer
    """

    red = grn = blu = map_range(index, 0, 1.0, 0.1, 1.0) ** gamma

    return (int(red * 255) << 16) + (int(grn * 255) << 8) + int(blu * 255)
