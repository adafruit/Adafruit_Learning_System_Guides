# thermal_cam_converters.py

def celsius_to_fahrenheit(deg_c=None):  # convert C to F; round to 1 degree C
    return round(((9 / 5) * deg_c) + 32)

def fahrenheit_to_celsius(deg_f=None):  # convert F to C; round to 1 degree F
    return round((deg_f - 32) * (5 / 9))
