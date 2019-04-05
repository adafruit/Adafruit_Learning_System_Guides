Welcome to CircuitPython!
#############################

Visit the pIRkey M0 product page here for more info: 
                        https://adafruit.com/product/3364


#############################

The pIRkey has a very tiny disk drive so we have disabled Mac OS X indexing
which could take up that valuable space. 

So *please* do not remove the empty .fseventsd/no_log, .metadata_never_index 
or .Trashes files! 

#############################

The pre-loaded demo files show off what your pIRkey M0 can do with 
CircuitPython:
  * The default 'main.py' will read infrared pulses and print them out
to the serial console/REPL
  * "NEC print example.py" will decode common 'NEC protocol' remotes and
print out the 4-digit code to the console
  * "NEC keyboard example.py" will read NEC protocol remotes and show how 
to trigger keyboard commands based on what codes are received. This example
is designed to be used with our simple low cost remote 
                        https://www.adafruit.com/product/389
but is easily adapted  to other NEC remotes

For more details on how to use and customize the pIRkey & CircuitPython, visit 
https://adafruit.com/product/3364 and check out all the tutorials we have!

#############################
CircuitPython Quick Start:

Changing the code is as easy as editing main.py in your favorite text editor. 

Our recommended editor is Mu, which is great for simple projects, and comes
with a built in REPL serial viewer! It is available for Mac, Windows & Linux
https://learn.adafruit.com/welcome-to-circuitpython/installing-mu-editor

After the file is saved, CircuitPython will automatically reload the latest 
code. Try this out by renaming 'main.py' to 'my backup.py' and then renaming 
'NEC print example.py' to main.py to load the different example sketch.
These sketches work best when you are also connected to the serial port / REPL

Connecting to the serial port will give you access to sensor information, 
better error messages and an interactive CircuitPython (known as the REPL). 
On Windows we recommend Mu, Tera Term or PuTTY. 
On Mac OSX and Linux, use Mu or 'screen' can be used from a terminal.
