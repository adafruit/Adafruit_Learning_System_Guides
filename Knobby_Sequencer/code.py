# SPDX-FileCopyrightText: John Park for Adafruit 2025 Knobby MIDI Step Sequencer
# SPDX-License-Identifier: MIT
"""
MIDI Step Sequencer for QT Py RP2040 with NeoRotary 4 encoder seesaw boards
Configurable 4/8/12/16-step sequencer:
- Each encoder controls one step's note pitch
- Encoder buttons toggle steps on/off
- DOUBLE-CLICK first knob to enter settings mode
- In settings mode: control playback, tempo, scales, velocity, randomization
- External NeoPixel strip shows step status and current playback position
- Sends MIDI notes via USB
- I2C reads only after each board's 4 steps for performance
- Uses bulk digital reads for better I2C performance
"""

import time
import random
import busio
import board
import digitalio
import usb_midi

import adafruit_seesaw.digitalio
import adafruit_seesaw.rotaryio
import adafruit_seesaw.seesaw
import neopixel

from scales import get_scale, list_scales, get_scale_info

# USER CONFIGURATION
SCALE_MODE = "major"  # Options: see scales.py for all available scales
STEPS = 16           # Options: 4, 8, 12, or 16 steps
BPM = 90            # Beats per minute

# I2C addresses for encoder boards (add/remove as needed)
I2C_ADDRESSES = [0x49, 0x4A, 0x4B, 0x4C]  # Up to 4 boards for 16 steps

# Calculate number of NeoPixels based on steps
NEOPIXEL_COUNT = {4: 12, 8: 24, 12: 36, 16: 48}
NUM_NEOPIXELS = NEOPIXEL_COUNT.get(STEPS, 24)

# Validate configuration
if STEPS not in [4, 8, 12, 16]:
    raise ValueError("STEPS must be 4, 8, 12, or 16")

REQUIRED_BOARDS = (STEPS + 3) // 4  # Round up division
if len(I2C_ADDRESSES) < REQUIRED_BOARDS:
    raise ValueError(f"Need at least {REQUIRED_BOARDS} I2C addresses for {STEPS} steps")

STEP_TIME = 60.0 / BPM / 4  # 16th note timing

# Button pin mappings for bulk reads
BUTTON_PINS_BOARD = [12, 14, 17, 9]  # Pin numbers for board buttons
BUTTON_MASK_BOARD = sum(1 << pin for pin in BUTTON_PINS_BOARD)  # Bitmask

# Timing constants
DOUBLE_CLICK_TIME = 0.5  # seconds
NOTE_LENGTH_RATIO = 0.25  # Note duration as ratio of step time

# Parameter limits
MIN_BPM, MAX_BPM = 60, 200
MIN_OCTAVE, MAX_OCTAVE = -2, 2
MIN_SEMITONE, MAX_SEMITONE = 0, 12
MIN_VELOCITY, MAX_VELOCITY = 20, 127
MIN_VEL_RANDOM, MAX_VEL_RANDOM = 0, 50

# Colors for settings indicators
COLORS = {
    'off': 0x000000,        # Black - step off
    'playing_off': 0x220000,  # Dim red - current position but step off
    'play_stop': 0x00FF00,   # Green - play/stop control
    'bpm': 0x800080,        # Purple - BPM control
    'octave': 0xFF8000,     # Orange - octave control
    'semitone': 0xFFFF00,   # Yellow - semitone control
    'scale_inactive': 0x404040,  # Dim white - inactive scale categories
    'scale_active': 0x008080,    # Cyan - active scale category
    'velocity': 0xFF0080,   # Hot pink - velocity control
    'vel_random': 0x80FF80,  # Light green - velocity randomization
    'randomize': 0xFF8080,  # Light red - randomize all
}

# External NeoPixel strip setup
external_strip = neopixel.NeoPixel(board.MOSI, NUM_NEOPIXELS, brightness=0.06, auto_write=False)
external_strip.fill(0x000000)
external_strip.show()

# Startup animation
for i in range(NUM_NEOPIXELS):
    external_strip[i] = 0x201500
    time.sleep(0.02)
    external_strip.show()

