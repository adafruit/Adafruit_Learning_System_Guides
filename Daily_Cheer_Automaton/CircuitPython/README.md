# DAILY CHEER AUTOMATON 
## AUTOCHEER DEVICE

code by [Andy Doro](https://andydoro.com/)

using [Adafruit Feather](https://www.adafruit.com/feather) hardware\
will play an MP3 at a specified time each day


## CircuitPython Version

![Autocheer CircuitPython](https://github.com/andydoro/autocheer/blob/master/CircuitPython/assets/autocheer_circpy.jpg "Autocheer CircuitPython, photo by Dano Wall")


### HARDWARE

* [Feather M4 Express](https://www.adafruit.com/product/3857) is need because it's fast enough to play back MP3 files

* [Adalogger FeatherWing](https://www.adafruit.com/product/2922) for PCF8523 RTC
  * & [CR1220 coin cell](https://www.adafruit.com/product/380)

* [MicroSD card](https://www.adafruit.com/product/1294) FAT formatted with "cheer.mp3"

* [FeatherWing Doubler](https://www.adafruit.com/product/2890) 
  * or [Feather Stacking Headers](https://www.adafruit.com/product/2830) for a different form factor 

* [Headphone Jack](https://www.adafruit.com/product/1699)


### SOFTWARE

requires M4 (ATSAMD51 32-bit Cortex M4 core) or higher and\
CircuitPython version 5.3.0+

#### LIBRARIES

from [library bundle version 5.x](https://circuitpython.org/libraries):

* adafruit_bus_device folder
* adafruit_register folder
* adafruit_pcf8523.mpy
* adafruit_sdcard.mpy

#### AUDIO FILE

cheer.mp3, place on FAT formatted SD card and insert into Music Maker\
suggestion: http://www.orangefreesounds.com/street-crowd-cheering-and-applauding/
