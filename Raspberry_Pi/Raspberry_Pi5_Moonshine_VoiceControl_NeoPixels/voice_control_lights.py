# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Adapted from Moonshine my-dalek example:
https://github.com/moonshine-ai/moonshine/blob/main/examples/raspberry-pi/my-dalek/my-dalek.py
"""
import argparse
import sys
import time
import board
import neopixel
from moonshine_voice import (
    MicTranscriber,
    TranscriptEventListener,
    IntentRecognizer,
    get_model_for_language,
    get_embedding_model,
)
from adafruit_led_animation.animation.colorcycle import ColorCycle

# pylint: disable=global-statement

# NeoPixels setup
PIXEL_PIN = board.D26  # pin that the NeoPixel is connected to
pixels = neopixel.NeoPixel(PIXEL_PIN, 30, brightness=0.1)

# CLI args setup
parser = argparse.ArgumentParser(
    description="Control NeoPixels using your voice on a Raspberry Pi"
)
parser.add_argument(
    "--model-arch",
    type=str,
    default=None,
    help="Model architecture to use for transcription",
)
parser.add_argument(
    "--embedding-model",
    type=str,
    default="embeddinggemma-300m",
    help="Embedding model name (default: embeddinggemma-300m)",
)
parser.add_argument(
    "--threshold",
    type=float,
    default=0.6,
    help="Similarity threshold for intent matching (default: 0.6)",
)
args = parser.parse_args()


# Generic handler for intent triggers
def on_intent_triggered_on(trigger: str, utterance: str, similarity: float):
    """Handler for when an intent is triggered."""
    print(
        f"\n'{trigger.upper()}' triggered by '{utterance}' with {similarity:.0%} confidence"
    )


class TranscriptPrinter(TranscriptEventListener):
    """Listener that prints transcript updates to the terminal."""

    def __init__(self):
        self.last_line_text_length = 0

    def update_last_terminal_line(self, new_text: str):
        print(f"\r{new_text}", end="", flush=True)
        if len(new_text) < self.last_line_text_length:
            diff = self.last_line_text_length - len(new_text)
            print(f"{' ' * diff}", end="", flush=True)
        self.last_line_text_length = len(new_text)

    def on_line_started(self, event):  # pylint: disable=unused-argument
        self.last_line_text_length = 0

    def on_line_text_changed(self, event):
        self.update_last_terminal_line(f"{event.line.text}")

    def on_line_completed(self, event):
        self.update_last_terminal_line(f"{event.line.text}")
        print()  # New line after completion


# Load the transcription model
print("Loading transcription model...", file=sys.stderr)
model_path, model_arch = get_model_for_language("en", args.model_arch)

# Download and load the embedding model for intent recognition
quantization = "q4"
print(
    f"Loading embedding model ({args.embedding_model}, variant={quantization})...",
    file=sys.stderr,
)
embedding_model_path, embedding_model_arch = get_embedding_model(
    args.embedding_model, quantization
)

# Create the intent recognizer (implements TranscriptEventListener)
print(f"Creating intent recognizer (threshold={args.threshold})...", file=sys.stderr)
intent_recognizer = IntentRecognizer(
    model_path=embedding_model_path,
    model_arch=embedding_model_arch,
    model_variant=quantization,
    threshold=args.threshold,
)

colors = [
    ("red", (255, 0, 0)),
    ("blue", (0, 0, 255)),
    ("green", (0, 255, 0)),
    ("yellow", (255, 255, 0)),
    ("orange", (255, 95, 0)),
    ("pink", (255, 0, 255)),
    ("purple", (90, 0, 255)),
    ("turquoise", (0, 255, 255)),
    ("off", (0, 0, 0)),
    ("black", (0, 0, 0)),
]

# Disco Party animation setup
disco_party = ColorCycle(pixels, speed=0.35, colors=[_[1] for _ in colors[:8]])
run_disco_animation = False


def build_lights_color_callback_function(input_data):
    """
    Given a tuple with color name, and RGB values like:
    ("red", (255, 0, 0))
    Create and return an intent trigger callback function
    that turns the NeoPixels the specified color.
    """

    def lights_color_callback(trigger: str, utterance: str, similarity: float):
        print("###########################")
        print(f"# {trigger} - {utterance} - {similarity}")
        print(f"# Turning lights {input_data[0]}")
        print("###########################")
        global run_disco_animation
        run_disco_animation = False
        pixels.fill(input_data[1])
        pixels.show()

    return lights_color_callback


def on_disco_party(trigger: str, utterance: str, similarity: float):
    """
    Intent trigger listener callback function for Disco Party command.
    Enables the disco party animation boolean.
    """
    print("###########################")
    print(f"# {trigger} - {utterance} - {similarity}")
    print("# Disco Party!")
    print("###########################")
    global run_disco_animation
    run_disco_animation = True


# Register intents with their trigger phrases and handlers
intents = {
    "disco party": on_disco_party,
}
# Add intents for all color commands
for color in colors:
    intents[f"lights {color[0]}"] = build_lights_color_callback_function(color)
    intents[f"{color[0]} lights"] = build_lights_color_callback_function(color)

for intent, handler in intents.items():
    intent_recognizer.register_intent(intent, handler)
print(f"Registered {intent_recognizer.intent_count} intents", file=sys.stderr)

# Initialize transcriber
transcriber = MicTranscriber(model_path=model_path, model_arch=model_arch)

# Add both the transcript printer and intent recognizer as listeners
# The intent recognizer will process completed lines and trigger handlers
transcript_printer = TranscriptPrinter()
transcriber.add_listener(transcript_printer)
transcriber.add_listener(intent_recognizer)

print("\n" + "=" * 60, file=sys.stderr)
print("🎤 Listening for voice commands...", file=sys.stderr)
print("Try saying phrases with the same meaning as these actions:", file=sys.stderr)
for intent in intents.keys():  # pylint: disable=consider-iterating-dictionary
    print(f"  - '{intent}'", file=sys.stderr)
print("=" * 60, file=sys.stderr)
print("Press Ctrl+C to stop.\n", file=sys.stderr)

transcriber.start()
try:
    # Loop forever, listening for voice commands,
    # and showing NeoPixel animation when appropriate.
    while True:
        if run_disco_animation:
            disco_party.animate()
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\n\nStopping...", file=sys.stderr)
finally:
    intent_recognizer.close()
    transcriber.stop()
    transcriber.close()
