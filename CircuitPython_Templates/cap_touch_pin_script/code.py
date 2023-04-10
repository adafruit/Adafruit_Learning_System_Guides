# SPDX-FileCopyrightText: 2021-2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Touch-Compatible Pin Identification Script

Depending on the order of the pins in the CircuitPython pin definition, some inaccessible pins
may be returned in the script results. Consult the board schematic and use your best judgement.

In some cases, such as LED, the associated pin, such as D13, may be accessible. The LED pin
name is first in the list in the pin definition, and is therefore printed in the results. The
pin name "LED" will work in code, but "D13" may be more obvious. Use the schematic to verify.
"""
import board
import touchio
from microcontroller import Pin


def get_pin_names():
    """
    Gets all unique pin names available in the board module, excluding a defined list.
    This list is not exhaustive, and depending on the order of the pins in the CircuitPython
    pin definition, some of the pins in the list may still show up in the script results.
    """
    exclude = [
        "NEOPIXEL",
        "APA102_MOSI",
        "APA102_SCK",
        "LED",
        "NEOPIXEL_POWER",
        "BUTTON",
        "BUTTON_UP",
        "BUTTON_DOWN",
        "BUTTON_SELECT",
        "DOTSTAR_CLOCK",
        "DOTSTAR_DATA",
        "IR_PROXIMITY",
        "SPEAKER_ENABLE",
        "BUTTON_A",
        "BUTTON_B",
        "POWER_SWITCH",
        "SLIDE_SWITCH",
        "TEMPERATURE",
        "ACCELEROMETER_INTERRUPT",
        "ACCELEROMETER_SDA",
        "ACCELEROMETER_SCL",
        "MICROPHONE_CLOCK",
        "MICROPHONE_DATA",
        "RFM_RST",
        "RFM_CS",
        "RFM_IO0",
        "RFM_IO1",
        "RFM_IO2",
        "RFM_IO3",
        "RFM_IO4",
        "RFM_IO5",
    ]
    pins = [
        pin
        for pin in [getattr(board, p) for p in dir(board) if p not in exclude]
        if isinstance(pin, Pin)
    ]
    pin_names = []
    for pin_object in pins:
        if pin_object not in pin_names:
            pin_names.append(pin_object)
    return pin_names


for possible_touch_pin in get_pin_names():  # Get the pin name.
    try:
        touch_pin_object = touchio.TouchIn(
            possible_touch_pin
        )  # Attempt to create the touch object on each pin.
        # Print the touch-capable pins that do not need, or already have, an external pulldown.
        print("Touch on:", str(possible_touch_pin).replace("board.", ""))
    except ValueError as error:  # A ValueError is raised when a pin is invalid or needs a pulldown.
        # Obtain the message associated with the ValueError.
        error_message = getattr(error, "message", str(error))
        if (
            "pulldown" in error_message  # If the ValueError is regarding needing a pulldown...
        ):
            print(
                "Touch (no pulldown) on:", str(possible_touch_pin).replace("board.", "")
            )
        else:
            print("No touch on:", str(possible_touch_pin).replace("board.", ""))
    except TypeError:  # Error returned when checking a non-pin object in dir(board).
        pass  # Passes over non-pin objects in dir(board).
