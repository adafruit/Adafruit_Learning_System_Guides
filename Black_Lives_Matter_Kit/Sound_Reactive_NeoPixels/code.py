import array
import math
import board
import audiobusio
import neopixel
from rainbowio import colorwheel

# Increase this number to use this example in louder environments. As you increase the number, it
# increases the level of sound needed to change the color of the LEDs. 5 is good for quiet up to
# workshop-level settings. If you plan to be in a louder setting, increase this number to maintain
# the same behavior as in a quieter setting.
magnitude_color_modifier = 5

pixels = neopixel.NeoPixel(board.NEOPIXEL, 6, auto_write=False)
mic = audiobusio.PDMIn(
    board.MICROPHONE_CLOCK, board.MICROPHONE_DATA, sample_rate=16000, bit_depth=16
)


def normalized_rms(values):
    """Normalized Root Mean Square. Removes DC bias before computing RMS."""
    mean_values = int(sum(values) / len(values))
    return math.sqrt(
        sum(float(sample - mean_values) * (sample - mean_values) for sample in values)
        / len(values)
    )


audio_samples = []  # Create an empty list for sample values
while True:
    sample_array = array.array("H", [0] * 32)
    mic.record(sample_array, len(sample_array))
    normalized_samples = normalized_rms(sample_array)  # Calculate normalized sample value
    audio_samples.append(normalized_samples)  # Add normalized values to the audio samples list
    audio_samples = audio_samples[-10:]  # Keep only the 10 most recent values in samples list
    magnitude = sum(audio_samples) / len(audio_samples)  # The average of the last 10 audio samples
    print(magnitude)
    # Fill NeoPixels with color based on scaled magnitude
    pixels.fill(colorwheel(min(255, (magnitude / magnitude_color_modifier))))
    pixels.show()
