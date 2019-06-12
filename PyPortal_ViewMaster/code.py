import os
import board
import busio
import digitalio
import storage
import adafruit_sdcard
from adafruit_slideshow import PlayBackOrder, SlideShow, PlayBackDirection

# Default location to look is in internal memory
IMAGE_DIRECTORY = "/images"

switch = digitalio.DigitalInOut(board.D3)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.SD_CS)
try:
    sdcard = adafruit_sdcard.SDCard(spi, cs)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    IMAGE_DIRECTORY = "/sd/images"
except OSError as error:
    print("No SD card, will only look on internal memory")

def print_directory(path, tabs=0):
    for file in os.listdir(path):
        stats = os.stat(path + "/" + file)
        filesize = stats[6]
        isdir = stats[0] & 0x4000

        if filesize < 1000:
            sizestr = str(filesize) + " by"
        elif filesize < 1000000:
            sizestr = "%0.1f KB" % (filesize / 1000)
        else:
            sizestr = "%0.1f MB" % (filesize / 1000000)

        prettyprintname = ""
        for _ in range(tabs):
            prettyprintname += "   "
        prettyprintname += file
        if isdir:
            prettyprintname += "/"
        print('{0:<20} Size: {1:>6}'.format(prettyprintname, sizestr))

        # recursively print directory contents
        if isdir:
            print_directory(path + "/" + file, tabs + 1)

try:
    print_directory(IMAGE_DIRECTORY)
except OSError as error:
    raise Exception("No images found on flash or SD Card")

# Create the slideshow object that plays through once alphabetically.
slideshow = SlideShow(board.DISPLAY, None, folder=IMAGE_DIRECTORY, loop=True,
                      order=PlayBackOrder.ALPHABETICAL, dwell=0)
while True:
    if not switch.value:
        print("Click!")
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()
        while not switch.value:
            pass
