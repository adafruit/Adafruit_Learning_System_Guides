## Adafruit Learning System - M4_Eyes for the MONSTER M4SK

Make blinking, moving eyes on an Adafruit Monster M4sk microcontroller and display board.

This code is used for displaying realistic eyes on the Adafruit [Monster M4sk](https://www.adafruit.com/product/4343) board.

See the main [Adafruit Learning System tutorial on the Monster M4sk here](https://learn.adafruit.com/adafruit-monster-m4sk-eyes/overview).

Note the code is such that user code may be run with linitations - see user*.cpp. This method is used for a number of Adafruit Learning System guides to provide various functionality. As this is a rough form of task switching, not all actions will be compatible. There be dragons here and there is no guarantee of compatibility with all types of actions and hardware.

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from [Adafruit](https://www.adafruit.com)!
 
MIT license, hardware by Limor "Ladyada" Fried, eye code by Phil Burgess

All text above must be included in any redistribution

-----------------------
If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.

-----------------------
### The sequence
This feature allows the user to define a list of eye models that can be shown in a sequence.

A file called **sequence.eye** can be placed on the root directory. If the **A** button is held down during reset AND the
sequence file exists, then it will be loaded and the eye switching sequence will begin immediately. The contents of the file is as follows:

```JSON
{  
   "eyes":[  
      { "/hazel": 30},  
      { "/fish_eyes": 90},  
      { "/demon": 240 }  
   ]  
}  

```

There is currently a limit on the number of models, it is defined by the **MAX_SEQUENCE_COUNT** variable and is arbitrarily set to **10** as of this writing. The seconds field is currently defined as a **uint8_t** and is in seconds so the maximum timeout is currently **255** seconds. This should be an easy change to increase the values at the expense of a bit more memory usage.

The code will always start the sequence at index 0 in the eyes array, in the above example that would be the hazel eye model which will display for 30 seconds. The next model will be the fish eyes which will display for 90 seconds, followed by the demon model which displays for 240 seconds, followed by the hazel model for 30 seconds and so on.

The code expects to find all the files needed to define the eye model in the directory specified, such as the config.eye, iris, sclera, eyelid shapes, etc.

Unfortunately the eye models cannot be easily swapped in run time given the complexity of the operations being performed to draw them and the memory optimizations required. What the sequence code does is take advantage of the watchdog timer to monitor the timeout for each model and rebooting the board to flush the memory and load the next model in the sequence. To achieve this the code writes back to the sequence file and stores the index of the model that should be loaded on next reboot. On reboot, the sequence logic recognizes that the reset was prompted by the watchdog timer and thus tries to load the contents of the sequence file again. This time it searches the file for the index of the model to load that was stored before reboot and uses it to load the next model. The cycle repeats itself indefinitely. To exit the sequence logic simply reset the board manually without holding down the **A** button. The functionality will return to normal operation. The only downside is that the config2.eye file will not load if it exists and a sequence.eye file also exists as the code will pick the latter in that case.

It is not perfect but demonstrates that it is possible to switch models "automatically". It should serve as a guide to enable a mechanism that switches out the eye models on an event instead of a timeout. That is left for a later time :).
