# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# note_manager.py: CircuitPython Music Staff Application component
"""

# pylint: disable=import-error
from displayio import Group, Bitmap, Palette, TileGrid


# pylint: disable=invalid-name,no-member,too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-branches,too-many-statements,protected-access,too-many-locals
# pylint: disable=trailing-whitespace
class NoteManager:
    """Manages notes, their positions, and related data"""

    def __init__(self, start_margin, staff_y_start, line_spacing):
        self.note_data = []  # List of (x_position, y_position, midi_note, midi_channel)
        self.notes_group = Group()
        self.ledger_lines_group = Group()
        self.note_to_ledger = {}  # Mapping from note indices to ledger line indices

        # Key staff parameters
        self.START_MARGIN = start_margin
        self.STAFF_Y_START = staff_y_start
        self.LINE_SPACING = line_spacing

        # Note positions and their MIDI values
        self.note_positions = self._create_note_positions()
        self.x_positions = []  # Will be populated by the UI manager

        # Create note bitmaps
        self.NOTE_WIDTH = (line_spacing // 2) - 2
        self.NOTE_HEIGHT = (line_spacing // 2) - 2
        self.note_bitmap = self._create_note_bitmap()

        # Create ledger line bitmap
        self.ledger_line_width = 14
        self.ledger_line_height = 2
        self.ledger_bitmap = Bitmap(self.ledger_line_width, self.ledger_line_height, 2)
        for x in range(self.ledger_line_width):
            for y in range(self.ledger_line_height):
                self.ledger_bitmap[x, y] = 1

        self.ledger_palette = Palette(2)
        self.ledger_palette[0] = 0x8AAD8A  # Transparent (sage green background)
        self.ledger_palette[1] = 0x000000  # Black for ledger lines

        # MIDI note mapping for each position
        self.midi_notes = {
            0: 59,   # B3
            1: 60,   # C4 (middle C)
            2: 62,   # D4
            3: 64,   # E4
            4: 65,   # F4
            5: 67,   # G4
            6: 69,   # A4
            7: 71,   # B4
            8: 72,   # C5
            9: 74,   # D5
            10: 76,  # E5
            11: 77,  # F5
            12: 79   # G5
        }

        # Map of positions to note names (for treble clef)
        self.note_names = {
            0: "B3",   # B below middle C (ledger line)
            1: "C4",   # Middle C (ledger line below staff)
            2: "D4",   # Space below staff
            3: "E4",   # Bottom line
            4: "F4",   # First space
            5: "G4",   # Second line
            6: "A4",   # Second space
            7: "B4",   # Middle line
            8: "C5",   # Third space
            9: "D5",   # Fourth line
            10: "E5",  # Fourth space
            11: "F5",  # Top line
            12: "G5"   # Space above staff
        }

    def _create_note_positions(self):
        """Create the vertical positions for notes on the staff"""
        note_positions = []

        # Calculate positions from the bottom up
        bottom_line_y = self.STAFF_Y_START + 5 * self.LINE_SPACING  # Bottom staff line (E)

        # B3 (ledger line below staff)
        note_positions.append(bottom_line_y + self.LINE_SPACING + self.LINE_SPACING // 2)

        # Middle C4 (ledger line below staff)
        note_positions.append(bottom_line_y + self.LINE_SPACING)

        # D4 (space below staff)
        note_positions.append(bottom_line_y + self.LINE_SPACING // 2)

        # E4 (bottom line)
        note_positions.append(bottom_line_y)

        # F4 (first space)
        note_positions.append(bottom_line_y - self.LINE_SPACING // 2)

        # G4 (second line)
        note_positions.append(bottom_line_y - self.LINE_SPACING)

        # A4 (second space)
        note_positions.append(bottom_line_y - self.LINE_SPACING - self.LINE_SPACING // 2)

        # B4 (middle line)
        note_positions.append(bottom_line_y - 2 * self.LINE_SPACING)

        # C5 (third space)
        note_positions.append(bottom_line_y - 2 * self.LINE_SPACING - self.LINE_SPACING // 2)

        # D5 (fourth line)
        note_positions.append(bottom_line_y - 3 * self.LINE_SPACING)

        # E5 (fourth space)
        note_positions.append(bottom_line_y - 3 * self.LINE_SPACING - self.LINE_SPACING // 2)

        # F5 (top line)
        note_positions.append(bottom_line_y - 4 * self.LINE_SPACING)

        # G5 (space above staff)
        note_positions.append(bottom_line_y - 4 * self.LINE_SPACING - self.LINE_SPACING // 2)

        return note_positions

    def _create_note_bitmap(self):
        """Create a bitmap for a quarter note (circular shape)"""
        note_bitmap = Bitmap(self.NOTE_WIDTH, self.NOTE_HEIGHT, 2)

        # Draw a circular shape for the note head
        cx = self.NOTE_WIDTH // 2
        cy = self.NOTE_HEIGHT // 2
        radius = self.NOTE_WIDTH // 2

        for y in range(self.NOTE_HEIGHT):
            for x in range(self.NOTE_WIDTH):
                # Use the circle equation (x-cx)² + (y-cy)² ≤ r² to determine if pixel is in circle
                if ((x - cx) ** 2 + (y - cy) ** 2) <= (radius ** 2):
                    note_bitmap[x, y] = 1

        return note_bitmap

    def find_closest_position(self, y):
        """Find the closest valid note position to a given y-coordinate"""
        closest_pos = 0
        min_distance = abs(y - self.note_positions[0])

        for i, pos in enumerate(self.note_positions):
            distance = abs(y - pos)
            if distance < min_distance:
                min_distance = distance
                closest_pos = i

        return closest_pos

    def find_closest_x_position(self, x):
        """Find the closest valid horizontal position"""
        # Only allow positions after the double bar at beginning
        if x < self.START_MARGIN:
            return self.x_positions[0]  # Return first valid position

        closest_x = self.x_positions[0]
        min_distance = abs(x - closest_x)

        for pos in self.x_positions:
            distance = abs(x - pos)
            if distance < min_distance:
                min_distance = distance
                closest_x = pos

        return closest_x

    def note_exists_at_position(self, x_pos, y_pos, mario_head, mario_palette):
        """Check if a note exists at the exact position (for adding new notes)"""
        # Only check for exact overlap, not proximity
        for note_tg in self.notes_group:
            # Check if this is a Mario head note or a regular note
            is_mario = (hasattr(note_tg.pixel_shader, "_palette") and
                        len(note_tg.pixel_shader._palette) > 1 and
                        note_tg.pixel_shader._palette[0] == mario_palette[0])

            if is_mario:
                note_width = mario_head.width
                note_height = mario_head.height
            else:
                note_width = self.NOTE_WIDTH
                note_height = self.NOTE_HEIGHT

            note_x = note_tg.x + note_width // 2
            note_y = note_tg.y + note_height // 2

            # Only prevent notes from being in the exact same position (with a tiny tolerance)
            if abs(note_x - x_pos) < 2 and abs(note_y - y_pos) < 2:
                return True
        return False

    def find_note_at(self, x, y, mario_head, mario_palette):
        """Check if a note already exists at a position and return its index"""
        for i, note_tg in enumerate(self.notes_group):
            # Check if this is a Mario head note or a regular note
            is_mario = (hasattr(note_tg.pixel_shader, "_palette") and
                        len(note_tg.pixel_shader._palette) > 1 and
                        note_tg.pixel_shader._palette[0] == mario_palette[0])

            if is_mario:
                note_width = mario_head.width
                note_height = mario_head.height
            else:
                note_width = self.NOTE_WIDTH
                note_height = self.NOTE_HEIGHT

            # Check if the note's center is within a reasonable distance of the cursor
            note_center_x = note_tg.x + note_width // 2
            note_center_y = note_tg.y + note_height // 2

            # Use a slightly larger hit box for easier clicking
            hit_box_width = max(self.NOTE_WIDTH, note_width)
            hit_box_height = max(self.NOTE_HEIGHT, note_height)

            if (abs(x-note_center_x) < hit_box_width) and (abs(y - note_center_y) < hit_box_height):
                return i
        return None

    def add_note(
        self,
        x,
        y,
        current_channel,
        note_palettes,
        mario_head,
        mario_palette,
        heart_note,
        heart_palette,
        sound_manager
    ):
        """Add a note at the specified position"""
        # Enforce the minimum x position (after the double bar at beginning)
        if x < self.START_MARGIN:
            return (False, "Notes must be after the double bar")

        # Find the closest valid position
        position_index = self.find_closest_position(y)
        y_position = self.note_positions[position_index]

        # Find the closest valid horizontal position
        x_position = self.find_closest_x_position(x)

        # Check if a note already exists at this exact position
        if self.note_exists_at_position(x_position, y_position, mario_head, mario_palette):
            return (False, "Note already exists here")

        # Get the corresponding MIDI note number
        midi_note = self.midi_notes[position_index]

        # Create a TileGrid for the note based on channel
        if current_channel == 0:  # Channel 1 (index 0) uses Mario head
            note_tg = TileGrid(mario_head, pixel_shader=mario_palette)
            # Adjust position offset based on the size of mario_head bitmap
            note_width = mario_head.width
            note_height = mario_head.height
            note_tg.x = x_position - note_width // 2
            note_tg.y = y_position - note_height // 2
        elif current_channel == 1:  # Channel 2 uses Heart note
            note_tg = TileGrid(heart_note, pixel_shader=heart_palette)
            # Adjust position offset based on the size of heart_note bitmap
            note_width = heart_note.width
            note_height = heart_note.height
            note_tg.x = x_position - note_width // 2
            note_tg.y = y_position - note_height // 2
        elif current_channel == 2:  # Channel 3 uses Drum note
            note_tg = TileGrid(mario_head, pixel_shader=mario_palette)
            # Adjust position offset based on the size
            note_width = mario_head.width
            note_height = mario_head.height
            note_tg.x = x_position - note_width // 2
            note_tg.y = y_position - note_height // 2
        elif current_channel in (3, 4, 5):  # Channels 4-6 use custom sprites
            # We'll pass appropriate sprites in ui_manager
            note_tg = TileGrid(mario_head, pixel_shader=mario_palette)
            note_width = mario_head.width
            note_height = mario_head.height
            note_tg.x = x_position - note_width // 2
            note_tg.y = y_position - note_height // 2
        else:  # Other channels use the colored circle
            note_tg = TileGrid(self.note_bitmap, pixel_shader=note_palettes[current_channel])
            note_tg.x = x_position - self.NOTE_WIDTH // 2
            note_tg.y = y_position - self.NOTE_HEIGHT // 2

        # Play the appropriate sound
        sound_manager.play_note(midi_note, current_channel)

        # Add the note to the notes group
        note_index = len(self.notes_group)
        self.notes_group.append(note_tg)

        # Store the note data for playback with channel information
        self.note_data.append((x_position, y_position, midi_note, current_channel))

        # Add a ledger line if it's the B3 or C4 below staff
        if position_index <= 1:  # B3 or C4
            ledger_tg = TileGrid(self.ledger_bitmap, pixel_shader=self.ledger_palette)
            ledger_tg.x = x_position - self.ledger_line_width // 2
            ledger_tg.y = y_position
            ledger_index = len(self.ledger_lines_group)
            self.ledger_lines_group.append(ledger_tg)

            # Track association between note and its ledger line
            self.note_to_ledger[note_index] = ledger_index

        note_name = self.note_names[position_index]
        return (True, f"Added: Ch{current_channel+1} {note_name}")

    def erase_note(self, x, y, mario_head, mario_palette, sound_manager=None):
        """Erase a note at the clicked position"""
        # Try to find a note at the click position
        note_index = self.find_note_at(x, y, mario_head, mario_palette)

        if note_index is not None:
            # Get the position of the note
            note_tg = self.notes_group[note_index]

            # Check if this is a Mario head note or a regular note
            is_mario = (hasattr(note_tg.pixel_shader, "_palette") and
                        len(note_tg.pixel_shader._palette) > 1 and
                        note_tg.pixel_shader._palette[0] == mario_palette[0])

            if is_mario:
                note_width = mario_head.width
                note_height = mario_head.height
            else:
                note_width = self.NOTE_WIDTH
                note_height = self.NOTE_HEIGHT

            note_x = note_tg.x + note_width // 2
            note_y = note_tg.y + note_height // 2

            # Find the corresponding note data
            found_data_index = None
            # found_channel = None  # Unused variable

            for i, (x_pos, y_pos, _midi_note, _channel) in enumerate(self.note_data):
                # Increased tolerance for position matching
                if abs(x_pos - note_x) < 5 and abs(y_pos - note_y) < 5:
                    found_data_index = i
                    break

            # If we found the note data and have a sound manager reference
            if found_data_index is not None and sound_manager is not None:
                # Extract note data
                x_pos, y_pos, _midi_note, channel = self.note_data[found_data_index]

                # If this is a sample-based note (channels 0, 1, or 2), stop it
                if channel in [0, 1, 2]:
                    sound_manager.stop_sample_at_position(x_pos, y_pos, channel)

                # Remove the note data
                self.note_data.pop(found_data_index)
                print(f"Erased note at position ({x_pos}, {y_pos}) ch {channel+1}")
            else:
                # Still remove the note data if found (for backward compatibility)
                if found_data_index is not None:
                    self.note_data.pop(found_data_index)

            # Check if this note has an associated ledger line
            if note_index in self.note_to_ledger:
                ledger_index = self.note_to_ledger[note_index]

                # Remove the ledger line
                self.ledger_lines_group.pop(ledger_index)

                # Update ledger line mappings after removing a ledger line
                new_note_to_ledger = {}

                # Process each mapping
                for n_idx, l_idx in self.note_to_ledger.items():
                    # Skip the note we're removing
                    if n_idx != note_index:
                        # Adjust indices for ledger lines after the removed one
                        if l_idx > ledger_index:
                            new_note_to_ledger[n_idx] = l_idx - 1
                        else:
                            new_note_to_ledger[n_idx] = l_idx

                self.note_to_ledger = new_note_to_ledger

            # Remove the note
            self.notes_group.pop(note_index)

            # Update mappings for notes with higher indices
            new_note_to_ledger = {}
            for n_idx, l_idx in self.note_to_ledger.items():
                if n_idx > note_index:
                    new_note_to_ledger[n_idx - 1] = l_idx
                else:
                    new_note_to_ledger[n_idx] = l_idx

            self.note_to_ledger = new_note_to_ledger

            return (True, "Note erased")

        return (False, "No note found at this position")

    def clear_all_notes(self, sound_manager=None):
        """Clear all notes from the staff"""
        # Stop all sample playback if we have a sound manager
        if sound_manager is not None:
            sound_manager.stop_all_notes()

        # Remove all notes
        while len(self.notes_group) > 0:
            self.notes_group.pop()

        # Remove all ledger lines
        while len(self.ledger_lines_group) > 0:
            self.ledger_lines_group.pop()

        # Clear note data and ledger line mappings
        self.note_data = []
        self.note_to_ledger = {}
