# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

# Based on https://github.com/Lumon-Industries/Macrodata-Refinement
# JavaScript project

import json
import os
import math
import hashlib
import shutil
import time
import random
import tkinter as tk
from PIL import Image, ImageTk, ImageFont, ImageDraw
from data import DataNumber
from data_bin import Bin
from palette import Palette
try: # blinka with haptics?
    import board
    import busio
    import adafruit_drv2605
except NotImplementedError:
    pass

TOTAL_REFINEMENT_GOAL = 250 # how many numbers to refine?
LOCATION = "Cold Harbor"

def get_username():
    try:
        username = os.environ.get('USER')
        if username:
            return username
        username = os.environ.get('LOGNAME')
        if username:
            return username
        username = os.environ.get('USERNAME')
        if username:
            return username
    except Exception:
        pass
    return "Mark S."
# pylint: disable=too-many-branches,too-many-lines,broad-except,unused-argument
# pylint: disable=too-many-statements,too-many-locals,too-many-public-methods,too-many-nested-blocks
class MacrodataRefinementTerminal:
    def __init__(self, username=None, location=LOCATION):
        self.palette = Palette()
        if username is None:
            username = get_username()
        # game settings
        self.username = username
        self.location = location
        self.completion = 0
        self.total_goal = TOTAL_REFINEMENT_GOAL
        self.total_refined = 0
        self.image_path = f"/home/{self.username}/lumon-logo.png"
        self.logo_img = Image.open(f"/home/{self.username}/lumon-logo-small.png")

        # graphics
        self.root = tk.Tk()
        self.root.title("Lumon MDR Terminal")
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<q>", self.exit_program)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_program)
        self.root.focus_force()
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            bg=self.palette.BG,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        try:
            self.image = Image.open(self.image_path)
            self.photo = ImageTk.PhotoImage(self.image)
            self.canvas_image = self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        except Exception as e:
            print(f"Error loading image: {e}")
            self.canvas_image = None
        self.screen = 1
        # macrodata settings
        self.completion_message_elements = {}
        self.x_pos, self.y_pos = 100, 100
        self.x_speed, self.y_speed = 2, 2
        self.base_size = 24
        self.number_spacing = 50
        self.margin = 80
        self.data_numbers = []
        self.ui_elements = {}
        self.selection_start = None
        self.selection_rect = None
        self.selection_active = False
        self.wiggle_numbers = []
        self.wiggle_timer = 0
        self.wiggle_interval = 600
        self.wiggle_amplitude = 2.0
        self.wiggle_speed = 0.2
        self.wiggle_phase = 0
        self.wiggle_phase_x = 0.0
        self.wiggle_phase_y = 0.0
        self.wiggle_phase_rotation = 0.0
        self.numbers_need_selection = False
        self.waiting_for_next_wiggle = False
        self.next_wiggle_timer = 0
        self.next_wiggle_delay = 210
        self.base_wiggle_amplitude = 1.5
        self.max_wiggle_amplitude = 10.0
        self.proximity_threshold = 350
        self.wiggle_speed_x = 0.058
        self.wiggle_speed_y = 0.047
        self.wiggle_speed_rotation = 0.02
        self.glow_step = 0
        self.fade_step = 0
        self.fade_timer = 0
        self.max_fade_steps = 20
        self.completion_photo = 0
        self.completion_triggered = False

        # mouse settings
        self.mouse_x = 0
        self.mouse_y = 0
        self.canvas.bind("<Motion>", self.track_mouse)
        self.bins = []
        self.canvas.bind("<Button-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        self.root.bind("<Button-3>", self.toggle_screen)
        # start program & autosave
        self.animate()
        self.setup_autosave(interval=300)
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.drv = adafruit_drv2605.DRV2605(self.i2c)
            self.haptic_enabled = True
            self.effect_level = 0
            self.haptic_effects = {
                0: 0,
                1: 9,
                2: 13,
                3: 47,
            }
            print("Haptic feedback initialized")
        except Exception as e:
            print(f"Haptic initialization error: {e}")
            self.haptic_enabled = False

    def update_haptic_intensity(self, proximity_factor):
        if not self.haptic_enabled:
            return

        if proximity_factor < 0.1:
            self.effect_level = 0
        elif proximity_factor < 0.4:
            self.effect_level = 1
        elif proximity_factor < 0.7:
            self.effect_level = 2
        else:
            self.effect_level = 3

        if self.effect_level == 0:
            self.drv.stop()
        else:
            effect_id = self.haptic_effects[self.effect_level]
            self.drv.sequence[0] = adafruit_drv2605.Effect(effect_id)
            self.drv.play()

    def track_mouse(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def apply_mouse_avoidance(self, number):
        """
        Apply an avoidance effect where numbers move away from the mouse cursor
        """
        if not hasattr(number, 'mouse_offset_x'):
            number.mouse_offset_x = 0
        if not hasattr(number, 'mouse_offset_y'):
            number.mouse_offset_y = 0
        if self.screen != 2 or number.bin_it:
            return
        dx = number.x - self.mouse_x
        dy = number.y - self.mouse_y
        distance = math.sqrt(dx*dx + dy*dy)
        avoidance_radius = 100
        max_repel_distance = 12
        if distance < avoidance_radius:
            normalized_distance = 1.0 - (distance / avoidance_radius)
            repel_factor = normalized_distance * normalized_distance * 0.8
            repel_distance = max_repel_distance * repel_factor
            if distance > 0.1:
                repel_x = (dx / distance) * repel_distance
                repel_y = (dy / distance) * repel_distance
            else:
                angle = random.uniform(0, 2 * math.pi)
                repel_x = math.cos(angle) * repel_distance
                repel_y = math.sin(angle) * repel_distance
            number.mouse_offset_x = repel_x
            number.mouse_offset_y = repel_y
        else:
            if hasattr(number, 'mouse_offset_x') and number.mouse_offset_x != 0:
                number.mouse_offset_x *= 0.95
                if abs(number.mouse_offset_x) < 0.05:
                    number.mouse_offset_x = 0
            if hasattr(number, 'mouse_offset_y') and number.mouse_offset_y != 0:
                number.mouse_offset_y *= 0.95
                if abs(number.mouse_offset_y) < 0.05:
                    number.mouse_offset_y = 0

    def generate_serial_number(self, username):
        """
        Generate a Severance-style serial number based on the username.
        Format: 0xAAAAAA : 0xBBBBBB where A and B are hex values derived from username.
        """
        username_bytes = username.encode('utf-8')
        first_hex = 0
        for i in range(min(3, len(username_bytes))):
            first_hex = (first_hex << 8) | username_bytes[i]
        second_hex = 0
        if len(username_bytes) > 3:
            remaining_bytes = username_bytes[3:]
            for i, byte in enumerate(remaining_bytes):
                second_hex ^= (byte << (8 * (i % 3)))
        else:
            hash_obj = hashlib.md5(username_bytes)
            digest = hash_obj.digest()
            second_hex = int.from_bytes(digest[:3], byteorder='big')
        serial = f"0x{first_hex:06X} : 0x{second_hex:06X}"
        return serial

    def save_progress(self, filepath=None):
        """
        Save the current progress and bin data to a JSON file.
        """
        if self.screen != 2 or not self.bins:
            return False
        if filepath is None:
            save_dir = f"/home/{self.username}/mdr_saves/"
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, f"mdr_{self.location.lower()}.json")
        try:
            save_data = {
                "timestamp": int(time.time()),
                "username": self.username,
                "location": self.location,
                "completion": self.completion,
                "total_goal": self.total_goal,
                "total_refined": self.total_refined,
                "bins": []
            }
            for bin_idx, bin_obj in enumerate(self.bins):
                bin_data = {
                    "bin_id": bin_idx,
                    "levels": bin_obj.levels,
                    "last_refined_time": bin_obj.last_refined_time
                }
                save_data["bins"].append(bin_data)
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            print(f"Progress autosaved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving progress: {str(e)}")
            return False

    def load_progress(self, filepath=None):
        """
        Load progress and bin data from a JSON file.
        Verifies that the saved total goal matches the current total goal,
        otherwise starts a new save.
        """
        if filepath is None:
            filepath = os.path.join(f"/home/{self.username}/mdr_saves/",
                                    f"mdr_{self.location.lower()}.json")
        if not os.path.exists(filepath):
            print(f"Save file {filepath} not found")
            return False
        try:
            with open(filepath, 'r') as f:
                save_data = json.load(f)
            required_keys = ["timestamp", "username", "location", "completion", "bins"]
            for key in required_keys:
                if key not in save_data:
                    print(f"Invalid save file: missing '{key}' field")
                    return False
            if "total_goal" in save_data:
                saved_goal = save_data["total_goal"]
                if saved_goal != TOTAL_REFINEMENT_GOAL:
                    print("Starting fresh with new refinement goal")
                    backup_path = filepath + f".goal_{saved_goal}.bak"
                    try:
                        shutil.copy2(filepath, backup_path)
                        print(f"Created backup of old save at {backup_path}")
                    except Exception as backup_err:
                        print(f"Warning: Could not create backup: {str(backup_err)}")
                    return False
            self.completion = save_data["completion"]
            if "total_goal" in save_data:
                self.total_goal = save_data["total_goal"]
            else:
                self.total_goal = TOTAL_REFINEMENT_GOAL

            if "total_refined" in save_data:
                self.total_refined = save_data["total_refined"]
            if self.screen == 2 and self.bins:
                for bin_data in save_data["bins"]:
                    bin_idx = bin_data["bin_id"]
                    if bin_idx < len(self.bins):
                        self.bins[bin_idx].levels = bin_data["levels"]
                        self.bins[bin_idx].last_refined_time = bin_data["last_refined_time"]
                        self.bins[bin_idx].update_progress_bar()
                if "total_refined" not in save_data:
                    self.update_total_refined()
                self.update_top_progress_bar()
            return True
        except Exception as e:
            print(f"Error loading progress: {str(e)}")
            return False

    def setup_autosave(self, interval=300):
        """
        Setup automatic saving at five minutes.
        """
        self.save_progress()
        self.root.after(interval * 1000, lambda: self.setup_autosave(interval))

    def create_ui_elements(self):
        """Create the UI elements for the MDR terminal"""
        for element_id in self.ui_elements.values():
            self.canvas.delete(element_id)
        self.ui_elements.clear()
        if hasattr(self, 'progress_fill_id'):
            self.canvas.delete(self.progress_fill_id)
        usable_width = self.screen_width - (2 * self.margin)
        header_height = 40
        footer_height = 30
        self.ui_elements['top_frame'] = self.canvas.create_rectangle(
            self.margin - 5, self.margin - 5,
            self.margin + usable_width -50, self.margin + header_height + 5,
            outline=self.palette.FG, fill=self.palette.BG, width=2
        )
        print(self.canvas.bbox(self.ui_elements['top_frame']))
        self.ui_elements['top_curve'] = self.canvas.create_line(
            self.margin, self.margin + header_height + 15,
            self.margin + usable_width, self.margin + header_height + 15,
            fill=self.palette.FG, width=2
        )
        self.ui_elements['location'] = self.canvas.create_text(
        self.margin + 20, self.margin + header_height/2,
        text=self.location,
        font=('Arial', 18),
        fill=self.palette.FG,
        anchor='w'
        )
        logo_x = self.margin + usable_width - 75
        logo_y = self.margin + header_height/2
        self.lumon_logo_photo = ImageTk.PhotoImage(self.logo_img) # pylint: disable=attribute-defined-outside-init
        self.ui_elements['logo'] = self.canvas.create_image(
            logo_x, logo_y,
            image=self.lumon_logo_photo,
            anchor=tk.CENTER
        )
        logo_bbox = self.canvas.bbox(self.ui_elements['logo'])
        completion_text = f"{self.completion}% Complete"
        outlined_img = self.create_outlined_text(completion_text, font_size=20, stroke_width=1)
        self.completion_photo = outlined_img
        completion_x = logo_bbox[0] - 20
        self.ui_elements['completion'] = self.canvas.create_image(
            completion_x, self.margin + header_height/2,
            image=outlined_img,
            anchor=tk.E
        )

        bins_y_position = self.screen_height - self.margin - 100
        progress_bar_height = 30
        spacing_after_bar = 30
        bottom_frame_y = bins_y_position + 5 + progress_bar_height + spacing_after_bar
        self.ui_elements['bottom_curve'] = self.canvas.create_line(
            self.margin, bins_y_position - 25,
            self.margin + usable_width, bins_y_position - 25,
            fill=self.palette.FG, width=2
        )
        self.ui_elements['bottom_shield'] = self.canvas.create_rectangle(
            self.margin - 5, bottom_frame_y-16,
            self.margin + usable_width + 5, bottom_frame_y,
            outline='', fill=self.palette.BG, width=2
        )
        self.ui_elements['bottom_frame'] = self.canvas.create_rectangle(
            self.margin - 5, bottom_frame_y,
            self.margin + usable_width + 5, bottom_frame_y + footer_height,
            outline=self.palette.FG, fill=self.palette.FG, width=2
        )
        serial = self.generate_serial_number(self.username)
        self.ui_elements['serial'] = self.canvas.create_text(
            self.margin + usable_width/2, bottom_frame_y + footer_height/2,
            text=serial,
            font=('Courier', 14),
            fill=self.palette.BG
        )
        if 'completion' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['completion'])
            print("Raised completion text to top")
        self.update_top_progress_bar()

    def create_outlined_text(self, text, font_size=24, stroke_width=1):
        """
        Creates an image with outlined text using PIL's stroke feature
        """
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", font_size)
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        padding = 6
        width = text_width + padding * 2 + stroke_width * 2
        height = text_height + padding * 2 + stroke_width * 2

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill_color = self.palette.BG
        stroke_color = self.palette.FG
        position = (padding + stroke_width, padding)
        draw.text(position, text, font=font, fill=fill_color,
                  stroke_width=stroke_width, stroke_fill=stroke_color)
        photo = ImageTk.PhotoImage(img)
        return photo

    def create_completion_text(self, text):
        """Creates and returns a canvas image item with stroke-outlined text"""
        photo = self.create_outlined_text(text)
        self.completion_photo = photo
        return photo

    def create_bins(self):
        """Create bins at the bottom of the screen"""
        bin_count = 5
        usable_width = self.screen_width - (2 * self.margin)
        actual_bin_width = (usable_width / bin_count) * 0.9
        spacing = (usable_width - (bin_count * actual_bin_width)) / (bin_count + 1)

        for bin_obj in self.bins:
            if hasattr(bin_obj, 'visual_elements'):
                for element_id in bin_obj.visual_elements.values():
                    self.canvas.delete(element_id)
            if hasattr(bin_obj, 'level_elements'):
                for element_id in bin_obj.level_elements.values():
                    self.canvas.delete(element_id)
            if hasattr(bin_obj, 'progress_bar_elements'):
                for element_id in bin_obj.progress_bar_elements.values():
                    self.canvas.delete(element_id)
        self.bins.clear()
        bin_goal = self.total_goal // bin_count
        bins_y_position = self.screen_height - self.margin - 100
        for i in range(bin_count):
            bin_obj = Bin(actual_bin_width, i, bin_goal, self.canvas, palette=self.palette)
            x_pos = (self.margin + spacing + (i *(actual_bin_width + spacing))
                     + (actual_bin_width / 2))
            bin_obj.x = x_pos
            bin_obj.y = bins_y_position
            self.bins.append(bin_obj)
            bin_obj.create_visual_elements()
            bin_obj.update_progress_bar()

        if 'bottom_shield' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['bottom_shield'])
        if 'bottom_frame' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['bottom_frame'])
        if 'serial' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['serial'])

    def update_total_refined(self):
        """Update total refined count based on all bins' levels"""
        previous_total = self.total_refined
        self.total_refined = 0

        for bin_obj in self.bins:
            bin_total = sum(bin_obj.levels.values())
            self.total_refined += bin_total
        if self.total_refined != previous_total:
            self.update_overall_completion()

    def update_completion_text(self):
        """Updates the completion text with new percentage"""
        if 'completion' in self.ui_elements:
            completion_text = f"{self.completion}% Complete"
            outlined_img = self.create_completion_text(completion_text)
            self.canvas.itemconfig(self.ui_elements['completion'], image=outlined_img)

    def should_update_completion(self):
        """Check if we should update the completion percentage"""
        if not self.bins:
            return False
        for bin_obj in self.bins:
            if bin_obj.show_levels or bin_obj.opening_animation or bin_obj.closing_animation:
                return False
        return True

    def calculate_bin_percentages(self):
        """Calculate the average completion percentage across all bins"""
        if not self.bins:
            return 0
        bin_percentages = []
        for bin_obj in self.bins:
            total_levels = sum(bin_obj.levels.values())
            max_possible = bin_obj.level_goal * len(bin_obj.KEYS)
            bin_percentage = (total_levels / max_possible) * 100 if max_possible > 0 else 0
            bin_percentages.append(bin_percentage)
        avg_percentage = sum(bin_percentages) / len(bin_percentages) if bin_percentages else 0
        return avg_percentage

    def update_overall_completion(self):
        """
        Update the overall completion percentage based on total numbers refined.
        """
        if not self.bins:
            return
        raw_completion = (self.total_refined / self.total_goal) * 100
        self.completion = int(raw_completion)
        self.update_top_progress_bar()

    def update_top_progress_bar(self):
        """
        Update the top progress bar based on bin percentages.
        """
        total_percentage = 0
        bin_count = 0
        for bin_obj in self.bins:
            total_levels = sum(bin_obj.levels.values())
            max_possible = bin_obj.level_goal * len(bin_obj.KEYS)
            bin_percentage = (total_levels / max_possible) * 100 if max_possible > 0 else 0
            total_percentage += bin_percentage
            bin_count += 1
        if bin_count > 0:
            calculated_completion = int(total_percentage / bin_count)
            self.completion = calculated_completion
        frame_bbox = self.canvas.bbox(self.ui_elements['top_frame'])
        frame_left = frame_bbox[0]
        frame_top = frame_bbox[1]
        frame_bottom = frame_bbox[3]
        logo_bbox = self.canvas.bbox(self.ui_elements['logo'])
        logo_left = logo_bbox[0]
        location_right = frame_left
        if 'location' in self.ui_elements:
            location_bbox = self.canvas.bbox(self.ui_elements['location'])
            location_right = location_bbox[2] + 20
        fill_right = logo_left + 15
        fillable_width = fill_right - location_right - 4
        fill_width = (self.completion / 100) * fillable_width
        if self.completion == 0:
            fill_left = fill_right
        else:
            fill_left = fill_right - fill_width
        fill_left = max(fill_left, location_right)
        if 'completion' in self.ui_elements:
            completion_text = f"{self.completion}% Complete"
            outlined_img = self.create_outlined_text(completion_text, font_size=20, stroke_width=1)
            self.completion_photo = outlined_img
            self.canvas.itemconfig(self.ui_elements['completion'], image=self.completion_photo)
            completion_x = logo_left - 20
            if 'completion' in self.ui_elements:
                self.canvas.coords(
                    self.ui_elements['completion'],
                    completion_x, self.margin + 40/2
                )
            self.canvas.tag_raise(self.ui_elements['completion'])
        if hasattr(self, 'progress_fill_id'):
            self.canvas.delete(self.progress_fill_id) # pylint: disable=access-member-before-definition
        self.progress_fill_id = self.canvas.create_rectangle( # pylint: disable=attribute-defined-outside-init
            fill_left, frame_top + 2,
            fill_right, frame_bottom - 2,
            fill=self.palette.FG,
            outline="",
            width=0
        )
        if 'location' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['location'])
        if 'completion' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['completion'])
        if 'logo' in self.ui_elements:
            self.canvas.tag_raise(self.ui_elements['logo'])

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        is_fullscreen = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode and quit application"""
        self.root.attributes("-fullscreen", False)
        self.exit_program()
        return "break"

    def exit_program(self, event=None):
        """Exit the program and clean up resources"""
        if hasattr(self, 'haptic_enabled') and self.haptic_enabled:
            try:
                self.drv.stop()
            except Exception as e:
                print(f"Error stopping haptic motor: {e}")
        self.root.quit()
        self.root.destroy()

    def move_logo(self):
        """Animate the logo bouncing around"""
        if self.screen == 1 and self.canvas_image:
            self.x_pos += self.x_speed
            self.y_pos += self.y_speed
            if self.x_pos + self.photo.width() >= self.screen_width or self.x_pos <= 0:
                self.x_speed = -self.x_speed
            if self.y_pos + self.photo.height() >= self.screen_height or self.y_pos <= 0:
                self.y_speed = -self.y_speed
            self.canvas.coords(self.canvas_image, self.x_pos, self.y_pos)

    def create_number_grid(self):
        """Create the grid of numbers with proper horizontal centering"""
        for number in self.data_numbers:
            self.canvas.delete(number.text_id)
        self.data_numbers.clear()
        num_columns = 22
        num_rows = 8
        usable_width = self.screen_width - (2 * self.margin)
        header_height = 40
        bottom_line_y = self.screen_height - self.margin - 80 - 25
        total_available_height = bottom_line_y - (self.margin + header_height + 15)
        horizontal_spacing = usable_width / (num_columns + 1)
        vertical_spacing = total_available_height / (num_rows + 1)
        grid_width = horizontal_spacing * num_columns
        grid_height = vertical_spacing * num_rows
        start_x = self.margin + (usable_width - grid_width) / 2 + horizontal_spacing/2
        start_y = self.margin + header_height + 15 + (total_available_height
                                                      - grid_height) / 2 + vertical_spacing/2
        for row in range(num_rows):
            for col in range(num_columns):
                x = start_x + (col * horizontal_spacing)
                y = start_y + (row * vertical_spacing)
                data_number = DataNumber(x, y, self.canvas, self.base_size, palette=self.palette)
                self.data_numbers.append(data_number)

    def update_numbers(self):
        """Update the number animations"""
        if self.screen == 2:
            for number in self.data_numbers:
                if number.bin_it:
                    number.go_bin()
                else:
                    number.go_home()

    def update_bins(self):
        """Update the bin animations and ensure proper z-ordering"""
        if self.screen == 2:
            self.update_total_refined()
            self.check_for_completion()

            for bin_obj in self.bins:
                bin_obj.update()
                if 'bottom_shield' in self.ui_elements:
                    self.canvas.tag_raise(self.ui_elements['bottom_shield'])
                if 'bottom_frame' in self.ui_elements:
                    self.canvas.tag_raise(self.ui_elements['bottom_frame'])
                if 'serial' in self.ui_elements:
                    self.canvas.tag_raise(self.ui_elements['serial'])
                for number in self.data_numbers:
                    if number.bin_it and number.bin == bin_obj:
                        if hasattr(bin_obj, 'level_elements'):
                            for element_id in bin_obj.level_elements.values():
                                self.canvas.tag_raise(number.text_id, element_id)

    def toggle_screen(self, event):
        """Toggle between logo and number screens with autosave"""
        if self.screen == 1:
            self.root.attributes("-fullscreen", True)
            self.screen = 2
            if self.canvas_image:
                self.canvas.itemconfig(self.canvas_image, state='hidden')
            self.canvas.configure(bg=self.palette.BG)
            self.completion = 0
            self.total_refined = 0
            if hasattr(self, 'completion_triggered'):
                self.completion_triggered = False
            if hasattr(self, 'completion_message_elements'):
                for element_id in self.completion_message_elements.values():
                    self.canvas.delete(element_id)
                self.completion_message_elements = {}
            self.create_ui_elements()
            self.create_bins()
            self.create_number_grid()
            self.wiggle_timer = 0
            self.waiting_for_next_wiggle = False
            self.next_wiggle_timer = 0
            load_successful = self.load_progress()
            all_bins_full = all(bin_obj.is_full() for bin_obj in self.bins)
            if all_bins_full:
                print("All bins were previously full. Resetting progress to start over.")
                for bin_obj in self.bins:
                    bin_obj.levels = {
                        'WO': 0,
                        'FC': 0,
                        'DR': 0,
                        'MA': 0
                    }
                    bin_obj.update_progress_bar()
                self.total_refined = 0
                self.completion = 0
                self.update_top_progress_bar()
            elif not load_successful:
                self.total_refined = 0
                self.completion = 0
                for bin_obj in self.bins:
                    bin_obj.levels = {
                        'WO': 0,
                        'FC': 0,
                        'DR': 0,
                        'MA': 0
                    }
                    bin_obj.update_progress_bar()
                self.update_top_progress_bar()
            self.select_random_wiggle_group()
        else:
            self.save_progress()
            self.root.attributes("-fullscreen", True)
            self.wiggle_numbers.clear()
            self.wiggle_timer = 0
            self.waiting_for_next_wiggle = False
            self.next_wiggle_timer = 0
            if hasattr(self, 'progress_fill_id'):
                self.canvas.delete(self.progress_fill_id)
            for element_id in self.ui_elements.values():
                self.canvas.delete(element_id)
            self.ui_elements.clear()
            for bin_obj in self.bins:
                if hasattr(bin_obj, 'visual_elements'):
                    for element_id in bin_obj.visual_elements.values():
                        self.canvas.delete(element_id)
                if hasattr(bin_obj, 'level_elements'):
                    for element_id in bin_obj.level_elements.values():
                        self.canvas.delete(element_id)
                if hasattr(bin_obj, 'progress_bar_elements'):
                    for element_id in bin_obj.progress_bar_elements.values():
                        self.canvas.delete(element_id)
            self.bins.clear()
            for number in self.data_numbers:
                self.canvas.delete(number.text_id)
            self.data_numbers.clear()
            if hasattr(self, 'top_progress_elements'):
                for element_id in self.top_progress_elements.values():
                    self.canvas.delete(element_id)
                self.top_progress_elements.clear()
            if hasattr(self, 'completion_message_elements'):
                for element_id in self.completion_message_elements.values():
                    self.canvas.delete(element_id)
                self.completion_message_elements.clear()
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
                self.selection_active = False
            self.screen = 1
            self.canvas.configure(bg=self.palette.BG)
            if self.canvas_image:
                self.canvas.itemconfig(self.canvas_image, state='normal')
                self.canvas.tag_raise(self.canvas_image)
                if hasattr(self, 'x_pos') and hasattr(self, 'y_pos'):
                    self.canvas.coords(self.canvas_image, self.x_pos, self.y_pos)

    def start_selection(self, event):
        """Start a selection box when mouse is pressed"""
        if self.screen == 2:
            self.selection_start = (event.x, event.y)
            self.selection_rect = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline=self.palette.SELECT, width=2, dash=(5, 5)
            )
            self.selection_active = True

    def update_selection(self, event):
        """Update the selection box when mouse is dragged"""
        if self.screen == 2 and self.selection_active:
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            self.canvas.coords(self.selection_rect, x1, y1, x2, y2)

    def end_selection(self, event):
        """Process the selection when mouse is released"""
        if self.screen == 2 and self.selection_active:
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            selected_numbers = []
            for number in self.data_numbers:
                if number.inside(x1, y1, x2, y2) and not number.bin_it:
                    selected_numbers.append(number)
                    number.turn(self.palette.SELECT)
            wiggle_selected = [n for n in selected_numbers if n in self.wiggle_numbers]
            non_wiggle_selected = [n for n in selected_numbers if n not in self.wiggle_numbers]
            wiggle_capture_percent = (len(wiggle_selected) / len(self.wiggle_numbers)
                                      if self.wiggle_numbers else 0)
            valid_selection = (
                wiggle_capture_percent >= 0.7 and
                len(non_wiggle_selected) <= len(wiggle_selected) * 2
            )
            if valid_selection:
                self.pulse_selected(wiggle_selected, 3)
                self.refine_numbers(wiggle_selected)
                for number in wiggle_selected:
                    if number in self.wiggle_numbers:
                        self.wiggle_numbers.remove(number)
                        number.needs_refinement = False
                self.waiting_for_next_wiggle = True
                self.next_wiggle_timer = 0
            else:
                for number in selected_numbers:
                    number.turn(self.palette.FG)
            self.update_overall_completion()
            self.canvas.delete(self.selection_rect)
            self.selection_active = False

    def pulse_selected(self, numbers, count, size_factor=1.5, current=0):
        """Create a pulsing animation for selected numbers"""
        if current >= count * 2:
            return
        if current < count:
            progress = current / count
            size_mod = 1.0 + (progress * (size_factor - 1.0))
        else:
            progress = (current - count) / count
            size_mod = size_factor - (progress * (size_factor - 1.0))
        for number in numbers:
            number.set_size(self.base_size * size_mod)
        self.root.after(50, lambda: self.pulse_selected(numbers, count, size_factor, current + 1))

    def refine_numbers(self, numbers):
        """Send selected numbers to bins based on their horizontal position"""
        wiggling_numbers = [n for n in numbers if n in self.wiggle_numbers]
        if not wiggling_numbers:
            return
        DataNumber.reset_active_bin()
        all_bins_full = all(bin_obj.is_full() for bin_obj in self.bins)
        if all_bins_full:
            print("All bins are full - can't refine more numbers")
            return
        number_positions = {}
        for number in wiggling_numbers:
            target_bin = number.get_non_full_bin_for_position(self.bins)
            if target_bin:
                if target_bin not in number_positions:
                    number_positions[target_bin] = []
                number_positions[target_bin].append(number)
        selected_bin = None
        max_count = 0
        for bin_obj, bin_numbers in number_positions.items():
            if len(bin_numbers) > max_count:
                max_count = len(bin_numbers)
                selected_bin = bin_obj
        if selected_bin:
            DataNumber.active_bin = selected_bin
            for number in wiggling_numbers:
                success = number.refine(bin_obj=selected_bin)
                if not success:
                    number.needs_refinement = False
                    if number in self.wiggle_numbers:
                        self.wiggle_numbers.remove(number)

    def select_random_wiggle_group(self):
        """Randomly select a CLUSTERED group of numbers that need refinement"""
        for number in self.wiggle_numbers:
            number.needs_refinement = False
            number.wiggle_offset_x = 0
            number.wiggle_offset_y = 0
        self.wiggle_numbers.clear()
        all_bins_full = all(bin_obj.is_full() for bin_obj in self.bins)
        if all_bins_full:
            return
        if not self.data_numbers:
            return
        available_numbers = [n for n in self.data_numbers if not n.bin_it]
        if not available_numbers:
            return
        seed_number = random.choice(available_numbers)
        for number in available_numbers:
            number.distance_to_seed = self.calculate_distance(
                seed_number.x, seed_number.y, number.x, number.y
            )
        available_numbers.sort(key=lambda n: n.distance_to_seed)
        cluster_size = random.randint(3, 6)
        clustered_numbers = available_numbers[:min(cluster_size, len(available_numbers))]
        self.wiggle_numbers = clustered_numbers
        for number in self.wiggle_numbers:
            number.needs_refinement = True

    def calculate_distance(self, x1, y1, x2, y2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def wiggle_selected_numbers(self):
        """Apply smooth, floating wiggle effect to numbers
        that need refinement and update haptics
        """
        if self.screen == 2 and self.wiggle_numbers:
            self.wiggle_phase_x += self.wiggle_speed_x
            self.wiggle_phase_y += self.wiggle_speed_y
            self.wiggle_phase_rotation += self.wiggle_speed_rotation
            proximity_factor = 0
            if len(self.wiggle_numbers) > 0:
                center_x = sum(number.x for number in
                               self.wiggle_numbers) / len(self.wiggle_numbers)
                center_y = sum(number.y for number in
                               self.wiggle_numbers) / len(self.wiggle_numbers)
                distance_to_mouse = math.sqrt((self.mouse_x - center_x)**2 +
                                              (self.mouse_y - center_y)**2)
                normalized_distance = max(0, min(1, distance_to_mouse / self.proximity_threshold))
                proximity_factor = 1.0 - normalized_distance
                dynamic_amplitude = self.base_wiggle_amplitude + (
                    (self.max_wiggle_amplitude - self.base_wiggle_amplitude) *
                    proximity_factor**1.5
                )
                self.update_haptic_intensity(proximity_factor)
            else:
                dynamic_amplitude = self.base_wiggle_amplitude
                self.update_haptic_intensity(0)
            for number in self.wiggle_numbers:
                if not number.bin_it:
                    index = self.wiggle_numbers.index(number)
                    phase_offset = index * 0.5
                    x_freq2 = 0.37
                    y_freq2 = 0.29
                    primary_x = math.sin(self.wiggle_phase_x
                                         + phase_offset) * dynamic_amplitude
                    primary_y = math.cos(self.wiggle_phase_y
                                         + phase_offset) * dynamic_amplitude * 0.8
                    secondary_x = math.sin(self.wiggle_phase_x * x_freq2
                                           + phase_offset * 1.3) * dynamic_amplitude * 0.3
                    secondary_y = math.cos(self.wiggle_phase_y * y_freq2
                                           + phase_offset * 0.9) * dynamic_amplitude * 0.25
                    rot_x = math.cos(self.wiggle_phase_rotation
                                     + index * 0.7) * dynamic_amplitude * 0.2
                    rot_y = math.sin(self.wiggle_phase_rotation
                                     + index * 0.7) * dynamic_amplitude * 0.2
                    offset_x = primary_x + secondary_x + rot_x
                    offset_y = primary_y + secondary_y + rot_y
                    number.wiggle_offset_x = offset_x
                    number.wiggle_offset_y = offset_y
                    number.show_wiggle(proximity_factor)

    def check_for_completion(self):
        """Check if all bins are full and trigger completion sequence if needed"""
        if self.screen != 2:
            return
        if hasattr(self, 'completion_triggered') and self.completion_triggered:
            return
        all_bins_full = all(bin_obj.is_full() for bin_obj in self.bins)
        if self.bins:
            total_refined = sum(sum(bin_obj.levels.values()) for bin_obj in self.bins)
            completion_pct = (total_refined / self.total_goal) * 100
        else:
            completion_pct = 0
        if all_bins_full or completion_pct >= 100:
            self.completion_sequence()

    def completion_sequence(self):
        """Start sequence for completion"""
        self.completion_triggered = True
        self.fade_out_numbers()
        self.completion = 100
        self.update_top_progress_bar()

    def fade_out_numbers(self):
        """Fade out all numbers gradually"""
        self.fade_step = 0
        self.fade_timer = 0
        self.max_fade_steps = 20
        self.animate_number_fade()

    def animate_number_fade(self):
        """Animate the fading out of all numbers"""
        if self.fade_step >= self.max_fade_steps:
            self.show_completion_message()
            return
        alpha = int(255 * (1 - (self.fade_step / self.max_fade_steps)))
        for number in self.data_numbers:
            number.alpha = alpha
            number.update_display()
        self.fade_step += 1
        self.root.after(50, self.animate_number_fade)

    def show_completion_message(self):
        """Show the completion celebration message"""
        if hasattr(self, 'completion_message_elements'):
            for element_id in self.completion_message_elements.values():
                self.canvas.delete(element_id)
        self.completion_message_elements = {}
        if 'top_curve' in self.ui_elements:
            top_y = self.canvas.coords(self.ui_elements['top_curve'])[1] + 15
        else:
            top_y = self.margin + 80
        if 'bottom_curve' in self.ui_elements:
            bottom_y = self.canvas.coords(self.ui_elements['bottom_curve'])[1] - 15
        else:
            bottom_y = self.screen_height - self.margin - 130
        center_x = self.screen_width / 2
        center_y = (top_y + bottom_y) / 2
        self.completion_message_elements['percent'] = self.canvas.create_text(
            center_x, center_y - 30,
            text="100%",
            font=('Courier', 48, 'bold'),
            fill=self.palette.FG,
            anchor='center'
        )
        self.completion_message_elements['praise'] = self.canvas.create_text(
            center_x, center_y + 30,
            text="Praise Kier",
            font=('Courier', 36, 'bold'),
            fill=self.palette.FG,
            anchor='center'
        )
        self.glow_step = 0
        self.animate_completion_glow()

    def animate_completion_glow(self):
        """Create a subtle glowing/pulsing effect for the completion message"""
        if (not hasattr(self, 'completion_message_elements')
            or 'percent' not in self.completion_message_elements):
            return
        glow_factor = 0.8 + (0.2 * (math.sin(self.glow_step / 10) + 1) / 2)
        percent_size = int(48 * glow_factor)
        praise_size = int(36 * glow_factor)
        self.canvas.itemconfig(
            self.completion_message_elements['percent'],
            font=('Courier', percent_size, 'bold')
        )
        self.canvas.itemconfig(
            self.completion_message_elements['praise'],
            font=('Courier', praise_size, 'bold')
        )
        self.glow_step += 1
        self.root.after(100, self.animate_completion_glow)

    def animate(self):
        """Main animation loop"""
        if self.screen == 1:
            self.root.attributes("-fullscreen", True)
            self.move_logo()
        else:
            self.update_bins()
            self.update_numbers()
            for number in self.data_numbers:
                self.apply_mouse_avoidance(number)
            if self.waiting_for_next_wiggle:
                self.next_wiggle_timer += 1
                self.next_wiggle_delay = random.randint(180, 240)
                if self.next_wiggle_timer >= self.next_wiggle_delay:
                    self.waiting_for_next_wiggle = False
                    self.next_wiggle_timer = 0
                    self.select_random_wiggle_group()
            elif (not self.wiggle_numbers and not self.waiting_for_next_wiggle
                  and self.wiggle_timer == 0):
                self.select_random_wiggle_group()
            self.wiggle_selected_numbers()
        self.root.after(20, self.animate)

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = MacrodataRefinementTerminal()
    app.run()
