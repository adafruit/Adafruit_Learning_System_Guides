# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Duplo Color Boombox"""

import board
import sdcardio
import storage
import audiobusio
import audiomixer
import audiomp3
from digitalio import DigitalInOut, Direction
from adafruit_as7341 import AS7341
from adafruit_seesaw import digitalio, neopixel, rotaryio, seesaw

#Power Setup
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

#SD Card setup

spi = board.SPI()
cs = board.D10
sdcard = sdcardio.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd", readonly=True)

#Audio
mp3 = audiomp3.MP3Decoder(open("/sd/blue.mp3", "rb"))

i2s = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=mp3.sample_rate, channel_count=1,
                         bits_per_sample=mp3.bits_per_sample)
i2s.play(mixer)
mixer.voice[0].level = 0.5

#Color Sensor
i2c = board.STEMMA_I2C()
sensor = AS7341(i2c)
sensor.led_current = 4  # increments in units of 4
sensor.led = False

brick_dictionary = [
    {'song': "/sd/blue.mp3", 'value': (1619, 13852, 19215, 18562, 12912, 8818, 9512, 5440),
     'color': ((0, 255, 255))},
    {'song': "/sd/orange.mp3", 'value': (2517, 3983, 5661, 6864, 16857, 39049, 55151, 35696),
     'color': ((255, 60, 0))},
    {'song': "/sd/coral.mp3", 'value': (3004, 6712, 7499, 7160, 13858, 46007, 65535, 39278),
     'color': ((250, 50, 50))},
    {'song': "/sd/purple.mp3", 'value': (2562, 20704, 19222, 15806, 16624, 18399, 27316, 22525),
     'color': ((125, 0, 255))},
    {'song': "/sd/red.mp3", 'value': (1453, 2629, 4050, 4656, 5527, 13403, 31096, 21368),
     'color': ((255, 0, 0))},
    {'song': "/sd/yellow.mp3", 'value': (3051, 4446, 8633, 17412, 37450, 48224, 56249, 34726),
     'color': ((255, 150, 0))},
    {'song': "/sd/butter.mp3", 'value': (4102, 8631, 13692, 29000, 58147, 63230, 65535, 43143),
     'color': ((255, 255, 0))},
    {'song': "/sd/green.mp3", 'value': (1383, 2767, 5850, 12964, 22118, 16304, 12669, 7008),
     'color': ((120, 255, 0))},
    {'song': "/sd/lime.mp3", 'value': (3017, 8109, 17948, 36761, 48754, 38009, 31671, 19457),
     'color': ((150, 255, 0))},
    {'song': "/sd/lightblue.mp3", 'value': (4188, 29507, 42326, 53214, 54067, 37512, 34129, 23544),
     'color':((100, 250, 255))},
    {'song': "/sd/white.mp3", 'value': (5246, 27506, 33883, 44702, 62766, 64254, 65535, 48334),
     'color':((255, 255, 255))},
    ]

def find_closest_brick(reading, dictionary, max_distance=50000):
    """
    Find the brick with the closest matching sensor values.

    Args:
        new_reading: Tuple of 8 sensor values
        brick_dictionary: List of brick dictionaries
        max_distance: Maximum distance to consider a valid match

    Returns:
        Tuple of (matched_brick, distance) or (None, distance) if no good match
    """
    best_match = None
    best_distance = float('inf')

    for brick in dictionary:
        # Calculate total distance (sum of absolute differences)
        distance = sum(abs(v1 - v2) for v1, v2 in zip(reading, brick['value']))

        if distance < best_distance:
            best_distance = distance
            best_match = brick

    # Only return a match if it's close enough
    if best_distance > max_distance:
        return None

    return best_match

#Rotary STEMMA I2C
seesaw = seesaw.Seesaw(i2c, 0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
switch = digitalio.DigitalIO(seesaw, 24)
switch_state = False

pixel = neopixel.NeoPixel(seesaw, 6, 1)
pixel.brightness = 1
pixel.fill((0, 0, 0))

last_position = -1
volume = 0.5 # volume
play = False
play_state = False

mp3 = audiomp3.MP3Decoder(open("/sd/boot.mp3", "rb"))
mixer.voice[0].play(mp3, loop=False)

while True:

    # make clockwise rotation positive
    position = -encoder.position

    if position != last_position:
        if position > last_position:
            #decrease volume
            volume = volume - 0.05
            volume = max(volume, 0)
        else:
            #increase volume
            volume = volume + 0.05
            volume = min(volume, 1)
        # set the audio volume
        mixer.voice[0].level = volume
        print(volume)
        last_position = position

    if not switch.value and not switch_state:
        print("Button pressed")
        switch_state = True
        if not play:
            sensor.led = True
            sensor_color = sensor.all_channels
            matched_brick = find_closest_brick(sensor_color, brick_dictionary)
            print(sensor_color)
            if matched_brick is not None:
                print(matched_brick['song'])
                mp3 = audiomp3.MP3Decoder(open(matched_brick['song'], "rb"))
                pixel.fill(matched_brick['color'])
                play = True
                mixer.voice[0].play(mp3, loop=False)
                play_state = True
            else:
                print("insert brick")
                mp3 = audiomp3.MP3Decoder(open("/sd/uhoh.mp3", "rb"))
                mixer.voice[0].play(mp3, loop=False)
        else:
            if play_state:
                i2s.pause()
                play_state = False
            else:
                i2s.resume()
                play_state = True

    if switch.value and switch_state:
        sensor.led = False
        switch_state = False
        print("Button released")

    if not mixer.playing:
        play_state = False
        play = False
        pixel.fill((0,0,0))
