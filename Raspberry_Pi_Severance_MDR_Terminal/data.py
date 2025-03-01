# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import math
import random
import tkinter as tk
import time
from palette import Palette

class DataNumber:
    active_bin = None

    @classmethod
    def reset_active_bin(cls):
        """Reset the class-level active bin tracker"""
        cls.active_bin = None

    def __init__(self, x: int, y: int, canvas: tk.Canvas, base_size: int = 35, palette=Palette):
        """
        Initialize a data number for macrodata refinement
        """
        self.num = random.randint(0, 9)
        self.home_x = x
        self.home_y = y
        self.x = x
        self.y = y
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.palette = palette
        self.color = self.palette.FG
        self.alpha = 255
        self.base_size = base_size
        self.size = base_size
        self.refined = False
        self.bin_it = False
        self.bin = None
        self.bin_pause_time = 2
        self.bin_pause = self.bin_pause_time
        self.canvas = canvas
        self.text_id = self.canvas.create_text(
            self.x, self.y,
            text=str(self.num),
            font=('Courier', self.size),
            fill=self.color,
            anchor='center'
        )
        self.needs_refinement = False
        self.wiggle_offset_x = 0
        self.wiggle_offset_y = 0

    def refine(self, bin_obj=None, bins_list=None):
        """
        Mark this number for refinement and assign it to a bin.
        """
        if bin_obj is not None:
            if bin_obj.is_full():
                return False
            target_bin = bin_obj
        elif bins_list is not None:
            target_bin = self.get_non_full_bin_for_position(bins_list)
            if target_bin is None:
                return False
        else:
            raise ValueError("Either bin_obj or bins_list must be provided")
        self.bin_it = True
        if DataNumber.active_bin is None:
            DataNumber.active_bin = target_bin
            self.bin = target_bin
        else:
            if DataNumber.active_bin.is_full():
                DataNumber.active_bin = target_bin
            self.bin = DataNumber.active_bin
        return True

    def get_non_full_bin_for_position(self, bins_list):
        """
        Determine which available bin should open based on the position of this number.
        """
        non_full_bins = [bin_obj for bin_obj in bins_list if not bin_obj.is_full()]
        if not non_full_bins:
            return None
        screen_width = self.canvas.winfo_width()
        original_bin_index = self.get_bin_index_for_position(screen_width, len(bins_list))
        closest_bin = None
        min_distance = float('inf')
        for bin_obj in non_full_bins:
            distance = abs(bin_obj.i - original_bin_index)
            if distance < min_distance:
                min_distance = distance
                closest_bin = bin_obj
        return closest_bin

    def get_bin_index_for_position(self, screen_width, num_bins):
        """
        Get the bin index that corresponds to this number's position
        """
        bin_width = screen_width / num_bins
        bin_index = int(self.x / bin_width)
        bin_index = max(0, min(bin_index, num_bins - 1))
        return bin_index

    def go_bin(self):
        """Move toward the bin for refinement"""
        if self.bin:
            self.bin.open()
            if self.bin_pause <= 0:
                dx = self.bin.x - self.x
                dy = self.bin.y - self.y
                distance = math.sqrt(dx*dx + dy*dy)
                if distance < 20:
                    self.alpha = int(255 * (distance / 20))
                    if distance < 3:
                        self.wiggle_offset_x = 0
                        self.wiggle_offset_y = 0
                        self.mouse_offset_x = 0
                        self.mouse_offset_y = 0
                        self.bin.add_number()
                        self.reset()
                        return
                easing = max(0.03, min(0.1, 5.0 / distance))
                self.x += dx * easing
                self.y += dy * easing
                fade_start_distance = self.distance(self.home_x, self.home_y,
                                                    self.bin.x, self.bin.y) * 0.4
                current_distance = self.distance(self.x, self.y, self.bin.x, self.bin.y)
                if distance >= 20:
                    self.alpha = self.map_value(current_distance, fade_start_distance, 20, 255, 55)
                self.update_display()
                if hasattr(self.bin, 'level_elements'):
                    for element_id in self.bin.level_elements.values():
                        self.canvas.tag_raise(self.text_id, element_id)
                self.bin.last_refined_time = int(time.time() * 1000)
            else:
                self.bin_pause -= 1
                if self.bin_pause > 0:
                    pulse_size = self.base_size * (1.0 + 0.5 *
                                 (1.0 - (self.bin_pause / self.bin_pause_time)))
                    self.set_size(pulse_size)
                    if hasattr(self.bin, 'level_elements'):
                        for element_id in self.bin.level_elements.values():
                            self.canvas.tag_raise(self.text_id, element_id)

    def reset(self):
        """Reset the number after being binned."""
        self.num = random.randint(0, 9)
        self.x = self.home_x
        self.y = self.home_y
        self.wiggle_offset_x = 0
        self.wiggle_offset_y = 0
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.refined = False
        self.bin_it = False
        self.bin = None
        self.color = self.palette.FG
        self.alpha = 255
        self.bin_pause = self.bin_pause_time
        self.update_display()
        still_active = False
        if not still_active and DataNumber.active_bin is not None:
            DataNumber.active_bin = None

    def go_home(self):
        """Move the number back to its home position with easing."""
        self.x = self.lerp(self.x, self.home_x, 0.1)
        self.y = self.lerp(self.y, self.home_y, 0.1)
        self.size = self.lerp(self.size, self.base_size, 0.1)
        self.update_display()

    def set_size(self, sz):
        """Set the size of the number."""
        self.size = sz
        self.update_display()

    def turn(self, new_color):
        """Change the color of the number."""
        self.color = new_color
        self.update_display()

    def inside(self, x1, y1, x2, y2):
        """Check if this number is inside the given rectangle."""
        return (
            self.x > min(x1, x2) and
            self.x < max(x1, x2) and
            self.y > min(y1, y2) and
            self.y < max(y1, y2)
        )

    def show(self):
        """Update the display of this number."""
        self.update_display()

    def update_display(self):
        """Update the text display with current properties and improved alpha handling"""
        if self.bin_it:
            digit_size = self.lerp(self.size, self.size * 2.5,
                        self.map_value(self.bin_pause, self.bin_pause_time, 0, 0, 1))
        else:
            digit_size = self.size
        font = ('Courier', int(digit_size))
        clamped_alpha = max(0, min(255, self.alpha))
        if clamped_alpha == 0:
            self.canvas.itemconfig(self.text_id, state='hidden')
            return
        else:
            self.canvas.itemconfig(self.text_id, state='normal')
        if clamped_alpha < 255:
            bg_color = self.palette.BG
            fg_color = self.color
            alpha_ratio = clamped_alpha / 255.0
            if alpha_ratio < 0.05:
                display_color = self.blend_colors(bg_color, fg_color, 0.05)
            else:
                display_color = self.blend_colors(bg_color, fg_color, alpha_ratio)
        else:
            display_color = self.color
        self.canvas.itemconfig(self.text_id,
                            text=str(self.num),
                            font=font,
                            fill=display_color)
        if not hasattr(self, 'wiggle_offset_x'):
            self.wiggle_offset_x = 0
        if not hasattr(self, 'wiggle_offset_y'):
            self.wiggle_offset_y = 0
        if not hasattr(self, 'mouse_offset_x'):
            self.mouse_offset_x = 0
        if not hasattr(self, 'mouse_offset_y'):
            self.mouse_offset_y = 0
        smooth_wiggle_x = round(self.wiggle_offset_x * 10) / 10
        smooth_wiggle_y = round(self.wiggle_offset_y * 10) / 10
        smooth_mouse_x = round(self.mouse_offset_x * 10) / 10
        smooth_mouse_y = round(self.mouse_offset_y * 10) / 10
        display_x = self.x + smooth_wiggle_x + smooth_mouse_x
        display_y = self.y + smooth_wiggle_y + smooth_mouse_y
        self.canvas.coords(self.text_id, display_x, display_y)

    def resize(self, new_x, new_y):
        """Update the home position when the window is resized."""
        self.home_x = new_x
        self.home_y = new_y

    def show_wiggle(self, proximity_factor=0):
        """Make the number threatening"""
        if self.needs_refinement and not self.bin_it:
            original_x, original_y = self.x, self.y
            smooth_x = round(self.wiggle_offset_x * 10) / 10
            smooth_y = round(self.wiggle_offset_y * 10) / 10
            self.x += smooth_x
            self.y += smooth_y
            original_color = self.color
            base_pulse = 0.7
            wave1 = math.sin(time.time() * 0.9) * 0.15
            wave2 = math.sin(time.time() * 1.8) * 0.05
            highlight_intensity = base_pulse + wave1 + wave2 + (proximity_factor * 0.2)
            highlight_intensity = max(0.6, min(1.0, highlight_intensity))
            if highlight_intensity > 0.82:
                self.color = self.palette.SELECT
            else:
                blend_amount = (highlight_intensity - 0.6) / 0.22
                self.color = self.blend_colors(self.palette.FG, self.palette.SELECT, blend_amount)
            self.update_display()
            self.x, self.y = original_x, original_y
            self.color = original_color

    @staticmethod
    def lerp(start, end, amt):
        """Linear interpolation between start and end by amt."""
        return start + (end - start) * amt

    @staticmethod
    def map_value(value, start1, stop1, start2, stop2):
        """Re-maps a number from one range to another."""
        if stop1 == start1:
            return start2
        return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1))

    @staticmethod
    def distance(x1, y1, x2, y2):
        """Calculate distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB values."""
        # Strip the # if it exists
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb):
        """Convert RGB tuple to hex color."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    @staticmethod
    def blend_colors(color1, color2, ratio):
        """Blend two colors based on ratio (0-1)."""
        c1 = DataNumber.hex_to_rgb(color1)
        c2 = DataNumber.hex_to_rgb(color2)
        blended = tuple(int(c1[i] + (c2[i] - c1[i]) * ratio) for i in range(3))
        return DataNumber.rgb_to_hex(blended)
