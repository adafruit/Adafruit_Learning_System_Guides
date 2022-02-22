# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'audio.py'.

=================================================
alarm circuit with a FSR and a speaker
requires:
- CircuitPython_CharLCD Module
"""
import audioio
import analogio
import board

f = open("siren.wav", "rb")
a = audioio.AudioOut(board.A0, f)

fsr = analogio.AnalogIn(board.A2)
threshold = 200
while True:
    if fsr.value < threshold:
        a.play(loop=True)
    else:
        a.pause()
