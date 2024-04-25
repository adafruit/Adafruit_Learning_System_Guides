# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import pulseio
import board

pulses = pulseio.PulseIn(board.D5)
pulse = False
pulse_count = 0

while True:

    # Wait for an active pulse
    while len(pulses) == 0:
        if pulse:
            pulse = False

    if len(pulses) != 0 and not pulse:
        pulse_count += 1
        print(f"pulses detected {pulse_count} times")
        pulse = True
    # Pause while we do something with the pulses
    pulses.pause()
    # Print the pulses. pulses[0] is an active pulse unless the length
    # reached max length and idle pulses are recorded.
    print(pulses[0])
    # Clear the rest
    pulses.clear()
    # Resume with an 80 microsecond active pulse
    pulses.resume(80)
