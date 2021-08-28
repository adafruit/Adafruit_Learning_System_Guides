"""
CircuitPython Audio-capable pin identifying script
"""
import board
from microcontroller import Pin
try:
    from audioio import AudioOut
except ImportError:
    from audiopwmio import PWMAudioOut as AudioOut


def is_audio(audio_pin_name):
    try:
        p = AudioOut(audio_pin_name)
        p.deinit()
        return True
    except ValueError:
        return False
    except RuntimeError:
        return False


def get_unique_pins():
    exclude = [
        getattr(board, p)
        for p in [
            # This is not an exhaustive list of unexposed pins. Your results
            # may include other pins that you cannot easily connect to.
            "NEOPIXEL",
            "DOTSTAR_CLOCK",
            "DOTSTAR_DATA",
            "APA102_SCK",
            "APA102_MOSI",
            "L",
            "SWITCH",
            "BUTTON",
        ]
        if p in dir(board)
    ]
    pins = [
        pin
        for pin in [getattr(board, p) for p in dir(board)]
        if isinstance(pin, Pin) and pin not in exclude
    ]
    unique = []
    for p in pins:
        if p not in unique:
            unique.append(p)
    return unique


for audio_pin in get_unique_pins():
    if is_audio(audio_pin):
        print("Audio pin:", audio_pin)
