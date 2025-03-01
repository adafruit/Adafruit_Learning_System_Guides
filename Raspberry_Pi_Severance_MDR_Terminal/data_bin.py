# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import math
import time
import random
import tkinter as tk
from PIL import Image, ImageTk, ImageFont, ImageDraw

# pylint: disable=broad-exception-caught,too-many-locals

class Bin:
    KEYS = ['WO', 'FC', 'DR', 'MA']
    MAX_LID_ANGLE = 45
    CLOSED_LID_ANGLE = 180
    MAX_SHOW_TIME = 1500  # milliseconds
    LID_OPEN_CLOSE_TIME = 750  # milliseconds

    def __init__(self, width, index, goal, canvas, levels=None, palette=None):
        self.w = width
        self.i = index
        self.x = index * width + width * 0.5
        self.canvas = canvas
        self.buffer = 60
        self.y = canvas.winfo_height() - 50
        self.palette = palette
        self.fg_color = self.palette.FG
        self.bg_color = self.palette.BG
        self.goal = goal
        self.level_goal = self.goal / 4
        self.level_h = self.buffer * 1.7
        self.levels_y_offset = self.level_h
        self.last_refined_time = self.get_millis()
        if levels is None:
            self.levels = {
                'WO': 0,
                'FC': 0,
                'DR': 0,
                'MA': 0
            }
        else:
            self.levels = levels
        self.count = sum(self.levels.values())

        self.show_levels = False
        self.closing_animation = False
        self.opening_animation = False
        self.lid_angle = self.CLOSED_LID_ANGLE
        self.show_time = 0
        self.animation_start_time = 0
        self.animation_progress = 0

        self.visual_elements = {}
        self.level_elements = {}
        self.progress_bar_elements = {}

        self.create_visual_elements()

    def create_outlined_text(self, text, font_size=22, stroke_width=4):
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", font_size)
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        padding = 12
        width = text_width + padding * 2 + stroke_width * 2
        height = text_height + padding * 2 + stroke_width * 2
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill_color = self.bg_color
        stroke_color = self.fg_color
        position = (padding + stroke_width, padding+stroke_width)
        draw.text(position, text, font=font, fill=fill_color,
                  stroke_width=stroke_width, stroke_fill=stroke_color)
        photo = ImageTk.PhotoImage(img)
        return photo

    def create_visual_elements(self):
        for key in list(self.visual_elements.keys()):
            try:
                self.canvas.delete(self.visual_elements[key])
            except Exception:
                pass
        for key in list(self.level_elements.keys()):
            try:
                self.canvas.delete(self.level_elements[key])
            except Exception:
                pass
        for key in list(self.progress_bar_elements.keys()):
            try:
                self.canvas.delete(self.progress_bar_elements[key])
            except Exception:
                pass
        self.visual_elements = {}
        self.level_elements = {}
        self.progress_bar_elements = {}
        rw = self.w
        popup_width = rw
        popup_height = self.buffer * 3
        base_y = self.y - self.buffer/4
        popup_y = base_y - popup_height/2
        self.visual_elements['main'] = self.canvas.create_rectangle(
            self.x - rw/2, self.y - self.buffer/4,
            self.x + rw/2, self.y + self.buffer/4,
            outline=self.fg_color, fill=self.bg_color, width=1
        )
        self.visual_elements['label'] = self.canvas.create_text(
            self.x, self.y,
            text=f"{self.i:02d}",
            font=('Arial', 16),
            fill=self.fg_color
        )
        self.level_elements['popup_bg'] = self.canvas.create_rectangle(
            self.x - popup_width/2, popup_y - popup_height/2,
            self.x + popup_width/2, popup_y + popup_height/2,
            outline="", fill=self.bg_color,
            state='hidden'
        )
        self.level_elements['container'] = self.canvas.create_rectangle(
            self.x - popup_width/2, popup_y - popup_height/2,
            self.x + popup_width/2, popup_y + popup_height/2,
            outline=self.fg_color, fill="", width=1,
            state='hidden'
        )
        bar_height = popup_height * 0.15
        for i, key in enumerate(self.KEYS):
            level_y = popup_y - popup_height * 0.3 + i * (popup_height * 0.6 / 3)
            self.level_elements[f'{key}_label'] = self.canvas.create_text(
                self.x - popup_width * 0.4, level_y,
                text=key,
                font=('Courier', 14),
                fill=self.fg_color,
                anchor='w',
                state='hidden'
            )
            self.level_elements[f'{key}_outline'] = self.canvas.create_rectangle(
                self.x - popup_width * 0.2, level_y - bar_height/2,
                self.x + popup_width * 0.4, level_y + bar_height/2,
                outline=self.fg_color, fill="",
                state='hidden'
            )
            self.level_elements[f'{key}_progress'] = self.canvas.create_rectangle(
                self.x - popup_width * 0.2, level_y - bar_height/2,
                self.x - popup_width * 0.2, level_y + bar_height/2,
                outline="", fill=self.fg_color,
                state='hidden'
            )
        left_edge_x = self.x - rw/2
        right_edge_x = self.x + rw/2
        top_edge_y = self.y - self.buffer/4
        self.level_elements['left_lid'] = self.canvas.create_line(
            left_edge_x, top_edge_y,
            self.x, top_edge_y,
            fill=self.fg_color, width=1,
            state='normal'
        )
        self.level_elements['right_lid'] = self.canvas.create_line(
            self.x, top_edge_y,
            right_edge_x, top_edge_y,
            fill=self.fg_color, width=1,
            state='normal'
        )
        progress_bar_y = self.y + self.buffer/4 + 2
        progress_bar_height = self.buffer/2
        self.progress_bar_elements['outline'] = self.canvas.create_rectangle(
            self.x - rw/2, progress_bar_y,
            self.x + rw/2, progress_bar_y + progress_bar_height,
            outline=self.fg_color, fill=self.bg_color, width=1
        )
        self.progress_bar_elements['fill'] = self.canvas.create_rectangle(
            self.x - rw/2 + 1, progress_bar_y + 1,
            self.x - rw/2 + 1, progress_bar_y + progress_bar_height - 1,
            outline="", fill=self.fg_color
        )
        percentage_text = "0%"
        outlined_img = self.create_outlined_text(percentage_text, font_size=14, stroke_width=1)
        left_edge = self.x - rw/2
        text_padding = 14
        self.progress_bar_elements['text'] = self.canvas.create_image(
            left_edge + text_padding, progress_bar_y + progress_bar_height/2,
            image=outlined_img,
            anchor=tk.CENTER
        )
        self.fix_z_order()
        self.update_progress_bar()

    def fix_z_order(self):
        self.canvas.tag_raise(self.level_elements['popup_bg'])
        self.canvas.tag_raise(self.level_elements['container'])
        for key in self.KEYS:
            if f'{key}_label' in self.level_elements:
                self.canvas.tag_raise(self.level_elements[f'{key}_label'])
            if f'{key}_outline' in self.level_elements:
                self.canvas.tag_raise(self.level_elements[f'{key}_outline'])
            if f'{key}_progress' in self.level_elements:
                self.canvas.tag_raise(self.level_elements[f'{key}_progress'])
        self.canvas.tag_raise(self.visual_elements['main'])
        self.canvas.tag_raise(self.visual_elements['label'])
        self.canvas.tag_raise(self.level_elements['left_lid'])
        self.canvas.tag_raise(self.level_elements['right_lid'])
        self.canvas.tag_raise(self.progress_bar_elements['outline'])
        self.canvas.tag_raise(self.progress_bar_elements['fill'])
        self.canvas.tag_raise(self.progress_bar_elements['text'])

    def is_full(self):
        total_levels = sum(self.levels.values())
        return total_levels >= self.goal

    def add_number(self):
        if self.is_full():
            return False
        options = [key for key in self.KEYS if self.levels[key] < self.level_goal]
        if options:
            key = random.choice(options)
            self.levels[key] += 1
            self.open()
            self.last_refined_time = self.get_millis()
            self.update_display()
            self.update_progress_bar()
            self.fix_z_order()
            return True
        return False

    def open(self):
        if not self.show_levels and not self.opening_animation:
            self.animation_start_time = self.get_millis()
            self.opening_animation = True
            self.closing_animation = False
            self.show_levels = True

    def update(self):
        current_time = self.get_millis()
        if self.opening_animation:
            elapsed = current_time - self.animation_start_time
            if elapsed >= self.LID_OPEN_CLOSE_TIME:
                self.opening_animation = False
                self.animation_progress = 1.0
            else:
                progress = elapsed / self.LID_OPEN_CLOSE_TIME
                self.animation_progress = 1 - (1 - progress) * (1 - progress)
            self.update_display()
            self.fix_z_order()
        elif self.show_levels and not self.closing_animation:
            if current_time - self.last_refined_time > self.MAX_SHOW_TIME:
                self.closing_animation = True
                self.animation_start_time = current_time
        elif self.closing_animation:
            elapsed = current_time - self.animation_start_time
            if elapsed >= self.LID_OPEN_CLOSE_TIME:
                self.closing_animation = False
                self.show_levels = False
                self.animation_progress = 0.0
            else:
                progress = elapsed / self.LID_OPEN_CLOSE_TIME
                self.animation_progress = 1.0 - (progress * progress)
            self.update_display()
            self.fix_z_order()
        self.update_progress_bar()

    def update_progress_bar(self):
        total_levels = sum(self.levels.values())
        completion_percentage = (total_levels / self.goal) * 100 if self.goal > 0 else 0
        rw = self.w
        progress_bar_y = self.y + self.buffer/4 + 2
        progress_bar_height = self.buffer/2
        fill_width = (rw * completion_percentage) / 100
        if completion_percentage == 0:
            self.canvas.coords(
                self.progress_bar_elements['fill'],
                self.x - rw/2 + 1, progress_bar_y + 1,
                self.x - rw/2 + 1, progress_bar_y + progress_bar_height - 1
            )
        else:
            self.canvas.coords(
                self.progress_bar_elements['fill'],
                self.x - rw/2 + 1, progress_bar_y + 1,
                self.x - rw/2 + max(1, fill_width), progress_bar_y + progress_bar_height - 1
            )
        percentage_text = f"{int(completion_percentage)}%"
        outlined_img = self.create_outlined_text(
            percentage_text,
            font_size=14,
            stroke_width=1
        )
        left_edge = self.x - rw/2
        text_padding = 30 if completion_percentage >= 100 else 24
        self.canvas.itemconfig(self.progress_bar_elements['text'], image=outlined_img)
        self.canvas.coords(
            self.progress_bar_elements['text'],
            left_edge + text_padding, progress_bar_y + progress_bar_height/2
        )

    def update_display(self):
        self.count = sum(self.levels.values())
        self.count = min(max(self.count, 0), self.goal)
        rw = self.w
        popup_width = rw
        popup_height = self.buffer * 3
        base_y = self.y - self.buffer/4
        popup_y_closed = base_y
        popup_y_open = base_y - popup_height/2
        current_popup_y = self.map_value(
            self.animation_progress,
            0, 1,
            popup_y_closed, popup_y_open
        )
        self.canvas.coords(
            self.level_elements['popup_bg'],
            self.x - popup_width/2, current_popup_y - popup_height/2,
            self.x + popup_width/2, current_popup_y + popup_height/2
        )
        self.canvas.coords(
            self.level_elements['container'],
            self.x - popup_width/2, current_popup_y - popup_height/2,
            self.x + popup_width/2, current_popup_y + popup_height/2
        )
        left_edge_x = self.x - rw/2
        right_edge_x = self.x + rw/2
        top_edge_y = base_y
        max_lid_angle = 120
        current_angle = self.animation_progress * max_lid_angle
        angle_rad = math.radians(current_angle)

        left_lid_end_x = left_edge_x + (rw/2) * math.cos(angle_rad)
        left_lid_end_y = top_edge_y - (rw/2) * math.sin(angle_rad)
        right_lid_end_x = right_edge_x - (rw/2) * math.cos(angle_rad)
        right_lid_end_y = top_edge_y - (rw/2) * math.sin(angle_rad)
        self.canvas.coords(
            self.level_elements['left_lid'],
            left_edge_x, top_edge_y,
            left_lid_end_x, left_lid_end_y
        )
        self.canvas.coords(
            self.level_elements['right_lid'],
            right_edge_x, top_edge_y,
            right_lid_end_x, right_lid_end_y
        )
        visibility_threshold = 0.05
        state = 'normal' if self.animation_progress > visibility_threshold else 'hidden'

        self.canvas.itemconfig(self.level_elements['popup_bg'], state=state)
        self.canvas.itemconfig(self.level_elements['container'], state=state)
        self.canvas.itemconfig(self.level_elements['left_lid'], state='normal')
        self.canvas.itemconfig(self.level_elements['right_lid'], state='normal')
        self.update_level_displays(current_popup_y, popup_height, popup_width)
        if state == 'hidden':
            for key in self.KEYS:
                if f'{key}_label' in self.level_elements:
                    self.canvas.itemconfig(self.level_elements[f'{key}_label'], state='hidden')
                if f'{key}_outline' in self.level_elements:
                    self.canvas.itemconfig(self.level_elements[f'{key}_outline'], state='hidden')
                if f'{key}_progress' in self.level_elements:
                    self.canvas.itemconfig(self.level_elements[f'{key}_progress'], state='hidden')

    def update_level_displays(self, popup_y, popup_height, popup_width):
        bar_height = popup_height * 0.15
        state = 'normal' if self.animation_progress > 0.05 else 'hidden'
        bar_width = popup_width * 0.6
        for i, key in enumerate(self.KEYS):
            level_y = popup_y - popup_height * 0.3 + i * (popup_height * 0.6 / 3)
            self.canvas.coords(
                self.level_elements[f'{key}_label'],
                self.x - popup_width * 0.4, level_y
            )
            self.canvas.coords(
                self.level_elements[f'{key}_outline'],
                self.x - popup_width * 0.2, level_y - bar_height/2,
                self.x + popup_width * 0.4, level_y + bar_height/2
            )
            progress_width = ((bar_width * self.levels[key])
                              / self.level_goal if self.level_goal > 0 else 0)
            self.canvas.coords(
                self.level_elements[f'{key}_progress'],
                self.x - popup_width * 0.2, level_y - bar_height/2,
                self.x - popup_width * 0.2 + progress_width, level_y + bar_height/2
            )
            self.canvas.itemconfig(self.level_elements[f'{key}_label'], state=state)
            self.canvas.itemconfig(self.level_elements[f'{key}_outline'], state=state)
            self.canvas.itemconfig(self.level_elements[f'{key}_progress'], state=state)

    def resize(self, new_w):
        self.w = new_w
        self.x = self.i * new_w + new_w * 0.5
        self.y = self.canvas.winfo_height() - 50
        for key in list(self.visual_elements.keys()):
            try:
                self.canvas.delete(self.visual_elements[key])
            except Exception:
                pass

        for key in list(self.level_elements.keys()):
            try:
                self.canvas.delete(self.level_elements[key])
            except Exception:
                pass

        for key in list(self.progress_bar_elements.keys()):
            try:
                self.canvas.delete(self.progress_bar_elements[key])
            except Exception:
                pass
        self.visual_elements = {}
        self.level_elements = {}
        self.progress_bar_elements = {}
        self.create_visual_elements()
        self.update_display()

    @staticmethod
    def get_millis():
        return int(time.time() * 1000)

    @staticmethod
    def map_value(value, start1, stop1, start2, stop2):
        if stop1 == start1:
            return start2
        return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1))
