# Code for Circuit Playground Express Rocket Lamp

# A fun lighting project using Circuit Playground Express and NeoPixels

# Written by Archie Roques for Adafruit Industries
# For full instructions see learn.adafruit.com/cpx-rocket-lamp !

# MIT License, see LICENSE for more info.

# import the libraries needed for this project
import time
import random
import board
import neopixel
import digitalio
import audioio

# enables the speaker for audio output
spkrenable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
spkrenable.direction = digitalio.Direction.OUTPUT
spkrenable.value = True

# define the onboard NeoPixel strip, and the externally connected one
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.2)
strip = neopixel.NeoPixel(board.A7, 30, brightness=.2)

# turn off the onboard pixels
pixels.fill((0, 0, 0))
pixels.show()

# set the rocket body LEDs to a pretty colour - we chose green!
# Colours are expressed in RGB format
# with each digit going up to 255.
# In this case we've used 0 red, 255 green and 150 blue.
strip.fill((0, 255, 150))
strip.show()

# set up the buttons to trigger the countdown
buttonA = digitalio.DigitalInOut(board.BUTTON_A)
buttonA.direction = digitalio.Direction.INPUT
buttonA.pull = digitalio.Pull.DOWN

buttonB = digitalio.DigitalInOut(board.BUTTON_B)
buttonB.direction = digitalio.Direction.INPUT
buttonB.pull = digitalio.Pull.DOWN

#this function will play the audio file
def play_audio():
    #open the file
    wave_file = open("liftoff.wav", "rb")
    #play the file
    with audioio.WaveFile(wave_file) as wave:
        with audioio.AudioOut(board.A0) as audio:
            audio.play(wave)
            #wait until audio is done
            while audio.playing:
                pass

# this function lights the CPX NeoPixels up with a blue fire animation
# (really quite hot) for about 1 second
def blue_fire(repeats):
    # fills them with a blue colour to start
    pixels.fill((40, 0, 200))
    pixels.show()
    # each repeat roughly corresponds to a second of running including processing time
    for _ in range(repeats):
        for _ in range(20):
            # pick a random pixel to fill
            j = random.randint(0, 9)
            # makes the pixel either lighter or darker to simulate firey goodness
            if random.random() > 0.5:
                pixels[j] = (40, 80, 250)
            else:
                pixels[j] = (20, 0, 200)
            pixels.show()
            # waits a bit so you can see it
            time.sleep(0.02)
            # returns pixel to original colour
            pixels[j] = (40, 0, 200)
            pixels.show()

# this function lights the CPX NeoPixels up with a white fire animation
# (super very hot) for about 1 second
def white_fire(repeats):
    # fills them with a white colour to start
    pixels.fill((100, 100, 100))
    pixels.show()
    # each repeat roughly corresponds to a second of running including processing time
    for _ in range(repeats):
        for _ in range(20):
            # pick a random pixel to fill
            j = random.randint(0, 9)
            # makes the pixel either lighter or darker to simulate firey goodness
            if random.random() > 0.5:
                pixels[j] = (140, 140, 100)
            else:
                pixels[j] = (100, 100, 140)
            pixels.show()
            # waits a bit so you can see it
            time.sleep(0.01)
            pixels[j] = (100, 100, 100)
            # returns pixel to original colour
            pixels.show()

# this function lights the CPX NeoPixels up with an orange fire animation
# (nice and toasty) for about 1 second
def orange_fire(repeats):
    # fills them with an orangy colour to start
    pixels.fill((200, 50, 0))
    pixels.show()
    # each repeat roughly corresponds to a second of running including processing time
    for _ in range(repeats):
        for _ in range(10):
            # pick a random pixel to fill
            j = random.randint(0, 9)
            # makes the pixel either lighter or darker to simulate firey goodness
            if random.random() > 0.5:
                pixels[j] = (200, 10, 0)
            else:
                pixels[j] = (200, 200, 0)
            pixels.show()
            # waits a bit so you can see it
            time.sleep(0.057)
            # returns pixel to original colour
            pixels[j] = (200, 50, 0)
            pixels.show()

# this function makes the body of the rocket light up in a countdown animation
def countdown(seconds):
    # turns off all the lights
    strip.fill((0, 0, 0))
    strip.show()
    # we pass the amount of seconds into the function at the start so the countdown
    # runs for the right amount of time 15 seconds is the max since we only have 30
    # NeoPixels in our strip, and the countdown runs on both sides. 30/2 = 15 seconds
    for i in range(seconds):
        # lights the top pixels, then the next ones down, etc etc all the way to the bottom
        strip[seconds-(i+1)] = (200, 200, 200)
        strip[30-(seconds-i)] = (200, 200, 200)
        strip.show()
        # we use the white fire animation as a timer since it takes about a second to run
        white_fire(1)
    # when the countdown's done, flash all the pixels and play a sound to celebrate take off!
    play_audio()
    for i in range(3):
        strip.fill((200, 200, 200))
        strip.show()
        time.sleep(0.1)
        strip.fill((0, 0, 0))
        strip.show()
        time.sleep(0.1)
    # return the strip to the original colour
    strip.fill((0, 200, 100))
    strip.show()

# this loop of code runs all the time and controls when all the other functions happen
while True:
    # if button A is pressed
    if buttonA.value:
        #run the ten second countdown procedure
        countdown(10)
    elif buttonB.value:
        # run the blue fire for a bit and then trigger the final countdown
        # this sequence is about a minute long
        blue_fire(45)
        countdown(10)
    # if the button isn't pressed, loop the normal animation sequence of orange fire
    else:
        orange_fire(1)
