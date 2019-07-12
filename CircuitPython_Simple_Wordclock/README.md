## Adafruit Learning System tutorial  - Simple Vertical Wordclock

Make a timekeeping vertical wordclock with Adafruit Feather M4, a RTC FeatherWing, and CircuitPython.

Follow the Adafruit learn guide here: https://learn.adafruit.com/vertical-wordclock/ !

**set_clock.py** is a run once program to set the time. You will need to edit the code as seen in the comments for the exact date and time (without daylight savings time, please). If you move time zones, you will have to reset the time using this code.

**code.py** is the code that will run to display the time. It reads the time previously set. A backup battery in the RTC FeatherWing keeps the time even when power is removed.

Use the slide switch added to the Adafruit Feather M4 to add one hour to the time for daylight savings.

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from [Adafruit](https://www.adafruit.com)!
 
MIT license, designed and guide written by Dano Wall, code by Mike Barela

All text above, and the splash screen below must be included in any redistribution

-----------------------
If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.