# RAW MIDI Setup - using direct USB MIDI port
midi_out = usb_midi.ports[1]


def midi_panic():
    """Send MIDI panic - All Notes Off and All Sound Off on all channels"""
    print("Sending MIDI panic...")
    try:
        # Send on all 16 MIDI channels (0-15)
        for channel in range(16):
            # All Notes Off (CC 123): 0xB0 + channel, 123, 0
            midi_out.write(bytes([0xB0 + channel, 123, 0]))
            # All Sound Off (CC 120): 0xB0 + channel, 120, 0
            midi_out.write(bytes([0xB0 + channel, 120, 0]))

        # Small delay to ensure messages are sent
        time.sleep(0.1)
        print("MIDI panic complete")
    except OSError as e:
        print(f"MIDI panic error: {e}")


# Send MIDI panic on startup to clear any stuck notes
midi_panic()

external_strip.fill(0x000000)
external_strip.show()

# I2C and Seesaw setup
i2c = busio.I2C(board.SCL1, board.SDA1, frequency=400000)

# Initialize seesaw boards based on required count
seesaw_boards = []
encoders_per_board = []
switches_per_board = []

for board_idx in range(REQUIRED_BOARDS):
    try:
        board_addr = I2C_ADDRESSES[board_idx]
        seesaw_board = adafruit_seesaw.seesaw.Seesaw(i2c, board_addr)
        seesaw_boards.append(seesaw_board)

        # Setup encoders and switches for this board
        board_encoders = [
            adafruit_seesaw.rotaryio.IncrementalEncoder(seesaw_board, n)
            for n in range(4)
        ]
        board_switches = [
            adafruit_seesaw.digitalio.DigitalIO(seesaw_board, pin)
            for pin in (12, 14, 17, 9)
        ]

        for switch in board_switches:
            switch.switch_to_input(digitalio.Pull.UP)

        encoders_per_board.append(board_encoders)
        switches_per_board.append(board_switches)

        print(f"Initialized board {board_idx+1} at address 0x{board_addr:02X}")

    except OSError as e:
        print(
            f"Failed to initialize board {board_idx+1} "
            f"at address 0x{I2C_ADDRESSES[board_idx]:02X}: {e}"
        )
        raise

# Flatten lists for easier access (only up to STEPS count)
encoders = []
switches = []
for board_encoders, board_switches in zip(encoders_per_board, switches_per_board):
    encoders.extend(board_encoders)
    switches.extend(board_switches)

# Trim to exact step count
encoders = encoders[:STEPS]
switches = switches[:STEPS]


# Step-to-external pixel mapping based on step count
def generate_step_to_pixel_mapping(num_steps, num_pixels):
    """Generate step to pixel mapping based on configuration"""
    if num_steps == 4:
        return [1, 4, 7, 10]
    elif num_steps == 8:
        return [1, 4, 7, 10, 13, 16, 19, 22]
    elif num_steps == 12:
        return [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]
    elif num_steps == 16:
        return [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46]
    else:
        # Fallback: evenly distribute
        step_spacing = num_pixels // num_steps
        return [idx * step_spacing + 1 for idx in range(num_steps)]


STEP_TO_PIXEL = generate_step_to_pixel_mapping(STEPS, NUM_NEOPIXELS)

# Get available scales organized by category
SCALE_CATEGORIES = get_scale_info()
AVAILABLE_SCALES = list_scales()
current_scale_index = 0

# Scale category management
SCALE_CATEGORY_NAMES = list(SCALE_CATEGORIES.keys())
current_scale_categories = {}  # Track current scale index for each category

# Initialize each category's current scale index
for category in SCALE_CATEGORY_NAMES:
    current_scale_categories[category] = 0

# Find the index of the current scale mode
try:
    current_scale_index = AVAILABLE_SCALES.index(SCALE_MODE)
except ValueError:
    current_scale_index = 0
    SCALE_MODE = AVAILABLE_SCALES[0]

# Get the selected scale
SCALE = get_scale(SCALE_MODE)


# Step data - each step has a note and on/off state
class Step:
    """Represents a single step in the sequence"""
    def __init__(self, note=60, active=False):
        self.note = note      # MIDI note number
        self.active = active  # Whether step plays or not


