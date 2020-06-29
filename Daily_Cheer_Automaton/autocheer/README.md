# DAILY CHEER AUTOMATON 
## AUTOCHEER DEVICE

code by [Andy Doro](https://andydoro.com/)

using [Adafruit Feather](https://www.adafruit.com/feather) hardware\
will play an MP3 at a specified time each day


## Arduino Version

![Autocheer Arduino](https://github.com/andydoro/autocheer/blob/master/Arduino/assets/autocheer_arduino.jpg "Autocheer Arduino, photo by Andy Doro")


### HARDWARE
* any Feather board, e.g. [Feather M0 Basic Proto](https://www.adafruit.com/product/2772)

* [Adalogger FeatherWing](https://www.adafruit.com/product/2922) for PCF8523 RTC
  * & [CR1220 coin cell](https://www.adafruit.com/product/380)

* [Adafruit Music Maker FeatherWing](https://www.adafruit.com/product/3357) for 3.5mm (1/8") audio jack output
  * or [Music Maker FeatherWing w/ Amp](https://www.adafruit.com/product/3436) for speaker wire output

* [MicroSD card](https://www.adafruit.com/product/1294) FAT formatted with "cheer.mp3"

* [FeatherWing Tripler](https://www.adafruit.com/product/3417) 
  * or [Feather Stacking Headers](https://www.adafruit.com/product/2830) for a different form factor 


### SOFTWARE
#### LIBRARIES
* [VS1053](https://github.com/adafruit/Adafruit_VS1053_Library) for Music Maker
* [RCTlib](https://github.com/adafruit/RTClib) for RTC
* [DST_RTC](https://github.com/andydoro/DST_RTC) for automatic Daylight Saving Time adjustments

#### AUDIO FILE

cheer.mp3, place on FAT formatted SD card and insert into Music Maker\
suggestion: http://www.orangefreesounds.com/street-crowd-cheering-and-applauding/
