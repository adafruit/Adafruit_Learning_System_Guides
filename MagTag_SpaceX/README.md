## Adafruit Learning System Guide - A SpaceX next launch display with Adafruit MagTag

Code and Guide by Anne Barela

MIT License

(C) 2020 Adafruit Industries, please attribute use of code

This code is for an Adafruit Learning System guide on displaying next launch data for SpaceX
on the epaper display of the Adafruit MagTag. All internet connectivity is done by the
ESP32-S2 processor on the MagTag.

Data from https://api.spacexdata.com/v4/launches/next

Documentation for this API is at https://github.com/r-spacex/SpaceX-API. As this is a
non-SpaceX data source, accuracy and availability could be limited.

Note: The Lato-Bold-ltd-25.bdf font file only has the characters used in "Next SpaceX Launch" 
to save space on the MagTag flash drive. See the guide https://learn.adafruit.com/custom-fonts-for-pyportal-circuitpython-display/overview 
for building your own custom fonts for CircuitPython use on displays.
