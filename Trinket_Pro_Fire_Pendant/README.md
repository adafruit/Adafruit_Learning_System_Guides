## Animated Flame Pendant Tutorial Code

The files in this repository accompanied an [Adafruit Learning System](https://learn.adafruit.com) tutorial 
https://learn.adafruit.com/animated-flame-pendant/

Fire pendant jewelry for Adafruit Pro Trinket + Charlieplex LED array. Loops a canned animation sequence on the display.

Arduino sketch is comprised of 'FirePendant.ino' and 'data.h' -- latter contains animation frames packed into PROGMEM array holding bounding rectangle + column-major pixel data for each frame (consumes most of the flash space on the ATmega328).

The sketch is very specifically optimized for the Pro Trinket and won’t likely work on other boards.

The 'frames.zip' archive contains the animation source PNG images and a python script, convert.py, which processes all the source images into the required data.h  format. The PNG images were generated via Adobe Premiere and Photoshop from Free Stock Video by user 'dietolog' on Videezy.com.

------------------

This code was formerly at https://github.com/adafruit/FirePendant - this has now been archived.

If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.

Please consider buying your parts at [Adafruit.com](https://www.adafruit.com) to support open source code.