# Initialize steps with notes from the selected scale
def initialize_steps_from_scale(scale, num_steps):
    """Initialize steps with notes from the selected scale"""
    step_list = []
    scale_len = len(scale)

    # Use notes from the middle of the scale (around the 4th octave)
    start_index = scale_len // 3  # Start roughly 1/3 through the scale

    # Create the first 8 ascending notes from the scale
    first_eight_notes = []
    for note_idx in range(8):
        # Cycle through scale notes, wrapping around if needed
        scale_index = (start_index + note_idx) % scale_len
        note = scale[scale_index]
        first_eight_notes.append(note)

    # Initialize steps based on the pattern
    for sequence_step in range(num_steps):
        if sequence_step < 8:
            # First 8 steps: use ascending notes
            note = first_eight_notes[sequence_step]
        else:
            # Steps 9-16: repeat the first 8 notes
            note = first_eight_notes[sequence_step - 8]

        active = True  # All steps start active
        step_list.append(Step(note=note, active=active))

    return step_list


# Initialize steps using the selected scale
steps = initialize_steps_from_scale(SCALE, STEPS)

# Sequencer state
current_step = 0
last_step_time = time.monotonic()
expected_step_time = time.monotonic()  # When step should have happened
last_positions = [0] * STEPS  # Track encoder positions
last_switch_states = [True] * STEPS  # Track switch states
currently_playing_note = None  # keep track of which note is currently playing
note_off_time = 0  # When to send note off
note_length = STEP_TIME * NOTE_LENGTH_RATIO  # Note duration
display_needs_update = False  # Flag to update display

# Global sequencer settings
is_playing = True  # Play/stop state
current_octave = 0  # Octave offset for entire sequence (-2 to +2)
semitone_transpose = 0  # Semitone offset (0 to 12)
velocity_baseline = 100  # Base MIDI velocity (20-127)
velocity_randomization = 0  # Amount of velocity randomization (0-50)

# Settings mode state
settings_mode = False
first_knob_click_time = 0
first_knob_click_count = 0


def get_current_scale_category():
    """Get the category name of the currently active scale"""
    for category_name, scales in SCALE_CATEGORIES.items():
        if SCALE_MODE in scales:
            return category_name
    return None


def get_note_color(note_value):
    """Get color based on note pitch - yellow for low notes, green for high notes"""
    # Using extended range: C1 (24) to B6 (95)
    min_note = 24  # C1
    max_note = 95  # B6

    # Clamp note to range
    note_value = max(min_note, min(max_note, note_value))

    # Calculate ratio (0.0 = lowest note, 1.0 = highest note)
    ratio = (note_value - min_note) / (max_note - min_note)

    # Interpolate from yellow (0xFFFF00) to green (0x00FF00)
    red = int(255 * (1 - ratio))    # 255 -> 0
    green = 255                      # Always 255
    blue = 0                         # Always 0

    return (red << 16) | (green << 8) | blue


# pylint: disable=global-statement
# Global statements are necessary for CircuitPython embedded programming
# to modify module-level sequencer state variables

def update_step_timing():
    """Update step timing when BPM changes"""
    global STEP_TIME, note_length, expected_step_time
    STEP_TIME = 60.0 / BPM / 4  # 16th note timing
    note_length = STEP_TIME * NOTE_LENGTH_RATIO  # Note duration
    # Adjust next expected step time
    expected_step_time = time.monotonic() + STEP_TIME


