# ui_manager.py
import time
from adafruit_display_text.bitmap_label import Label
import terminalio
from displayio import TileGrid

from display_manager import DisplayManager
from staff_view import StaffView
from control_panel import ControlPanel
from input_handler import InputHandler
from sprite_manager import SpriteManager
from cursor_manager import CursorManager
from playback_controller import PlaybackController

class UIManager:
    """Manages the UI elements, input, and user interaction"""

    def __init__(self, sound_manager, note_manager):
        self.sound_manager = sound_manager
        self.note_manager = note_manager

        # Screen dimensions
        self.SCREEN_WIDTH = 320
        self.SCREEN_HEIGHT = 240

        # Staff dimensions
        self.TOP_MARGIN = int(self.SCREEN_HEIGHT * 0.1)
        self.BOTTOM_MARGIN = int(self.SCREEN_HEIGHT * 0.2)
        self.STAFF_HEIGHT = int((self.SCREEN_HEIGHT - self.TOP_MARGIN - self.BOTTOM_MARGIN) * 0.95)
        self.STAFF_Y_START = self.TOP_MARGIN
        self.LINE_SPACING = self.STAFF_HEIGHT // 8

        # Start margin
        self.START_MARGIN = 25

        # Tempo and timing
        self.BPM = 120
        self.SECONDS_PER_BEAT = 60 / self.BPM
        self.SECONDS_PER_EIGHTH = self.SECONDS_PER_BEAT / 2

        # Initialize components
        self.display_manager = DisplayManager(self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        self.staff_view = StaffView(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, self.note_manager)
        self.control_panel = ControlPanel(self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        self.input_handler = InputHandler(self.SCREEN_WIDTH, self.SCREEN_HEIGHT,
                                         self.STAFF_Y_START, self.STAFF_HEIGHT)
        self.sprite_manager = SpriteManager()
        self.cursor_manager = CursorManager()
        self.playback_controller = PlaybackController(self.sound_manager, self.note_manager,
                                                     self.SECONDS_PER_EIGHTH)

        # UI elements
        self.main_group = None
        self.note_name_label = None
        self.tempo_label = None
        self.preview_tg = None
        self.highlight_grid = None
        self.playhead = None
        self.channel_buttons = []
        self.channel_selector = None

        # Channel setting
        self.current_channel = 0

    def setup_display(self):
        """Initialize the display and create visual elements"""
        # Initialize display
        self.main_group, self.display = self.display_manager.initialize_display()

        # Create background
        bg_grid = self.display_manager.create_background()
        self.main_group.append(bg_grid)

        # Create staff
        staff_group = self.staff_view.create_staff()
        self.main_group.append(staff_group)

        # Create grid lines
        grid_tg = self.staff_view.create_grid_lines()
        self.main_group.insert(1, grid_tg)  # Insert before staff so it appears behind

        # Create channel buttons using sprites
        self._create_sprite_channel_buttons()

        # Create transport controls
        transport_group, self.play_button, self.stop_button, self.loop_button, self.clear_button = \
            self.control_panel.create_transport_controls(self.sprite_manager)
        self.main_group.append(transport_group)

        # Create cursors
        self.crosshair_cursor, self.triangle_cursor = self.cursor_manager.create_cursors()
        self.main_group.append(self.crosshair_cursor)
        self.main_group.append(self.triangle_cursor)

        # Create note name label
        self._create_note_name_label()

        # Create tempo display
        self._create_tempo_display()

        # Create highlight
        self.highlight_grid = self.staff_view.create_highlight()
        self.main_group.append(self.highlight_grid)

        # Create playhead
        self.playhead = self.staff_view.create_playhead()
        self.main_group.append(self.playhead)

        # Set playback controller elements
        self.playback_controller.set_ui_elements(
            self.playhead,
            self.play_button,
            self.stop_button,
            self.control_panel.button_sprites
        )

        # Create preview note
        self.preview_tg = self.sprite_manager.create_preview_note(
            self.current_channel, self.note_manager.note_bitmap)
        self.main_group.append(self.preview_tg)

        # Add note groups to main group
        self.main_group.append(self.note_manager.notes_group)
        self.main_group.append(self.note_manager.ledger_lines_group)

    def _create_sprite_channel_buttons(self):
        """Create channel buttons using sprites instead of numbered boxes"""
        # Get a reference to the channel selector from control panel
        channel_group, self.channel_selector = self.control_panel.create_channel_buttons()

        # Add sprite-based channel buttons
        button_sprites = [
            (self.sprite_manager.mario_head, self.sprite_manager.mario_palette),
            (self.sprite_manager.heart_note, self.sprite_manager.heart_palette),
            (self.sprite_manager.drum_note, self.sprite_manager.drum_palette),
            (self.sprite_manager.meatball_note, self.sprite_manager.meatball_palette),
            (self.sprite_manager.star_note, self.sprite_manager.star_palette),
            (self.sprite_manager.bot_note, self.sprite_manager.bot_palette)
        ]

        # Create and position the sprite buttons
        self.channel_buttons = []

        for i, (sprite, palette) in enumerate(button_sprites):
            button_x = 10 + i * (self.control_panel.CHANNEL_BUTTON_SIZE +
                               self.control_panel.CHANNEL_BUTTON_SPACING)

            # Create TileGrid for the sprite
            button_tg = TileGrid(sprite, pixel_shader=palette,
                               x=button_x, y=self.control_panel.CHANNEL_BUTTON_Y)

            # Center the sprite if it's not exactly the button size
            if sprite.width != self.control_panel.CHANNEL_BUTTON_SIZE:
                offset_x = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite.width) // 2
                button_tg.x += offset_x

            if sprite.height != self.control_panel.CHANNEL_BUTTON_SIZE:
                offset_y = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite.height) // 2
                button_tg.y += offset_y

            self.channel_buttons.append(button_tg)
            channel_group.append(button_tg)

        # Add the channel_group to main_group
        self.main_group.append(channel_group)

    def _create_note_name_label(self):
        """Create a label to show the current note name"""
        self.note_name_label = Label(
            terminalio.FONT,
            text="",
            color=0x000000,  # Black text for beige background
            scale=1
        )
        self.note_name_label.anchor_point = (0, 0)
        self.note_name_label.anchored_position = (10, self.SCREEN_HEIGHT - 70)
        self.main_group.append(self.note_name_label)

    def _create_tempo_display(self):
        """Create a label for the tempo display with + and - buttons"""
        import gc
        gc.collect()  # Force garbage collection before creating the label

        # Create plus and minus buttons for tempo adjustment
        self.tempo_minus_label = Label(
            terminalio.FONT,
            text="-",
            color=0xaaaaaa,  # White text
            background_color=0x444444,  # Dark gray background
            scale=1
        )
        self.tempo_minus_label.anchor_point = (0.5, 0.5)
        self.tempo_minus_label.anchored_position = (self.SCREEN_WIDTH - 24, 10)
        self.main_group.append(self.tempo_minus_label)

        self.tempo_plus_label = Label(
            terminalio.FONT,
            text="+",
            color=0xaaaaaa,  # gray text
            background_color=0x444444,  # Dark gray background
            scale=1
        )
        self.tempo_plus_label.anchor_point = (0.5, 0.5)
        self.tempo_plus_label.anchored_position = (self.SCREEN_WIDTH - 7, 10)
        self.main_group.append(self.tempo_plus_label)

        # Create the tempo display label
        self.tempo_label = Label(
            terminalio.FONT,
            text=f"Tempo: {self.BPM} BPM",
            color=0x222222,  # gray text
            scale=1
        )
        self.tempo_label.anchor_point = (0, 0.5)
        self.tempo_label.anchored_position = (self.SCREEN_WIDTH - 114, 10)
        self.main_group.append(self.tempo_label)

        print(f"Created tempo display: {self.tempo_label.text}")

    def find_mouse(self):
        """Find the mouse device"""
        return self.input_handler.find_mouse()

    def change_channel(self, channel_idx):
        """Change the current MIDI channel"""
        if 0 <= channel_idx < 6:  # Ensure valid channel index
            self.current_channel = channel_idx

            # Update channel selector position
            self.channel_selector.x = 7 + channel_idx * (self.control_panel.CHANNEL_BUTTON_SIZE +
                                                        self.control_panel.CHANNEL_BUTTON_SPACING)

            # Update preview note color/image based on channel
            self.main_group.remove(self.preview_tg)
            self.preview_tg = self.sprite_manager.create_preview_note(
                self.current_channel, self.note_manager.note_bitmap)
            self.main_group.append(self.preview_tg)

            # Update status text
            channel_names = ["Lars", "Heart", "Drum", "Meatball", "Star", "Bot"]
            self.note_name_label.text = f"Channel {self.current_channel + 1}: {channel_names[self.current_channel]} selected"

            print(f"Changed to MIDI channel {self.current_channel + 1}")

    def toggle_loop(self):
        """Toggle loop button state"""
        self.playback_controller.loop_enabled = not self.playback_controller.loop_enabled
        self.control_panel.loop_enabled = self.playback_controller.loop_enabled

        # Update loop button appearance using bitmap if button_sprites are available
        if hasattr(self.control_panel, 'button_sprites') and self.control_panel.button_sprites is not None:
            loop_bitmap, loop_palette = self.control_panel.button_sprites['loop']['down' if self.playback_controller.loop_enabled else 'up']
            self.loop_button.bitmap = loop_bitmap
            self.loop_button.pixel_shader = loop_palette
        else:
            # Fallback to original implementation
            for x in range(1, self.control_panel.BUTTON_WIDTH - 1):
                for y in range(1, self.control_panel.BUTTON_HEIGHT - 1):
                    if (x, y) not in [(0, 0), (0, self.control_panel.BUTTON_HEIGHT-1),
                                     (self.control_panel.BUTTON_WIDTH-1, 0),
                                     (self.control_panel.BUTTON_WIDTH-1, self.control_panel.BUTTON_HEIGHT-1)]:
                        # Skip pixels that are part of the loop symbol
                        dx = x - self.control_panel.BUTTON_WIDTH // 2
                        dy = y - self.control_panel.BUTTON_HEIGHT // 2
                        is_on_circle = self.control_panel.loop_radius - 1 <= (dx*dx + dy*dy)**0.5 <= self.control_panel.loop_radius + 1

                        is_arrow = (x == (self.control_panel.BUTTON_WIDTH // 2 +
                                         int(self.control_panel.loop_radius * 0.7) - 0) and
                                   (y == self.control_panel.BUTTON_HEIGHT // 2 -
                                    self.control_panel.loop_radius - 1 + 0 or
                                    y == self.control_panel.BUTTON_HEIGHT // 2 -
                                    self.control_panel.loop_radius - 1 - 0 + 2))

                        if not (is_on_circle or is_arrow):
                            self.control_panel.loop_button_bitmap[x, y] = 2 if self.playback_controller.loop_enabled else 0

        self.note_name_label.text = "Loop: " + ("ON" if self.playback_controller.loop_enabled else "OFF")

    def press_clear_button(self):
        """Handle clear button pressing effect"""
        # Show pressed state
        if hasattr(self.control_panel, 'button_sprites') and self.control_panel.button_sprites is not None:
            self.clear_button.bitmap = self.control_panel.button_sprites['clear']['down'][0]
            self.clear_button.pixel_shader = self.control_panel.button_sprites['clear']['down'][1]
        else:
            # Fallback to original implementation
            for x in range(1, self.control_panel.BUTTON_WIDTH - 1):
                for y in range(1, self.control_panel.BUTTON_HEIGHT - 1):
                    self.control_panel.clear_button_bitmap[x, y] = 2  # Red

        # Small delay for visual feedback
        time.sleep(0.1)

        # Return to up state
        if hasattr(self.control_panel, 'button_sprites') and self.control_panel.button_sprites is not None:
            self.clear_button.bitmap = self.control_panel.button_sprites['clear']['up'][0]
            self.clear_button.pixel_shader = self.control_panel.button_sprites['clear']['up'][1]
        else:
            # Fallback to original implementation
            for x in range(1, self.control_panel.BUTTON_WIDTH - 1):
                for y in range(1, self.control_panel.BUTTON_HEIGHT - 1):
                    self.control_panel.clear_button_bitmap[x, y] = 0  # Gray

    def clear_all_notes(self):
        """Clear all notes"""
        # Stop playback if it's running
        if self.playback_controller.is_playing:
            self.playback_controller.stop_playback()

        # Visual feedback for button press
        self.press_clear_button()

        # Clear notes using note manager
        self.note_manager.clear_all_notes(self.sound_manager)

        self.note_name_label.text = "All notes cleared"

    def adjust_tempo(self, direction):
        """Adjust the tempo based on button press"""
        # direction should be +1 for increase, -1 for decrease

        # Adjust BPM
        new_bpm = self.BPM + (direction * 5)  # Change by 5 BPM increments

        # Constrain to valid range
        new_bpm = max(40, min(280, new_bpm))

        # Only update if changed
        if new_bpm != self.BPM:
            self.BPM = new_bpm
            self.SECONDS_PER_BEAT = 60 / self.BPM
            self.SECONDS_PER_EIGHTH = self.SECONDS_PER_BEAT / 2

            # Update playback controller with new tempo
            self.playback_controller.set_tempo(self.SECONDS_PER_EIGHTH)

            # Update display
            self.tempo_label.text = f"Tempo: {self.BPM} BPM"

            print(f"Tempo adjusted to {self.BPM} BPM")

    def handle_mouse_position(self):
        """Handle mouse movement and cursor updates"""
        mouse_x = self.input_handler.mouse_x
        mouse_y = self.input_handler.mouse_y

        # Check if mouse is over channel buttons area
        is_over_channel_buttons = (self.control_panel.CHANNEL_BUTTON_Y <= mouse_y <=
                                  self.control_panel.CHANNEL_BUTTON_Y +
                                  self.control_panel.CHANNEL_BUTTON_SIZE)

        # Check if we're over the staff area or transport controls area
        is_over_staff = self.input_handler.is_over_staff(mouse_y)
        is_over_transport = (mouse_y >= self.control_panel.TRANSPORT_AREA_Y)

        # Switch cursor based on area
        self.cursor_manager.switch_cursor(use_triangle=(is_over_transport or is_over_channel_buttons))
        self.cursor_manager.set_cursor_position(mouse_x, mouse_y)

        # Only update highlight and preview if over staff area
        if is_over_staff:
            # Find closest position and update highlight
            closest_pos = self.note_manager.find_closest_position(mouse_y)
            y_position = self.note_manager.note_positions[closest_pos]
            self.highlight_grid.y = y_position - 1  # Center the highlight
            self.highlight_grid.hidden = False

            # Find closest horizontal position (enforce minimum x position)
            x_position = self.note_manager.find_closest_x_position(mouse_x)

            # Update preview note position
            if self.current_channel == 0:  # Adjust for Lars note
                self.preview_tg.x = x_position - self.sprite_manager.mario_head.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.mario_head.height // 2
            elif self.current_channel == 1:  # Adjust for Heart note
                self.preview_tg.x = x_position - self.sprite_manager.heart_note.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.heart_note.height // 2
            elif self.current_channel == 2:  # Adjust for Drum note
                self.preview_tg.x = x_position - self.sprite_manager.drum_note.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.drum_note.height // 2
            elif self.current_channel == 3:  # Adjust for Meatball note
                self.preview_tg.x = x_position - self.sprite_manager.meatball_note.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.meatball_note.height // 2
            elif self.current_channel == 4:  # Adjust for Star note
                self.preview_tg.x = x_position - self.sprite_manager.star_note.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.star_note.height // 2
            elif self.current_channel == 5:  # Adjust for Bot note
                self.preview_tg.x = x_position - self.sprite_manager.bot_note.width // 2
                self.preview_tg.y = y_position - self.sprite_manager.bot_note.height // 2
            else:  # Regular note
                self.preview_tg.x = x_position - self.note_manager.NOTE_WIDTH // 2
                self.preview_tg.y = y_position - self.note_manager.NOTE_HEIGHT // 2

            self.preview_tg.hidden = False

            # Update note name label
            if x_position < self.START_MARGIN:
                self.note_name_label.text = "Invalid position - after double bar only"
            else:
                channel_names = ["Lars", "Heart", "Drum", "Meatball", "Star", "Bot"]
                self.note_name_label.text = f"Ch{self.current_channel+1} ({channel_names[self.current_channel]}): {self.note_manager.note_names[closest_pos]}"
        else:
            # Hide highlight and preview when not over staff
            self.highlight_grid.hidden = True
            self.preview_tg.hidden = True

            # Show channel info if over channel buttons
            if is_over_channel_buttons:
                # Calculate which channel button we're over (if any)
                for i in range(6):
                    button_x = 10 + i * (self.control_panel.CHANNEL_BUTTON_SIZE +
                                        self.control_panel.CHANNEL_BUTTON_SPACING)

                    # Get the actual sprite dimensions for better hit detection
                    if i == 0:
                        sprite_width = self.sprite_manager.mario_head.width
                        sprite_height = self.sprite_manager.mario_head.height
                    elif i == 1:
                        sprite_width = self.sprite_manager.heart_note.width
                        sprite_height = self.sprite_manager.heart_note.height
                    elif i == 2:
                        sprite_width = self.sprite_manager.drum_note.width
                        sprite_height = self.sprite_manager.drum_note.height
                    elif i == 3:
                        sprite_width = self.sprite_manager.meatball_note.width
                        sprite_height = self.sprite_manager.meatball_note.height
                    elif i == 4:
                        sprite_width = self.sprite_manager.star_note.width
                        sprite_height = self.sprite_manager.star_note.height
                    elif i == 5:
                        sprite_width = self.sprite_manager.bot_note.width
                        sprite_height = self.sprite_manager.bot_note.height

                    # Calculate the centered position of the sprite
                    offset_x = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite_width) // 2
                    offset_y = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite_height) // 2
                    sprite_x = button_x + offset_x
                    sprite_y = self.control_panel.CHANNEL_BUTTON_Y + offset_y

                    # Check if mouse is over the sprite
                    if self.input_handler.point_in_rect(
                            mouse_x, mouse_y, sprite_x, sprite_y,
                            sprite_width, sprite_height):
                        channel_names = ["Lars", "Heart", "Drum", "Meatball", "Star", "Bot"]
                        self.note_name_label.text = f"Channel {i+1}: {channel_names[i]}"
                        break

    def handle_mouse_buttons(self):
        """Handle mouse button presses"""
        mouse_x = self.input_handler.mouse_x
        mouse_y = self.input_handler.mouse_y

        # Check for staff area
        is_over_staff = self.input_handler.is_over_staff(mouse_y)

        if self.input_handler.left_button_pressed:
            # Check for tempo button clicks
            minus_button_x, minus_button_y = self.tempo_minus_label.anchored_position
            plus_button_x, plus_button_y = self.tempo_plus_label.anchored_position
            button_radius = 8  # Allow a bit of space around the button for easier clicking

            if ((mouse_x - minus_button_x)**2 + (mouse_y - minus_button_y)**2) < button_radius**2:
                # Clicked minus button - decrease tempo
                self.adjust_tempo(-1)
                return

            if ((mouse_x - plus_button_x)**2 + (mouse_y - plus_button_y)**2) < button_radius**2:
                # Clicked plus button - increase tempo
                self.adjust_tempo(1)
                return

            # Check if a channel button was clicked
            channel_clicked = False
            for i in range(6):
                button_x = 10 + i * (self.control_panel.CHANNEL_BUTTON_SIZE +
                                    self.control_panel.CHANNEL_BUTTON_SPACING)

                # Get the actual sprite dimensions for better hit detection
                if i == 0:
                    sprite_width = self.sprite_manager.mario_head.width
                    sprite_height = self.sprite_manager.mario_head.height
                elif i == 1:
                    sprite_width = self.sprite_manager.heart_note.width
                    sprite_height = self.sprite_manager.heart_note.height
                elif i == 2:
                    sprite_width = self.sprite_manager.drum_note.width
                    sprite_height = self.sprite_manager.drum_note.height
                elif i == 3:
                    sprite_width = self.sprite_manager.meatball_note.width
                    sprite_height = self.sprite_manager.meatball_note.height
                elif i == 4:
                    sprite_width = self.sprite_manager.star_note.width
                    sprite_height = self.sprite_manager.star_note.height
                elif i == 5:
                    sprite_width = self.sprite_manager.bot_note.width
                    sprite_height = self.sprite_manager.bot_note.height

                # Calculate the centered position of the sprite
                offset_x = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite_width) // 2
                offset_y = (self.control_panel.CHANNEL_BUTTON_SIZE - sprite_height) // 2
                sprite_x = button_x + offset_x
                sprite_y = self.control_panel.CHANNEL_BUTTON_Y + offset_y

                # Check if click is within the sprite area
                if self.input_handler.point_in_rect(
                        mouse_x, mouse_y, sprite_x, sprite_y,
                        sprite_width, sprite_height):
                    self.change_channel(i)
                    channel_clicked = True
                    break

            if not channel_clicked:
                # Handle play/stop button clicks
                if self.input_handler.point_in_rect(
                        mouse_x, mouse_y, self.play_button.x, self.play_button.y,
                        self.control_panel.BUTTON_WIDTH, self.control_panel.BUTTON_HEIGHT):
                    if not self.playback_controller.is_playing:
                        self.playback_controller.start_playback(self.START_MARGIN)
                    else:
                        self.playback_controller.stop_playback()
                elif self.input_handler.point_in_rect(
                        mouse_x, mouse_y, self.stop_button.x, self.stop_button.y,
                        self.control_panel.BUTTON_WIDTH, self.control_panel.BUTTON_HEIGHT):
                    self.playback_controller.stop_playback()
                elif self.input_handler.point_in_rect(
                        mouse_x, mouse_y, self.loop_button.x, self.loop_button.y,
                        self.control_panel.BUTTON_WIDTH, self.control_panel.BUTTON_HEIGHT):
                    self.toggle_loop()
                elif self.input_handler.point_in_rect(
                        mouse_x, mouse_y, self.clear_button.x, self.clear_button.y,
                        self.control_panel.BUTTON_WIDTH, self.control_panel.BUTTON_HEIGHT):
                    self.clear_all_notes()
                # Handle staff area clicks - left button adds notes only
                elif is_over_staff:
                    if self.current_channel == 0:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.mario_head, self.sprite_manager.mario_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )


                    elif self.current_channel == 1:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    elif self.current_channel == 2:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.drum_note, self.sprite_manager.drum_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    elif self.current_channel == 3:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.meatball_note, self.sprite_manager.meatball_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    elif self.current_channel == 4:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.star_note, self.sprite_manager.star_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    elif self.current_channel == 5:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.bot_note, self.sprite_manager.bot_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    else:
                        success, message = self.note_manager.add_note(
                            mouse_x, mouse_y, self.current_channel,
                            self.sprite_manager.note_palettes,
                            self.sprite_manager.mario_head, self.sprite_manager.mario_palette,
                            self.sprite_manager.heart_note, self.sprite_manager.heart_palette,
                            self.sound_manager
                        )
                    self.note_name_label.text = message

        # Handle right mouse button for note deletion
        elif self.input_handler.right_button_pressed and is_over_staff:
            success, message = self.note_manager.erase_note(
                mouse_x, mouse_y,
                self.sprite_manager.mario_head, self.sprite_manager.mario_palette,
                self.sound_manager
            )
            self.note_name_label.text = message

    def main_loop(self):
        """Main application loop"""
        while True:
            # Update playback if active
            if self.playback_controller.is_playing:
                self.playback_controller.update_playback(self.staff_view.x_positions)

            # Update sound manager for timed releases
            self.sound_manager.update()

            # Process mouse input - simplified version without wheel tracking
            if self.input_handler.process_mouse_input():
                # Handle mouse position and update cursor
                self.handle_mouse_position()

                # Handle mouse button presses
                self.handle_mouse_buttons()
