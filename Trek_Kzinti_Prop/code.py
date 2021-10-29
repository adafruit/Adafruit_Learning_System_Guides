# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
KZINTI COSPLAY PROPS for Feather M4 Express. Same code can be used for
the "talking computer" prop or the simpler "total conversion beam."
It's essentially just a sound board and relies on a bit of acting flair
from its operator: understand that the "mode selector" slider really
just makes clicky noises (doesn't select actual modes), the keypad (if
building the talking computer) plays or selects one of nine sounds, and
the trigger either plays a zap-gun noise or the last-selected sound.

'pew.wav' derived from freesound.org/people/newlocknew/sounds/520056
CC BY 3.0 creativecommons.org/licenses/by/3.0
Other sounds via Adafruit, MIT license.
"""

import board  #                   For pin names
import keypad  #                  For talking computer buttons
import pwmio  #                   For LED flicker
from analogio import AnalogIn  #  For slider potentiometer
from audiocore import WaveFile  # For WAV file handling

# audioio is present on boards w/DAC out. If not available, fall back on
# audiopwmio. If neither is supported, code stops w/ImportError exception.
try:
    from audioio import AudioOut
except ImportError:
    from audiopwmio import PWMAudioOut as AudioOut


# CONFIGURABLES -----

# If building the talking computer: setting this True makes the keypad
# buttons play sounds when pressed. If False, keypad buttons select but
# do not play sounds -- that's done with the trigger button.
buttons_play = True

sound_folder = "/sounds"  # Location of WAV files
num_modes = 5  #            Number of clicks from slider, plus one
pin_to_wave = (  # This table maps input pins to corresponding WAV files:
    (board.A1, "pew.wav"),  # Trigger on handle
    (board.D4, "1.wav"),  #   9 buttons on top (if building
    (board.D12, "2.wav"),  #  talking computer, else ignored)
    (board.D11, "3.wav"),
    (board.D10, "4.wav"),
    (board.D9, "5.wav"),
    (board.D6, "6.wav"),
    (board.D5, "7.wav"),
    (board.SCL, "8.wav"),
    (board.SDA, "9.wav"),
)  # Tip: avoid pin D13 for keypad input; LED sometimes interferes.

# HARDWARE SETUP ---- mode selector, LED, speaker, keypad ----

analog_in = AnalogIn(board.A2)  # Slider for "mode selector"
mode = (analog_in.value * (num_modes - 1) + 32768) // 65536  # Initial mode
bounds = (  # Lower, upper limit to detect change from current mode
    (mode * 65535 - 32768) // (num_modes - 1) - 512,
    (mode * 65535 + 32768) // (num_modes - 1) + 512,
)

led = pwmio.PWMOut(board.A3)
led.duty_cycle = 0  # Start w/LED off
led_sync = 0  #       LED behavior for different sounds, see comments later

# AudioOut MUST be invoked AFTER PWMOut, for correct WAV playback timing.
# Maybe sharing a timer or IRQ. Unsure if bug or just overlooked docs.
audio = AudioOut(board.A0)  # A0 is DAC pin on M0/M4 boards

# To simplify the build, each key is wired to a separate input pin rather
# than making an X/Y matrix. CircuitPython's keypad module is still used
# (treating the buttons as a 1x10 matrix) as this gives us niceties such
# as background processing, debouncing and an event queue!
keys = keypad.Keys([x[0] for x in pin_to_wave], value_when_pressed=False, pull=True)
event = keypad.Event()  # Single key event for re-use
keys.events.clear()

# Load all the WAV files from the pin_to_wave list, and one more for the
# mode selector, sharing a common buffer since only one is used at a time.
# Also, play a startup sound.
audio_buf = bytearray(1024)
waves = [
    WaveFile(open(sound_folder + "/" + x[1], "rb"), audio_buf) for x in pin_to_wave
]
active_sound = 0  # Index of waves[] to play when trigger is pressed
selector_wave = WaveFile(open(sound_folder + "/" + "click.wav", "rb"), audio_buf)
audio.play(WaveFile(open(sound_folder + "/" + "startup.wav", "rb"), audio_buf))

# MAIN LOOP --------- repeat forever ----

while True:

    # Process the mode selector slider, check if moved into a new position.
    # This is currently just used to make click noises, it doesn't actually
    # change any "mode" in the operation of the prop, but it could if we
    # really wanted, with additional code (e.g. different sound sets).
    selector_pos = analog_in.value
    if not bounds[0] < selector_pos < bounds[1]:  # Moved out of mode range?
        # New mode, new bounds. +/-512 adds a little hysteresis to selection.
        mode = (selector_pos * (num_modes - 1) + 32768) // 65536
        bounds = (
            (mode * 65535 - 32768) // (num_modes - 1) - 512,
            (mode * 65535 + 32768) // (num_modes - 1) + 512,
        )
        led_sync = 0  #              LED stays off for selector sound
        audio.play(selector_wave)  # Make click sound

    # Process keypad input. If building the "total conversion beam,"
    # only the trigger button is wired up, the rest simply ignored.
    if keys.events.get_into(event) and event.pressed:
        if event.key_number == 0:  # Trigger button
            # LED is steady for zap gun (index 0), flickers for other sounds
            led_sync = 1 if active_sound else 2
            audio.play(waves[active_sound])
        elif buttons_play:  # Other buttons, play immediately
            led_sync = 1
            audio.play(waves[event.key_number])
        else:  # Other buttons, select but don't play
            # Once another sound is selected, no going back to the zap.
            active_sound = event.key_number
            led_sync = 0  # Don't blink during selector sound
            audio.play(selector_wave)

    # LED is continually updated. If sound playing, and led_sync set above...
    if audio.playing and led_sync > 0:
        # Trigger button sound is steady on. For others, peek inside the
        # WAV audio buffer, this provides a passable voice-to-LED flicker.
        if led_sync == 2:
            led.duty_cycle = 65535
        else:
            led.duty_cycle = 65535 - abs(audio_buf[1] - 128) * 65535 // 128
    else:  # No sound, or is just selector clicks (no LED)
        led.duty_cycle = 0
