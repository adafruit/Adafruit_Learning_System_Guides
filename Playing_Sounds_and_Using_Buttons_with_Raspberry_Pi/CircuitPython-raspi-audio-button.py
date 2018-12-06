# This script requires a Raspberry Pi 2, 3 or Zero. Circuit Python must 
# be installed and it is strongly recommended that you use the latest 
# release of Raspbian.

import time
import board
import digitalio
import os

print("press a button!")

button1 = digitalio.DigitalInOut(board.D23)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.UP

button2 = digitalio.DigitalInOut(board.D24)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.UP

button3 = digitalio.DigitalInOut(board.D25)
button3.direction = digitalio.Direction.INPUT
button3.pull = digitalio.Pull.UP

while True:

    # omxplayer is a media player install by default with a full Raspbian installation.
    # It uses the Pi's GPU for playback and accepts output flags to control where to 
    # direct the audio. local is the headphone port, hdmi would be your monitor 
    # or both. It defaults to whichever device is selected for audio
    # in raspi-config or you can override with the follow syntax.
    # 
    # omxplayer -o local <file> 
    # omxplayer -o hdmi <file>
    # omxplayer -o both <file>
    #
    if not button1.value: 
        os.system('omxplayer temple-bell.mp3 &')

    if not button2.value: 
        os.system('omxplayer temple-bell-bigger.mp3 &')

    if not button3.value: 
        os.system('omxplayer temple-bell-huge.mp3 &')

    time.sleep(.25)
