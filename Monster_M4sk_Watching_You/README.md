# Adafruit Learning System tutorial - Monster M4sk Is Watching You

Make a person responsive set of eyes.

Follow the Adafruit learn guide here: https://learn.adafruit.com/monster-m4sk-is-watching-you/

The source code is the same as the [M4_Eyes](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/master/M4_Eyes) code
with the following changes:

In **user.cpp**, change the first line from #if 1 to #if 0. In **user_watch.cpp**, do the opposite: change the first line from #if 0 to #if 1. This ensures that exactly one version of the **user_setup()** and **user_loop()** functions is defined.

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from [Adafruit](https://www.adafruit.com)!
 
MIT license, project and sensor code by Timothy Weber. M4_Eyes by Phil Burgess for Adafruit Industries

All text above, and the splash screen below must be included in any redistribution

-----------------------
If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.