def update_scale_by_category(category_name, direction):
    """Update scale within a specific category - preserve notes and mutes"""
    global SCALE, SCALE_MODE, steps, display_needs_update, current_scale_categories

    if category_name not in SCALE_CATEGORIES:
        return

    category_scales = SCALE_CATEGORIES[category_name]
    current_idx = current_scale_categories[category_name]

    # Update index with wrapping
    new_idx = (current_idx + direction) % len(category_scales)
    current_scale_categories[category_name] = new_idx

    # Get new scale name
    new_scale_name = category_scales[new_idx]

    # Update the scale
    old_scale = SCALE_MODE
    SCALE_MODE = new_scale_name
    SCALE = get_scale(SCALE_MODE)

    # Adjust existing notes to fit new scale (preserve mute states)
    for step in steps:
        if step.note not in SCALE:
            # Find the nearest higher note in the new scale
            nearest_note = None
            for scale_note in sorted(SCALE):
                if scale_note >= step.note:
                    nearest_note = scale_note
                    break

            # If no higher note found, use the highest note in scale
            if nearest_note is None:
                nearest_note = max(SCALE)

            step.note = nearest_note

    print(f"Scale changed ({category_name}): {old_scale} → {SCALE_MODE}")
    print("Adjusted out-of-scale notes to fit new scale")
    display_needs_update = True


