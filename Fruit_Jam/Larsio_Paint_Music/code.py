# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Larsio Paint Music
Fruit Jam w mouse, HDMI, audio out
or Metro RP2350 with EYESPI DVI breakout and TLV320DAC3100 breakout on STEMMA_I2C,
pin D7 reset, 9/10/11 = BCLC/WSEL/DIN
"""
# pylint: disable=invalid-name,too-few-public-methods,broad-except,redefined-outer-name

# Main application file for Larsio Paint Music

import time
import gc
from sound_manager import SoundManager
from note_manager import NoteManager
from ui_manager import UIManager

# Configuration
AUDIO_OUTPUT = "i2s"  # Options: "pwm" or "i2s"

class MusicStaffApp:
    """Main application class that ties everything together"""

    def __init__(self, audio_output="pwm"):
        # Initialize the sound manager with selected audio output
        # Calculate tempo parameters
        BPM = 120  # Beats per minute
        SECONDS_PER_BEAT = 60 / BPM
        SECONDS_PER_EIGHTH = SECONDS_PER_BEAT / 2

        # Initialize components in a specific order
        # First, force garbage collection to free memory
        gc.collect()

        # Initialize the sound manager
        print("Initializing sound manager...")
        self.sound_manager = SoundManager(
            audio_output=audio_output,
            seconds_per_eighth=SECONDS_PER_EIGHTH
        )

        # Give hardware time to stabilize
        time.sleep(0.5)
        gc.collect()

        # Initialize the note manager
        print("Initializing note manager...")
        self.note_manager = NoteManager(
            start_margin=25,  # START_MARGIN
            staff_y_start=int(240 * 0.1),  # STAFF_Y_START
            line_spacing=int((240 - int(240 * 0.1) - int(240 * 0.2)) * 0.95) // 8  # LINE_SPACING
        )

        gc.collect()

        # Initialize the UI manager
        print("Initializing UI manager...")
        self.ui_manager = UIManager(self.sound_manager, self.note_manager)

    def run(self):
        """Set up and run the application"""
        # Setup the display and UI
        print("Setting up display...")
        self.ui_manager.setup_display()

        # Give hardware time to stabilize
        time.sleep(0.5)
        gc.collect()

        # Try to find the mouse
        if self.ui_manager.find_mouse():
            print("Mouse found successfully!")
        else:
            print("WARNING: Mouse not found.")
            print("The application will run, but mouse control may be limited.")

        # Enter the main loop
        self.ui_manager.main_loop()


# Create and run the application
if __name__ == "__main__":
    # Start with garbage collection
    gc.collect()
    print("Starting Music Staff Application...")

    try:
        app = MusicStaffApp(audio_output=AUDIO_OUTPUT)
        app.run()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error with I2S audio: {e}")

        # Force garbage collection
        gc.collect()
        time.sleep(1)

        # Fallback to PWM
        try:
            app = MusicStaffApp(audio_output="pwm")
            app.run()
        except Exception as e2:  # pylint: disable=broad-except
            print(f"Fatal error: {e2}")
