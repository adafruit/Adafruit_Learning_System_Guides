import time
import adafruit_sdcard
import microcontroller
import board
import busio
import digitalio
import storage

# Setup the little red LED on D13
led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

# Connect to the card and mount the filesystem.
spi = busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO)
cs = digitalio.DigitalInOut(board.SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

print("Logging temperature to SD card")
# We're going to append to the file
while True:
    # Open file for append
    with open("/sd/temperature.txt", "a") as file:
        led.value = True  # Turn on LED to indicate we're writing to the file
        temperature = microcontroller.cpu.temperature
        print("Temperature = %0.1f" % temperature)
        file.write("%0.1f\n" % temperature)
        led.value = False  # Turn off LED to indicate we're done
    # File is saved
    time.sleep(1)
