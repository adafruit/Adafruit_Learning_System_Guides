# EZ Make Oven

The EZ Make Oven is an easy to build reflow oven utilizing a PyPortal as
the controller. It also uses the Adafruit MCP9600 thermocouple amplifier, a thermocouple and the IoT Power Relay from Digital Loggers.

A standard, non-digital toaster oven is needed for this project, which can be purchased online or at your nearest appliance store. It should be small (4 slice capacity), at least 1100 watts and a maximum temperature of 450F / 230C or better.

Follow the Adafruit learn guide here: https://learn.adafruit.com/ez-make-oven

Run **codecalibrate.py** first to determine calibration settings for your toaster oven. You will need to re-run this if you switch toaster ovens or update the EZ Make Oven software. The calibration values displayed will need to be manually entered into the **config.json file**. This file also contains the I2C address of your MCP9600 breakout (in decimal) and the name of the solder profile to use. Available solder profiles can be found in the profiles folder. You will need to rename this file to **code.py** in order to run it.

**code.py** is the EZ Make Oven code that will run the program when the board boots up.

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from [Adafruit](https://www.adafruit.com)!
 
MIT license, code and guide written by Dan Cogliano

All text above, and the splash screen below must be included in any redistribution

-----------------------
If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.
