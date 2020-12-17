# Shake Audio Lamp
# for Adafruit Circuit Playground express
# with CircuitPython
import time
import audioio
import audiocore
import board

from adafruit_circuitplayground.express import cpx

# External Audio Stuff
audio = audioio.AudioOut(board.A0)  # Speaker
wave_file = None

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    :param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    :param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    global wave_file  # pylint: disable=global-statement
    print("playing", name)
    if wave_file:
        wave_file.close()
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb') # using wave files from sounds folder
        wave = audiocore.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except OSError:
        pass # we'll just skip playing then

# flash neopixel effects
def party_flash(duration):
    cpx.pixels.fill((255, 255, 255))
    cpx.pixels.show()
    time.sleep(duration)
    cpx.pixels.fill((255, 0, 0))
    cpx.pixels.show()
    time.sleep(duration)

def led_flash(duration):
    cpx.pixels.fill((255, 255, 255))
    cpx.pixels.show()
    time.sleep(duration)
    cpx.pixels.fill((0, 0, 0))
    cpx.pixels.show()
    time.sleep(duration)

# make a counter variable
counter = 0

while True:
    # Listen for shakes
    if cpx.shake(shake_threshold=15): # adjust sensitivity - low number is more sensitive
        print("Shake detected!") # Let us know there was a shake
        counter = counter + 1 # Start a counter
        if counter == 2: # On second shake
            play_wav("awe-a") # play audio
            for _ in range(3): # loop x times
                party_flash(0.4) # neopixel flash
        elif counter == 3: # On third shake
            play_wav("awe-b")
            for _ in range(3): # loop x times
                party_flash(0.4) # neopixel flash
        elif counter == 4: # On fourth shake
            play_wav("awe-c")
            for _ in range(3): # loop x times
                party_flash(0.4) # neopixel flash
        elif counter == 5: # on fifth shake
            counter = 0 # Reset the counter back to zero
            play_wav("untz") #play audio
            for _ in range(3): # loop x times
                led_flash(.18) # faster pixel flash
            cpx.pixels.fill((255,255,255)) # solid pixel
            time.sleep(1) # light it for one second
        else: # On first shake
            play_wav("haha") # play audio
            cpx.pixels.fill((255,255,255)) # white color
            time.sleep(1) # for one second
    else: # When there's no shakyness to be had
        cpx.pixels.fill((0, 0, 0)) # keep pixels off when not shaking
