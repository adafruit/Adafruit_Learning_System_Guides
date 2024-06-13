# SPDX-FileCopyrightText: 2022 John Park and Tod Kurt for Adafruit Industries
# SPDX-License-Identifier: MIT
'''Walkmp3rson digital cassette tape player (ok fine it's just SD cards)'''

import time
import os
import board
import busio
import sdcardio
import storage
import audiomixer
import audiobusio
import audiomp3
from adafruit_neokey.neokey1x4 import NeoKey1x4
from adafruit_seesaw import seesaw, rotaryio
import displayio
import fourwire
import terminalio
from adafruit_display_text import label
from adafruit_st7789 import ST7789
from adafruit_progressbar.progressbar import HorizontalProgressBar
from adafruit_progressbar.verticalprogressbar import VerticalProgressBar


displayio.release_displays()

# SPI for TFT display, and SD Card reader on TFT display
spi = board.SPI()
# display setup
tft_cs = board.D6
tft_dc = board.D9
tft_reset = board.D12
display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_reset)
display = ST7789(display_bus, width=320, height=240, rotation=90)

# SD Card setup
sd_cs = board.D13
sdcard = sdcardio.SDCard(spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# I2C NeoKey setup
i2c = busio.I2C(board.SCL, board.SDA)
neokey = NeoKey1x4(i2c, addr=0x30)
amber = 0x300800
red = 0x900000
green = 0x009000

neokey.pixels.fill(amber)
keys = [
    (neokey, 0, green),
    (neokey, 1, red),
    (neokey, 2, green),
    (neokey, 3, green),
]
#  states for key presses
key_states = [False, False, False, False]

# STEMMA QT Rotary encoder setup
rotary_seesaw = seesaw.Seesaw(i2c, addr=0x36)  # default address is 0x36
encoder = rotaryio.IncrementalEncoder(rotary_seesaw)
last_encoder_pos = 0

# file system setup
mp3s = []
for filename in os.listdir('/sd'):
    if filename.lower().endswith('.mp3') and not filename.startswith('.'):
        mp3s.append("/sd/"+filename)

mp3s.sort()  # sort alphanumerically for mixtape  order, e.g., "1_King_of_Rock.mp3"
for mp3 in mp3s:
    print(mp3)

track_number = 0
mp3_filename = mp3s[track_number]
mp3_bytes = os.stat(mp3_filename)[6]  # size in bytes is position 6
mp3_file = open(mp3_filename, "rb")
mp3stream = audiomp3.MP3Decoder(mp3_file)

def tracktext(full_path_name, position):
    return full_path_name.split('_')[position].split('.')[0]
# LRC is word_select, BCLK is bit_clock, DIN is data_pin.
# Feather RP2040
audio = audiobusio.I2SOut(bit_clock=board.D24, word_select=board.D25, data=board.A3)
# Feather M4
# audio = audiobusio.I2SOut(bit_clock=board.D1, word_select=board.D10, data=board.D11)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)
mixer.voice[0].level = 0.15

# Colors
blue_bright = 0x17afcf
blue_mid = 0x0d6173
blue_dark = 0x041f24

orange_bright = 0xda8c57
orange_mid = 0xa46032
orange_dark = 0x472a16

# display
main_display_group = displayio.Group()  # everything goes in main group
display.root_group = main_display_group  # show main group (clears screen, too)

# background bitmap w OnDiskBitmap
tape_bitmap = displayio.OnDiskBitmap(open("mp3_tape.bmp", "rb"))
tape_tilegrid = displayio.TileGrid(tape_bitmap, pixel_shader=tape_bitmap.pixel_shader)
main_display_group.append(tape_tilegrid)


# song name label
song_name_text_group = displayio.Group(scale=3, x=90, y=44)  # text label goes in this Group
song_name_text = tracktext(mp3_filename, 2)
song_name_label = label.Label(terminalio.FONT, text=song_name_text, color=orange_bright)
song_name_text_group.append(song_name_label)  # add the label to the group
main_display_group.append(song_name_text_group)  # add to the parent group

# artist name label
artist_name_text_group = displayio.Group(scale=2, x=92, y=186)
artist_name_text = tracktext(mp3_filename, 1)
artist_name_label = label.Label(terminalio.FONT, text=artist_name_text, color=orange_bright)
artist_name_text_group.append(artist_name_label)
main_display_group.append(artist_name_text_group)

# song progress bar
progress_bar = HorizontalProgressBar(
    (72, 144),
    (174, 12),
    bar_color=blue_bright,
    outline_color=blue_mid,
    fill_color=blue_dark,
)
main_display_group.append(progress_bar)

# volume level bar
volume_bar = VerticalProgressBar(
    (304, 40),
    (8, 170),
    bar_color=orange_bright,
    outline_color=orange_mid,
    fill_color=orange_dark,
)
main_display_group.append(volume_bar)
volume_bar.value = mixer.voice[0].level * 100

def change_track(tracknum):
    # pylint: disable=global-statement
    global mp3_filename
    # pylint: disable=global-statement
    global mp3stream
    mp3_filename = mp3s[tracknum]
    song_name_fc = tracktext(mp3_filename, 2)
    artist_name_fc = tracktext(mp3_filename, 1)
    mp3_file_fc = open(mp3_filename, "rb")
    mp3stream.file = mp3_file_fc
    mp3stream_fc = mp3stream
    mp3_bytes_fc = os.stat(mp3_filename)[6]
    return (mp3_file_fc, mp3stream_fc, song_name_fc, artist_name_fc, mp3_bytes_fc)

print("Walkmp3rson")
play_state = False  # so we know if we're auto advancing when mixer finishes a song
last_debug_time = 0  # for timing track position
reels_anim_frame = 0
last_percent_done = 0.01
audio.play(mixer)
while True:
    encoder_pos = -encoder.position
    if encoder_pos != last_encoder_pos:
        encoder_delta = encoder_pos - last_encoder_pos
        volume_adjust = min(max((mixer.voice[0].level + (encoder_delta*0.005)), 0.0), 1.0)
        mixer.voice[0].level = volume_adjust

        last_encoder_pos = encoder_pos
        volume_bar.value = mixer.voice[0].level * 100

    if play_state is True:  # if not stopped, auto play next song
        if time.monotonic() - last_debug_time > 0.2:  # so we can check track progress
            last_debug_time = time.monotonic()
            bytes_played = mp3_file.tell()
            percent_done = (bytes_played / mp3_bytes)
            progress_bar.value = min(max(percent_done * 100, 0), 100)

        if not mixer.playing:
            print("next song")
            audio.pause()
            track_number = ((track_number + 1) % len(mp3s))
            mp3_file, mp3stream, song_name, artist_name, mp3_bytes = change_track(track_number)
            song_name_label.text = song_name
            artist_name_label.text = artist_name
            mixer.voice[0].play(mp3stream, loop=False)
            time.sleep(.1)
            audio.resume()

    # Use the NeoKeys as transport controls
    for k in range(len(keys)):
        neokey, key_number, color = keys[k]
        if neokey[key_number] and not key_states[key_number]:
            key_states[key_number] = True
            neokey.pixels[key_number] = color

            if key_number == 0:  # previous track
                audio.pause()
                track_number = ((track_number - 1) % len(mp3s) )
                mp3_file, mp3stream, song_name, artist_name, mp3_bytes = change_track(track_number)
                song_name_label.text = song_name
                artist_name_label.text = artist_name
                mixer.voice[0].play(mp3stream, loop=False)
                play_state = True
                time.sleep(.1)
                audio.resume()

            if key_number == 1:  # Play/pause
                if play_state:
                    audio.pause()
                    play_state = False
                else:
                    audio.resume()
                    play_state = True

            if key_number == 2:  # Play track from beginning
                audio.pause()
                mixer.voice[0].play(mp3stream, loop=False)
                song_name_label.text = tracktext(mp3_filename, 2)
                artist_name_label.text = tracktext(mp3_filename, 1)
                play_state = True
                time.sleep(.1)
                audio.resume()

            if key_number == 3:  # next track
                audio.pause()
                track_number = ((track_number + 1) % len(mp3s))
                mp3_file, mp3stream, song_name, artist_name, mp3_bytes = change_track(track_number)
                song_name_label.text = song_name
                artist_name_label.text = artist_name
                mixer.voice[0].play(mp3stream, loop=False)
                play_state = True
                time.sleep(.1)
                audio.resume()

        if not neokey[key_number] and key_states[key_number]:
            neokey.pixels[key_number] = amber
            key_states[key_number] = False
