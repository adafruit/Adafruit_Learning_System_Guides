## TrinketReactCounter
Trinket sketch to build a react or 'like' button that counts button presses and
displays them on a 7-segment or 14-segment LED backpack.

The files in this repository accompany an [Adafruit Learning System](https://learn.adafruit.com) tutorial 
https://learn.adafruit.com/trinket-react-counter

This code was formerly at https://github.com/adafruit/TrinketReactCounter - this has now been archived.

All code MIT License, please keep attribution to Adafruit Industries

If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.

Please consider buying your parts at [Adafruit.com](https://www.adafruit.com) to support open source code.

## Hardware

You need the following hardware to build this device:

*   [Adafruit Trinket](https://www.adafruit.com/trinket) (either the [5V Trinket](https://www.adafruit.com/products/1501) or [3.3V Trinket](https://www.adafruit.com/products/1500) will work)
*   [Adafruit 7-segment LED Backpack Display](https://www.adafruit.com/product/879) or [Adafruit 14-segment quad alphanumeric LED Backpack Display](https://www.adafruit.com/product/1911)
*   [Momentary push button](https://www.adafruit.com/products/1009)

Connect the hardware as follows:

*   Trinket 3V/5V power to 7-segment power (+) and one side of the button.  If
    using the 14-segment display connect 3V/5V power to the additional power (+) pin.
*   Trinket #0 to 7-segment SDA (D).
*   Trinket #1 to opposite side of button.
*   Trinket #2 to 7-segment SCL (C).
*   Trinket GND/ground to 7-segment ground (-).

## Usage

Load the right sketch in Arduino depending on your hardware.  The 7-segment display
should use the TrinketReactCounter_7segment sketch, and the 14-segment quad alphanumeric
display should use the TrinketReactCounter_14segment sketch.  Make sure the following
libraries are installed too (using the library manager or a manual install):

*   [Adafruit GFX Library](https://github.com/adafruit/Adafruit-GFX-Library)
*   [Adafruit LED Backpack](https://github.com/adafruit/Adafruit_LED_Backpack)

For your first use uncomment this line near the top of the sketch:

    // Uncomment the line below to reset the counter value in EEPROM to zero.
    // After uncommenting reload the sketch and during the setup the counter
    // will be reset.  Then comment the line again and reload to start again
    // (if you don't comment it out then every time the board powers on it
    // will reset back to zero!).
    //#define RESET_COUNT

So that it looks like the following:

    // Uncomment the line below to reset the counter value in EEPROM to zero.
    // After uncommenting reload the sketch and during the setup the counter
    // will be reset.  Then comment the line again and reload to start again
    // (if you don't comment it out then every time the board powers on it
    // will reset back to zero!).
    #define RESET_COUNT  

This will cause the count stored in EEPROM to be reset to zero during the setup.

Save and upload the modified sketch to the Trinket.  You should see the display print 0.
If you press and release the button the count should increment by one.

Now back in the sketch code comment out the RESET_COUNT line again so it looks
like its original value:

    // Uncomment the line below to reset the counter value in EEPROM to zero.
    // After uncommenting reload the sketch and during the setup the counter
    // will be reset.  Then comment the line again and reload to start again
    // (if you don't comment it out then every time the board powers on it
    // will reset back to zero!).
    //#define RESET_COUNT

Upload the sketch to the Trinket again.  You should see the display print the
previous count value, and again pressing the button will increment the count.
Now if you power down and then power back up the Trinket it should load the
last count value after the bootloader runs (the red light stops pulsing).

You can follow the above steps to uncomment the RESET_COUNT value any time you
want to reset the count value back to zero.
