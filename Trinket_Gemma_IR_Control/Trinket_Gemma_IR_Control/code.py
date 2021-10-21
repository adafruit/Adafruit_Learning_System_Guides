# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
IR codes for button 0, 1, 2, 3 these were acquired from the
Adafruit Mini Remote Control #389
https://www.adafruit.com/product/389
stored as a 2D list
these codes were collected from running IR_reader.py
and watching the output on the REPL console
"""

import time

import adafruit_irremote
import board
import pulseio
import simpleio

speaker_pin = board.D0  # speaker connected to digital pin
ir_pin = board.D2  # pin connected to IR receiver.

fuzzyness = 0.2  # IR remote timing must be within 20% tolerance

button_presses = [

    [
        9073, 4504, 575, 589, 557, 581, 546, 592, 553, 585, 542, 595,
        550, 588, 552, 588, 544, 591, 549, 1671, 579, 1669, 572, 1675,
        577, 1671, 570, 1678, 574, 1673, 579, 559, 572, 1676, 575, 589,
        542, 596, 546, 1674, 577, 1671, 571, 567, 574, 590, 552, 586,
        545, 593, 548, 1672, 569, 1678, 574, 591, 550, 588, 550, 1670,
        575, 1673, 579, 1671, 570, 1675, 586
    ],

    [
        9075, 4498, 571, 566, 575, 562, 569, 569, 573, 564, 577, 587, 544,
        567, 577, 587, 551, 586, 545, 1675, 577, 1671, 575, 1672, 574, 1674,
        580, 1668, 572, 1675, 576, 589, 542, 1678, 574, 564, 577, 588, 543,
        594, 547, 591, 551, 1669, 572, 592, 553, 585, 542, 595, 550, 1671,
        577, 1670, 571, 1677, 575, 1673, 569, 576, 565, 1675, 577, 1670, 572,
        1676, 575
    ],

    [
        9070, 4505, 574, 563, 578, 559, 572, 566, 575, 562, 569, 569, 573, 564,
        577, 561, 570, 567, 575, 1674, 578, 1669, 577, 1670, 577, 1670, 571,
        1677, 575, 1672, 569, 569, 573, 1674, 577, 1671, 571, 566, 575, 562,
        569, 575, 566, 1675, 577, 560, 571, 567, 574, 563, 568, 569, 573, 1675,
        576, 1671, 571, 1681, 571, 562, 569, 1679, 575, 1672, 578, 1670, 570
    ],

    [
        9080, 4500, 569, 568, 573, 564, 577, 561, 570, 567, 574, 564, 578, 559,
        577, 561, 575, 562, 579, 1669, 572, 1675, 577, 1671, 570, 1677, 575,
        1673, 578, 1672, 570, 570, 571, 1671, 574, 564, 574, 1678, 573, 560,
        571, 568, 574, 1671, 570, 568, 573, 564, 577, 561, 570, 1677, 575, 563,
        578, 1669, 572, 1676, 576, 561, 570, 1677, 574, 1674, 578, 1669, 572
    ]

]


def fuzzy_pulse_compare(received):
    # Did we receive a full IR code?
    # Should be 67 timings for this remote
    if len(received) == len(button_presses[0]):

        # compare received IR code with our stored button_press list
        # remote control button codes for : [0-3]
        for b_index, button_press in enumerate(button_presses):

            # compare individual timings for each IR code
            # confirm that every entry is within fuzzyness 20% accuracy
            for i, press in enumerate(button_press):

                threshold = int(press * fuzzyness)

                if abs(press - received[i]) < threshold:
                    match_count[b_index] += 1


def play_tone():
    """ half second tones based on button selection [0-3] """
    if remote_control_press == 0:
        simpleio.tone(speaker_pin, 400, .5)  # 400Hz beep, 1/2 sec

    elif remote_control_press == 1:
        simpleio.tone(speaker_pin, 500, .5)  # 500Hz beep, 1/2 sec

    elif remote_control_press == 2:
        simpleio.tone(speaker_pin, 600, .5)  # 600Hz beep, 1/2 sec

    elif remote_control_press == 3:
        simpleio.tone(speaker_pin, 700, .5)  # 700Hz beep, 1/2 sec


# Create pulse input and IR decoder.
pulses = pulseio.PulseIn(ir_pin, maxlen=200, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# Loop waiting to receive pulses.
while True:
    # total count of IR code matches for each button {0, 1, 2, 3}
    match_count = [0] * len(button_presses)

    # make sure pulses is empty
    pulses.clear()
    pulses.resume()
    time.sleep(.1)

    # Wait for a pulse to be detected.
    detected = decoder.read_pulses(pulses)

    fuzzy_pulse_compare(detected)

    # confirm that we know this button
    # received IR code compared with saved button_presses
    # 100% match (+/- fuzziness)
    # otherwise we don't know this button pressed
    if max(match_count) == len(button_presses[0]):
        remote_control_press = match_count.index(max(match_count))
        play_tone()
        print(match_count.index(max(match_count)))
    else:
        print("unknown button")
