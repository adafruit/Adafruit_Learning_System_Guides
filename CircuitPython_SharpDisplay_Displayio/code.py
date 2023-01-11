# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import random
import time

import adafruit_display_text.label
from adafruit_bitmap_font import bitmap_font
import board
import displayio
import framebufferio
import sharpdisplay

## When making several changes, this ensures they aren't shown partially
## completed (except for the time to actually update the display)
class BatchDisplayUpdate:
    def __init__(self, the_display):
        self.the_display = the_display
        self.auto_refresh = the_display.auto_refresh

    def __enter__(self):
        self.the_display.auto_refresh = False

    def __exit__(self, unused1, unused2, unused3):
        self.the_display.refresh()
        self.the_display.auto_refresh = self.auto_refresh

# https://saytheirnames.com/
# real people, not just #hashtags
names = [
    "Rodney King",
    "Abner Louima",
    "Amadou Diallo",
    "Sean Bell",
    "Oscar Grant",
    "Eric Garner",
    "Michael Brown",
    "Laquan McDonald",
    "Freddie Gray",
    "Antwon Rose Jr",
    "Ahmaud Arbery",
    "Breonna Taylor",
    "John Crawford III",
    "Ezell Ford",
    "Dante Parker",
    "Michelle Cusseaux",
    "Laquan Mcdonald",
    "George Mann",
    "Tanisha Anderson",
    "Akai Gurley",
    "Tamir Rice",
    "Rumain Brisbon",
    "Jerame Reid",
    "Matthew Ajibade",
    "Frank Smart",
    "Nastasha McKenna",
    "Tony Robinson",
    "Anthony Hill",
    "Mya Hall",
    "Phillip White",
    "Eric Harris",
    "Walter Scott",
    "William Chapman II",
    "Alexia Christian",
    "Brendon Glenn",
    "Victor Maunel Larosa",
    "Jonathan Sanders",
    "Freddie Blue",
    "Joseph Mann",
    "Salvado Ellswood",
    "Sanda Bland",
    "Albert Joseph Davis",
    "Darrius Stewart",
    "Billy Ray Davis",
    "Samuel Dubose",
    "Michael Sabbie",
    "Brian Keith Day",
    "Christian Taylor",
    "Troy Robinson",
    "Asshams Pharoah Manley",
    "Felix Kumi",
    "Keith Harrison Mcleod",
    "Junior Prosper",
    "Lamontez Jones",
    "Paterson Brown",
    "Dominic Hutchinson",
    "Anthony Ashford",
    "Alonzo Smith",
    "Tyree Crawford",
    "India Kager",
    "La'vante Biggs",
    "Michael Lee Marshall",
    "Jamar Clark",
    "Richard Perkins",
    "Nathaniel Harris Pickett",
    "Benni Lee Tignor",
    "Miguel Espinal",
    "Michael Noel",
    "Kevin Matthews",
    "Bettie Jones",
    "Quintonio Legrier",
    "Keith Childress Jr",
    "Janet Wilson",
    "Randy Nelson",
    "Antronie Scott",
    "Wendell Celestine",
    "David Joseph",
    "Calin Roquemore",
    "Dyzhawn Perkins",
    "Christoper Davis",
    "Marco Loud",
    "Peter Gaines",
    "Torry Robison",
    "Darius Robinson",
    "Kevin Hicks",
    "Mary Truxillo",
    "Demarcus Semer",
    "Willie Tillman",
    "Terrill Thomas",
    "Sylville Smith",
    "Sean Reed",
    "Alton Streling",
    "Philando Castile",
    "Terence Crutcher",
    "Paul O'Neal",
    "Alteria Woods",
    "Jordan Edwards",
    "Aaron Bailey",
    "Ronell Foster",
    "Stephon Clark",
    "Antwon Rose II",
    "Botham Jean",
    "Pamela Turner",
    "Dominique Clayton",
    "Atatiana Jefferson",
    "Christopher Whitfield",
    "Christopher Mccovey",
    "Eric Reason",
    "Michael Lorenzo Dean",
    "Tony McDade",
    "David McAtee",
    "George Floyd",
]

# A function to choose "k" different items from the "population" list
# We'll use it to select the names to display
def sample(population, k):
    population = population[:]
    for _ in range(k):
        j = random.randint(0, len(population)-1)
        yield population[j]
        population[j] = population[-1]
        population.pop()

# Initialize the display, cleaning up after a display from the previous run
# if necessary
displayio.release_displays()
bus = board.SPI()
framebuffer = sharpdisplay.SharpMemoryFramebuffer(bus, board.D6, 400, 240)
display = framebufferio.FramebufferDisplay(framebuffer, auto_refresh = True)

# Load our font
font = bitmap_font.load_font("/GothamBlack-54.bdf")

# Create a Group for the BLM text
blm_group = displayio.Group()
display.show(blm_group)

# Create a 3 line set of text for BLM
blm_font = [None, None, None]
for line in range(3):
    label = adafruit_display_text.label.Label(font, color=0xFFFFFF)
    label.anchor_point = (0, 0)
    label.anchored_position = (8, line*84+8)
    blm_font[line] = label
    blm_group.append(label)

# Get something on the display as soon as possible by loading
# specific glyphs.
font.load_glyphs(b"BLACK")
blm_font[0].text = "BLACK"
font.load_glyphs(b"ISEV")
blm_font[1].text = "LIVES"
font.load_glyphs(b"RMT")
blm_font[2].text = "MATTER"
font.load_glyphs(b"' DFGHJNOPQUWXYZabcdefghijklmnopqrstuvwxyz")


# Create a 2 line set of font text for names
names_font = [None, None]
for line in range(2):
    label = adafruit_display_text.label.Label(font, color=0xFFFFFF)
    # Center each line horizontally, position vertically
    label.anchor_point = (0.5, 0)
    label.anchored_position = (200, line*84+42)
    names_font[line] = label

# Create a Group for the name text
name_group = displayio.Group()
for line in names_font:
    name_group.append(line)

# Repeatedly show the BLM slogan and then 5 names.
while True:
    display.show(blm_group)

    # Show the BLM slogan
    with BatchDisplayUpdate(display):
        blm_font[1].color = blm_font[2].color = 0  # hide lines 2&3
    time.sleep(1)

    with BatchDisplayUpdate(display):
        blm_font[1].color = 0xFFFFFF  # show middle line
        blm_font[0].color = blm_font[2].color = 0  # hide lines 1&3
    time.sleep(1)

    with BatchDisplayUpdate(display):
        blm_font[2].color = 0xFFFFFF  # show last line
        blm_font[0].color = blm_font[1].color = 0  # hide lines 1&2
    time.sleep(1)

    with BatchDisplayUpdate(display):
        for line in blm_font:
            line.color = 0xFFFFFF
    time.sleep(2)

    # Show 5 names
    display.show(name_group)
    for name in sample(names, 5):
        print(name)
        lines = name.split(" ")
        with BatchDisplayUpdate(display):
            for i in range(2):
                names_font[i].text = lines[i]
        time.sleep(5)
    names_font[0].text = names_font[1].text = ""
