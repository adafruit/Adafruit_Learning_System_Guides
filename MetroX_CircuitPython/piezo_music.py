"""
'piezo_music.py'.

=================================================
Twinkle Twinkle with a piezo!
requires:
- simpleio library
"""
import time
import board
from simpleio import tone

NOTES = "ccdcfeccdcgf "
BEATS = [1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 4]
TONES = {"c": 263, "d": 293, "e": 329, "f": 349, "g": 391, "a": 440, "b": 493, "C": 523}
TEMPO = 300

# play the notes!
for i, item in enumerate(NOTES):
    tempodelay = 60 / TEMPO
    note = NOTES[i]
    beat = BEATS[i]
    print(note, end="")
    if note == " ":
        time.sleep(beat * tempodelay)
    else:
        tone(board.D9, TONES[note], beat * tempodelay)
    time.sleep(tempodelay / 2)
