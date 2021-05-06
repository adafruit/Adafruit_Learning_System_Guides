"""CircuitPython Touch-Compatible Pin Identification Script"""
import board
import touchio
from microcontroller import Pin


def is_touch_capable(pin_name):
    """Attempts to create touchio.TouchIn() object on all available pins. Returns True if valid."""
    try:
        _ = touchio.TouchIn(pin_name)
        # Print the touch-capable pins that do not need, or already have, an external pulldown.
        return True
    except ValueError as e:  # A ValueError is raised when a pin is invalid or needs a pulldown.
        x = getattr(e, "message", str(e))  # Obtain the message associated with the ValueError.
        if "pulldown" in x:  # If the ValueError is regarding needing a pulldown...
            return True  # ...the pin is valid.
        else:
            return False  # Otherwise, the pins are invalid.
    except TypeError:  # Error returned when checking a non-pin object in dir(board).
        pass  # Passes over non-pin objects in dir(board).


def get_pin_names():
    """Gets all unique pin names available in the board module, excluding a defined list."""
    exclude = ["NEOPIXEL", "APA102_MOSI", "APA102_SCK", "LED", "NEOPIXEL_POWER", "BUTTON",
               "BUTTON_UP", "BUTTON_DOWN", "BUTTON_SELECT", "DOTSTAR_CLOCK", "DOTSTAR_DATA",
               "IR_PROXIMITY"]
    pins = [pin for pin in [getattr(board, p) for p in dir(board) if p not in exclude]
            if isinstance(pin, Pin)]
    pin_names = []
    for p in pins:
        if p not in pin_names:
            pin_names.append(p)
    return pin_names


for possible_touch_pin in get_pin_names():  # Get the pin name.
    if is_touch_capable(possible_touch_pin):  # Check if the pin is touch-capable.
        print("Touch on:", str(possible_touch_pin).replace("board.", ""))  # Print the valid list.
