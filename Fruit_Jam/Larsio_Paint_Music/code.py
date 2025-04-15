# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
Larsio Paint Music
Fruit Jam w mouse, HDMI, audio out
'''

# Main application file for the Music Staff application

from sound_manager import SoundManager
from note_manager import NoteManager
from ui_manager import UIManager
import time
import gc

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

        # Try to find the mouse with multiple attempts
        MAX_ATTEMPTS = 5
        RETRY_DELAY = 1  # seconds

        mouse_found = False
        for attempt in range(MAX_ATTEMPTS):
            print(f"Mouse detection attempt {attempt+1}/{MAX_ATTEMPTS}")
            if self.ui_manager.find_mouse():
                mouse_found = True
                print("Mouse found successfully!")
                break

            print(f"Mouse detection attempt {attempt+1} failed, retrying...")
            time.sleep(RETRY_DELAY)

        if not mouse_found:
            print("WARNING: Mouse not found after multiple attempts.")
            print("The application will run, but mouse control may be limited.")

        # Enter the main loop
        self.ui_manager.main_loop()


# Create and run the application
if __name__ == "__main__":
    # Start with garbage collection
    gc.collect()
    print("Starting Music Staff Application...")

    #
    try:
        app = MusicStaffApp(audio_output=AUDIO_OUTPUT)
        app.run()
    except Exception as e:
        print(f"Error with I2S audio: {e}")
        print("Retrying with PWM audio...")

        # Force garbage collection
        gc.collect()
        time.sleep(1)

        # Fallback to PWM
        try:
            app = MusicStaffApp(audio_output="pwm")
            app.run()
        except Exception as e:
            print(f"Fatal error: {e}")
