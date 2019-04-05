# All_Seeing_Skull

'Uncanny eyes' for Adafruit 1.5" OLED (product #1431) or 1.44" TFT LCD (#2088).  Works on PJRC Teensy 3.x and on Adafruit M0 and M4 boards (Feather, Metro, etc.), and HalloWing M0 Express.  This code uses features specific to these boards and WILL NOT work on normal Arduino or other boards!

This version is configured for the HalloWing. https://learn.adafruit.com/hallowing-all-seeing-skull/overview

Original project How-to guide with parts list and 3D models is here:
https://learn.adafruit.com/animated-electronic-eyes-using-teensy-3-1/overview

Teensy 3.x w/OLED screens: use 72 MHz board speed -- 96 MHz requires throttling back SPI bitrate and actually runs slower!

Directory contains Arduino sketch for Adafruit HalloWing M0. 'graphics' subfolder has various eye designs, as #include-able header files.
