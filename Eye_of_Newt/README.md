# Teensy3.1_Eyes

Adapted from the 'Uncanny eyes' project for PJRC Teensy 3.1 with Adafruit 1.5" OLED (product #1431) or 1.44" TFT LCD (#2088). This uses Teensy-3.1-specific features and WILL NOT work on normal Arduino or other boards!  Use 72 MHz (Optimized) board speed -- OLED does not work at 96 MHz.

How-to guide with parts list and 3D models is here:
https://learn.adafruit.com/eye-of-newt/introduction

Directory 'uncannyEyes_newt' contains Arduino sketch for PJRC Teensy 3.1. 'uncannyEyes_newt.ino' is the code, 'newtEye.h' is a set of arrays containing eye bitmaps, etc.

Folder 'convert' contains Python sketch for generating eyeData.h. Requires Python Imaging Library. Example images are also in this directory.