def randomize_all_steps():
    """Randomize all step notes within current octave range and mute states"""
    global steps, display_needs_update

    # Calculate the current octave range based on existing notes
    current_notes = [step.note for step in steps]
    min_current = min(current_notes)
    max_current = max(current_notes)

    # Find the octave that contains most of our current notes
    base_octave = (min_current // 12) * 12
    octave_range = [note for note in SCALE if base_octave <= note <= base_octave + 24]

    # If we don't have enough notes in that range, expand to include current range
    if not octave_range or max(octave_range) < max_current:
        octave_range = [
            note for note in SCALE
            if min_current <= note <= max_current + 12
        ]

    # Fallback: use a reasonable default range if still empty
    if not octave_range:
        # C3 to C5 range
        octave_range = [note for note in SCALE if 48 <= note <= 72]

    for step in steps:
        # Randomize note within the current octave range
        if octave_range:
            random_note = random.choice(octave_range)
            step.note = random_note

        # Randomize mute state (70% chance to be active)
        step.active = random.random() > 0.3

    print(f"Randomized notes w/in range {min(octave_range)}-{max(octave_range)} and mute states")
    display_needs_update = True


def calculate_velocity():
    """Calculate velocity with randomization"""
    if velocity_randomization == 0:
        return velocity_baseline

    # Add random variation
    variation = random.randint(-velocity_randomization, velocity_randomization)
    final_velocity = velocity_baseline + variation

    # Clamp to valid MIDI range
    return max(1, min(127, final_velocity))


# Initialize external strip with step indicators
print("Setting up external strip...")
for display_step_idx in range(STEPS):
    display_pixel_idx = STEP_TO_PIXEL[display_step_idx]

    if steps[display_step_idx].active:
        if display_step_idx == current_step:
            display_color = 0xFF0000  # Red for currently playing
        else:
            display_color = get_note_color(steps[display_step_idx].note)
    else:
        display_color = COLORS['off']

    external_strip[display_pixel_idx] = display_color

external_strip.show()
print("External strip setup complete")


def update_display():
    """Update only external strip for speed"""
    # Clear all pixels first
    external_strip.fill(0x000000)

    # Special handling for settings mode
    if settings_mode:
        # Set settings mode indicators based on knob positions
        external_strip[0] = COLORS['play_stop']   # Pixel 0: Play/Stop (knob 1)
        external_strip[3] = COLORS['bpm']         # Pixel 3: BPM (knob 2)
        external_strip[6] = COLORS['octave']      # Pixel 6: Octave (knob 3)
        external_strip[9] = COLORS['semitone']    # Pixel 9: Semitone (knob 4)

        # Get current scale category for scale indicators
        current_category = get_current_scale_category()

        # Scale category indicators - active one is cyan, others dim white
        if STEPS >= 8:
            # Western scales (knob 5)
            western_color = (
                COLORS['scale_active'] if current_category == "Western"
                else COLORS['scale_inactive']
            )
            external_strip[12] = western_color

            # Middle Eastern scales (knob 6)
            me_color = (
                COLORS['scale_active'] if current_category == "Middle Eastern"
                else COLORS['scale_inactive']
            )
            external_strip[15] = me_color

        if STEPS >= 12:
            # Indonesian scales (knob 7)
            indonesian_color = (
                COLORS['scale_active'] if current_category == "Indonesian"
                else COLORS['scale_inactive']
            )
            external_strip[18] = indonesian_color

            # Japanese scales (knob 8)
            japanese_color = (
                COLORS['scale_active'] if current_category == "Japanese"
                else COLORS['scale_inactive']
            )
            external_strip[21] = japanese_color

            # Indian scales (knob 9)
            indian_color = (
                COLORS['scale_active'] if current_category == "Indian"
                else COLORS['scale_inactive']
            )
            external_strip[24] = indian_color

        if STEPS >= 16:
            # Chinese scales (knob 10)
            chinese_color = (
                COLORS['scale_active'] if current_category == "Chinese"
                else COLORS['scale_inactive']
            )
            external_strip[27] = chinese_color

            # African scales (knob 11)
            african_color = (
                COLORS['scale_active'] if current_category == "African"
                else COLORS['scale_inactive']
            )
            external_strip[30] = african_color

            # Eastern European scales (knob 12)
            ee_color = (
                COLORS['scale_active'] if current_category == "Eastern European"
                else COLORS['scale_inactive']
            )
            external_strip[33] = ee_color

            # Celtic scales (knob 13)
            celtic_color = (
                COLORS['scale_active'] if current_category == "Celtic"
                else COLORS['scale_inactive']
            )
            external_strip[36] = celtic_color

            # Velocity baseline (knob 14)
            external_strip[39] = COLORS['velocity']

            # Velocity randomization (knob 15)
            external_strip[42] = COLORS['vel_random']

            # Randomize all (knob 16)
            external_strip[45] = COLORS['randomize']

    # Update step indicators (normal step pixels remain unchanged)
    for main_step_idx in range(STEPS):
        main_pixel_idx = STEP_TO_PIXEL[main_step_idx]
        if main_step_idx == current_step and is_playing:
            # Current step is always red when playing
            main_color = (
                0xFF0000 if steps[main_step_idx].active
                else COLORS['playing_off']
            )
        elif main_step_idx == current_step and not is_playing:
            # Current step is dim when stopped
            main_color = (
                0x440000 if steps[main_step_idx].active
                else 0x220000
            )
        else:
            # Non-current steps use pitch-based color when active
            final_note = (
                steps[main_step_idx].note + current_octave * 12 +
                semitone_transpose
            )
            main_color = (
                get_note_color(final_note) if steps[main_step_idx].active
                else COLORS['off']
            )
        external_strip[main_pixel_idx] = main_color

    external_strip.show()


def handle_basic_settings(step_id, change):
    """Handle basic settings controls (play/stop, BPM, octave, semitones)"""
    global BPM, current_octave, semitone_transpose, is_playing

    if step_id == 0:
        # Knob 1: Play/Stop
        if change != 0:
            is_playing = not is_playing
            playback_status = 'PLAYING' if is_playing else 'STOPPED'
            print(f"Playback: {playback_status}")

    elif step_id == 1:
        # Knob 2: BPM
        new_bpm = BPM + change
        BPM = max(MIN_BPM, min(MAX_BPM, new_bpm))
        update_step_timing()
        print(f"BPM: {BPM}")

    elif step_id == 2:
        # Knob 3: Octave
        new_octave = current_octave + change
        current_octave = max(MIN_OCTAVE, min(MAX_OCTAVE, new_octave))
        print(f"Octave: {current_octave:+d}")

    elif step_id == 3:
        # Knob 4: Semitones
        new_semitone = semitone_transpose + change
        semitone_transpose = max(MIN_SEMITONE, min(MAX_SEMITONE, new_semitone))
        print(f"Semitones: +{semitone_transpose}")


def handle_scale_settings(step_id, change):
    """Handle scale category controls"""
    scale_categories = {
        4: "Western", 5: "Middle Eastern", 6: "Indonesian", 7: "Japanese",
        8: "Indian", 9: "Chinese", 10: "African", 11: "Eastern European",
        12: "Celtic"
    }
    if step_id in scale_categories:
        update_scale_by_category(scale_categories[step_id], change)


def handle_velocity_settings(step_id, change):
    """Handle velocity and randomization controls"""
    global velocity_baseline, velocity_randomization

    if step_id == 13:
        # Knob 14: Velocity baseline
        new_velocity = velocity_baseline + change * 5  # Increment by 5
        velocity_baseline = max(MIN_VELOCITY, min(MAX_VELOCITY, new_velocity))
        print(f"Velocity baseline: {velocity_baseline}")

    elif step_id == 14:
        # Knob 15: Velocity randomization
        new_vel_random = velocity_randomization + change
        velocity_randomization = max(
            MIN_VEL_RANDOM, min(MAX_VEL_RANDOM, new_vel_random)
        )
        print(f"Velocity randomization: ±{velocity_randomization}")

    elif step_id == 15:
        # Knob 16: Randomize all
        if change != 0:
            randomize_all_steps()


def handle_settings_mode_encoder():
    """Handle encoder input for settings mode with all 16 controls"""
    global last_positions, display_needs_update

    # Check all available encoders for settings
    for settings_board_idx, settings_board_encoders in enumerate(encoders_per_board):
        for encoder_idx, encoder in enumerate(settings_board_encoders):
            step_id = settings_board_idx * 4 + encoder_idx

            if step_id >= STEPS:
                continue

            current_pos = encoder.position

            if current_pos != last_positions[step_id]:
                change = current_pos - last_positions[step_id]

                # Handle different setting categories
                if step_id <= 3:
                    handle_basic_settings(step_id, change)
                elif 4 <= step_id <= 12:
                    handle_scale_settings(step_id, change)
                elif 13 <= step_id <= 15:
                    handle_velocity_settings(step_id, change)

                last_positions[step_id] = current_pos
                display_needs_update = True


def handle_encoder_input_board(board_index):
    """Handle rotary encoder input for a specific board"""
    global last_positions, display_needs_update

    if board_index >= len(encoders_per_board):
        return

    encoder_board_encoders = encoders_per_board[board_index]
    positions = [encoder.position for encoder in encoder_board_encoders]

    for encoder_idx, pos in enumerate(positions):
        step_id = board_index * 4 + encoder_idx

        # Only process if this step exists in our configuration
        if step_id >= STEPS:
            continue

        # Skip all encoders in settings mode (they're handled separately)
        if settings_mode:
            continue

        if pos != last_positions[step_id]:
            # Calculate note change
            note_change = pos - last_positions[step_id]

            # Find current note in scale
            try:
                current_index = SCALE.index(steps[step_id].note)
            except ValueError:
                # If note not in scale, find closest
                current_index = 0
                for scale_idx, note in enumerate(SCALE):
                    if note >= steps[step_id].note:
                        current_index = scale_idx
                        break

            # Apply change and constrain
            new_index = current_index + note_change
            new_index = max(0, min(len(SCALE) - 1, new_index))

            steps[step_id].note = SCALE[new_index]

            # Calculate final note with octave and semitone transpose
            final_note = (
                steps[step_id].note + current_octave * 12 + semitone_transpose
            )
            print(
                f"Step {step_id + 1}: Note {steps[step_id].note} "
                f"(final: {final_note})"
            )
            last_positions[step_id] = pos
            display_needs_update = True


def handle_switch_input_board(board_index):
    """Handle encoder button presses for a specific board using bulk read"""
    global last_switch_states, display_needs_update

    if board_index >= len(seesaw_boards):
        return

    switch_seesaw_board = seesaw_boards[board_index]

    # Bulk read all digital pins from this board
    try:
        digital_bulk = switch_seesaw_board.digital_read_bulk(BUTTON_MASK_BOARD)

        # Process each button on this board
        for encoder_idx, pin in enumerate(BUTTON_PINS_BOARD):
            step_id = board_index * 4 + encoder_idx

            # Only process if this step exists in our configuration
            if step_id >= STEPS:
                continue

            # Skip first knob (step 0) - it's handled separately for double-click
            if step_id == 0:
                continue

            # In settings mode, skip ALL settings control knobs for button presses
            if settings_mode:
                # Still need to update the switch state to prevent false triggers
                current_state = bool(digital_bulk & (1 << pin))
                last_switch_states[step_id] = current_state
                continue

            current_state = bool(digital_bulk & (1 << pin))

            # Detect button press (transition from high to low)
            if not current_state and last_switch_states[step_id]:
                # Normal step toggle (only when not in settings mode)
                steps[step_id].active = not steps[step_id].active
                step_status = 'ON' if steps[step_id].active else 'OFF'
                print(f"Step {step_id + 1}: {step_status}")
                display_needs_update = True

            last_switch_states[step_id] = current_state

    except OSError as e:
        print(f"Bulk read error board {board_index + 1}: {e}")
        # Fallback to individual reads if bulk read fails
        switch_board_switches = switches_per_board[board_index]
        for encoder_idx, board_switch in enumerate(switch_board_switches):
            step_id = board_index * 4 + encoder_idx

            if step_id >= STEPS:
                continue

            # Skip first knob and all settings knobs in settings mode
            if step_id == 0:
                continue

            current_state = board_switch.value

            # In settings mode, skip all control knobs for button presses
            if settings_mode:
                last_switch_states[step_id] = current_state
                continue

            if not current_state and last_switch_states[step_id]:
                steps[step_id].active = not steps[step_id].active
                step_status = 'ON' if steps[step_id].active else 'OFF'
                print(f"Step {step_id + 1}: {step_status}")
                display_needs_update = True
            last_switch_states[step_id] = current_state


def check_first_knob_button():
    """Check first knob button state more frequently for double-click detection"""
    global last_switch_states, settings_mode, first_knob_click_time
    global first_knob_click_count, display_needs_update

    if len(seesaw_boards) == 0:
        return

    try:
        # Read just the first button (pin 12 on first board)
        first_button_state = seesaw_boards[0].digital_read(12)

        # Detect button press (transition from high to low)
        if not first_button_state and last_switch_states[0]:
            button_time = time.monotonic()

            if first_knob_click_count == 0:
                # First click
                first_knob_click_time = button_time
                first_knob_click_count = 1
                print("First knob clicked once")
            elif first_knob_click_count == 1:
                # Check if this is a double-click
                time_diff = button_time - first_knob_click_time
                print(f"Second click detected, time diff: {time_diff:.3f}s")
                if time_diff <= DOUBLE_CLICK_TIME:
                    # Double-click detected - toggle settings mode
                    settings_mode = not settings_mode
                    mode_status = 'ON' if settings_mode else 'OFF'
                    print(f"DOUBLE-CLICK! Settings mode: {mode_status}")
                    if settings_mode:
                        print("Settings mode controls available")
                    display_needs_update = True
                    first_knob_click_count = 0
                else:
                    # Too slow, treat as new first click
                    print("Too slow for double-click, treating as new first click")
                    first_knob_click_time = button_time
                    first_knob_click_count = 1

        last_switch_states[0] = first_button_state

    except OSError as e:
        print(f"Error reading first knob button: {e}")


def check_double_click_timeout():
    """Check for double-click timeout in main loop"""
    global first_knob_click_count, first_knob_click_time
    global settings_mode, display_needs_update

    if first_knob_click_count > 0:
        if time.monotonic() - first_knob_click_time > DOUBLE_CLICK_TIME:
            # Timeout - treat first click as single step toggle (if not in settings mode)
            print("Double-click timeout - treating as single click")
            if not settings_mode:
                steps[0].active = not steps[0].active
                step_status = 'ON' if steps[0].active else 'OFF'
                print(f"Step 1: {step_status}")
                display_needs_update = True
            first_knob_click_count = 0


def play_current_step():
    """Play the current step if it's active using raw MIDI"""
    global currently_playing_note, note_off_time

    # First, turn off any currently playing note
    if currently_playing_note is not None:
        # Raw MIDI Note Off: 0x80 (channel 1), note, velocity 0
        midi_out.write(bytes([0x80, currently_playing_note, 0]))
        currently_playing_note = None

    # Then play the new note if this step is active and we're playing
    if steps[current_step].active and is_playing:
        # Apply octave and semitone transpose to the note
        final_note = steps[current_step].note + current_octave * 12 + semitone_transpose

        # Clamp to valid MIDI range (0-127)
        final_note = max(0, min(127, final_note))

        # Calculate velocity with randomization
        velocity = calculate_velocity()

        # Raw MIDI Note On: 0x90 (channel 1), note, velocity
        midi_out.write(bytes([0x90, final_note, velocity]))
        currently_playing_note = final_note
        note_off_time = time.monotonic() + note_length

    # Determine which board to check based on current step
    # Check I2C inputs only after each board's last step (every 4th step)
    board_to_check = current_step // 4
    step_in_board = current_step % 4

    if step_in_board == 3:  # Last step of a board (0,1,2,3 -> check at 3)
        if board_to_check < len(seesaw_boards):
            # Handle settings mode encoder separately
            if settings_mode:
                handle_settings_mode_encoder()

            # Always handle normal encoder input
            handle_encoder_input_board(board_to_check)
            handle_switch_input_board(board_to_check)


def handle_note_off():
    """Handle note off after specified duration using raw MIDI"""
    global currently_playing_note, note_off_time

    if (currently_playing_note is not None and
            time.monotonic() >= note_off_time):
        # Raw MIDI Note Off: 0x80 (channel 1), note, velocity 0
        midi_out.write(bytes([0x80, currently_playing_note, 0]))
        currently_playing_note = None
        note_off_time = 0


def advance_step():
    """Advance to the next step in the sequence with timing compensation"""
    global current_step, last_step_time, expected_step_time, display_needs_update

    # Only advance if we're playing
    if not is_playing:
        return

    step_time = time.monotonic()

    # Calculate timing error (how late were we?)
    timing_error = step_time - expected_step_time

    # Advance step
    current_step = (current_step + 1) % STEPS
    last_step_time = step_time

    # Set next expected time, compensating for any drift
    expected_step_time += STEP_TIME

    # If we're way behind (more than one step), reset to current time
    if timing_error > STEP_TIME:
        expected_step_time = step_time + STEP_TIME
        print(f"Timing reset - was {timing_error*1000:.1f}ms late")

    # Always update display when step changes (for current step indicator)
    update_display()


# Initialize timing
last_step_time = time.monotonic()
expected_step_time = last_step_time + STEP_TIME

# Initialize display
update_display()
print("MIDI Step Sequencer Started - COMPREHENSIVE SETTINGS MODE")
print(f"{STEPS} steps, single track ({REQUIRED_BOARDS} NeoRotary boards)")
for board_idx, addr in enumerate(I2C_ADDRESSES[:REQUIRED_BOARDS]):
    steps_start = board_idx * 4 + 1
    steps_end = min((board_idx + 1) * 4, STEPS)
    print(f"Board {board_idx+1} (0x{addr:02X}): Steps {steps_start}-{steps_end}")
print("Encoder rotation: Change note pitch for each step")
print("Encoder press: Toggle step on/off")
print("DOUBLE-CLICK first knob: Enter settings mode")
print("Settings mode controls:")
print("  1. Play/Stop  2. BPM  3. Octave  4. Semitones")
print("  5. Western  6. Middle Eastern  7. Indonesian  8. Japanese")
print("  9. Indian  10. Chinese  11. African  12. Eastern European")
print("  13. Celtic  14. Velocity  15. Vel Random  16. Randomize All")
print(f"BPM: {BPM}")
print(f"Octave: {current_octave:+d}")
print(f"Semitones: +{semitone_transpose}")
print(f"Scale: {SCALE_MODE}")
print(f"Velocity: {velocity_baseline} ±{velocity_randomization}")
print(f"Playing: {is_playing}")
print(f"NeoPixels: {NUM_NEOPIXELS}")

# Main loop - MINIMAL for maximum timing precision with compensation
while True:
    current_time = time.monotonic()

    # Handle note off timing (critical timing)
    handle_note_off()

    # Check first knob button frequently for double-click detection
    check_first_knob_button()

    # Check for double-click timeout in main loop (more frequent than I2C reads)
    check_double_click_timeout()

    # Check if it's time for the next step (use expected time for compensation)
    if current_time >= expected_step_time:
        advance_step()
        play_current_step()  # This will handle I2C reads only after each board's 4th step

    # Update display only when needed and only after board transitions
    if display_needs_update and (current_step % 4 == 3):
        update_display()
        display_needs_update = False
