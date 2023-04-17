# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import sys
import os
import time
import math
from enum import Enum
import pygame

# Image Names
WELCOME_IMAGE = "welcome.png"
BACKGROUND_IMAGE = "paper_background.png"
LOADING_IMAGE = "loading.png"
BUTTON_BACK_IMAGE = "button_back.png"
BUTTON_NEXT_IMAGE = "button_next.png"

# Asset Paths
IMAGES_PATH = os.path.dirname(sys.argv[0]) + "images/"
FONTS_PATH = os.path.dirname(sys.argv[0]) + "fonts/"

# Font Path, Size
TITLE_FONT = (FONTS_PATH + "lucida_black.ttf", 48)
TITLE_COLOR = (0, 0, 0)
TEXT_FONT = (FONTS_PATH + "times new roman.ttf", 24)
TEXT_COLOR = (0, 0, 0)

# Delays to control the speed of the text
#   Default
WORD_DELAY = 0.1
TITLE_FADE_TIME = 0.05
TITLE_FADE_STEPS = 25
TEXT_FADE_TIME = 0.25
TEXT_FADE_STEPS = 51
BUTTON_FADE_TIME = 0.10
BUTTON_FADE_STEPS = 11

# Whitespace Settings in Pixels
PAGE_TOP_MARGIN = 20
PAGE_SIDE_MARGIN = 20
PAGE_BOTTOM_MARGIN = 0
PAGE_NAV_HEIGHT = 100
EXTRA_LINE_SPACING = 0
PARAGRAPH_SPACING = 30


class Position(Enum):
    TOP = 0
    CENTER = 1
    BOTTOM = 2
    LEFT = 3
    RIGHT = 4


class Button:
    def __init__(self, x, y, image, action, draw_function):
        self.x = x
        self.y = y
        self.image = image
        self.action = action
        self._width = self.image.get_width()
        self._height = self.image.get_height()
        self._visible = False
        self._draw_function = draw_function

    def is_in_bounds(self, position):
        x, y = position
        return (
            self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
        )

    def show(self):
        self._draw_function(
            self.image, self.x, self.y, BUTTON_FADE_TIME, BUTTON_FADE_STEPS
        )
        self._visible = True

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def visible(self):
        return self._visible


class Textarea:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def size(self):
        return {"width": self.width, "height": self.height}


class Book:
    def __init__(self, rotation=0):
        self.paragraph_number = 0
        self.page = 0
        self.title = ""
        self.paragraphs = []
        self.pages = []
        self.rotation = rotation
        self.images = {}
        self.fonts = {}
        self.width = 0
        self.height = 0
        self.back_button = None
        self.next_button = None
        self.textarea = None
        self.screen = None
        # Use a cursor to keep track of where we are in the text area
        self.cursor = {"x": 0, "y": 0}

    def init(self):
        # Output to the LCD instead of the console
        os.putenv("DISPLAY", ":0")

        # Initialize the display
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.width = self.screen.get_height()
        self.height = self.screen.get_width()

        # Preload images
        self.load_image("welcome", WELCOME_IMAGE)
        self.load_image("background", BACKGROUND_IMAGE)
        self.load_image("loading", LOADING_IMAGE)

        # Preload fonts
        self.load_font("title", TITLE_FONT)
        self.load_font("text", TEXT_FONT)

        # Add buttons
        back_button_image = pygame.image.load(IMAGES_PATH + BUTTON_BACK_IMAGE)
        next_button_image = pygame.image.load(IMAGES_PATH + BUTTON_NEXT_IMAGE)
        button_spacing = (
            self.width - (back_button_image.get_width() + next_button_image.get_width())
        ) // 3
        button_ypos = (
            self.height
            - PAGE_NAV_HEIGHT
            + (PAGE_NAV_HEIGHT - next_button_image.get_height()) // 2
        )
        self.back_button = Button(
            button_spacing,
            button_ypos,
            back_button_image,
            self.previous_page,
            self.fade_in_surface,
        )
        self.next_button = Button(
            self.width - button_spacing - next_button_image.get_width(),
            button_ypos,
            next_button_image,
            self.next_page,
            self.fade_in_surface,
        )

        # Add Text Area
        self.textarea = Textarea(
            PAGE_SIDE_MARGIN,
            PAGE_TOP_MARGIN,
            self.width - PAGE_SIDE_MARGIN * 2,
            self.height - PAGE_NAV_HEIGHT - PAGE_TOP_MARGIN - PAGE_BOTTOM_MARGIN,
        )

        pygame.mouse.set_visible(False)
        self.screen.fill((255, 255, 255))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # If button pressed while visible, trigger action
                    coords = self.rotate_mouse_pos(event.pos)
                    for button in [self.back_button, self.next_button]:
                        if button.visible and button.is_in_bounds(coords):
                            button.action()

    def rotate_mouse_pos(self, point):
        # Recalculate the mouse position based on the rotation of the screen
        # So that we have the coordinates relative to the upper left corner of the screen
        angle = 360 - self.rotation
        y, x = point
        x -= self.width // 2
        y -= self.height // 2
        x, y = x * math.sin(math.radians(angle)) + y * math.cos(
            math.radians(angle)
        ), x * math.cos(math.radians(angle)) - y * math.sin(math.radians(angle))
        x += self.width // 2
        y += self.height // 2
        return (round(x), round(y))

    def load_image(self, name, filename):
        try:
            image = pygame.image.load(IMAGES_PATH + filename)
            self.images[name] = image
        except pygame.error:
            pass

    def load_font(self, name, details):
        self.fonts[name] = pygame.font.Font(details[0], details[1])

    def get_position(self, obj, x, y):
        if x == Position.CENTER:
            x = (self.width - obj.get_width()) // 2
        elif x == Position.RIGHT:
            x = self.width - obj.get_width()
        elif x == Position.LEFT:
            x = 0
        elif not isinstance(x, int):
            raise ValueError("Invalid x position")

        if y == Position.CENTER:
            y = (self.height - obj.get_height()) // 2
        elif y == Position.BOTTOM:
            y = self.height - obj.get_height()
        elif y == Position.TOP:
            y = 0
        elif not isinstance(y, int):
            raise ValueError("Invalid y position")

        return (x, y)

    # Display a surface either positionally or with a specific x,y coordinate
    def display_surface(
        self, surface, x=Position.CENTER, y=Position.CENTER, target_surface=None
    ):
        buffer = self.create_transparent_buffer((self.width, self.height))
        buffer.blit(surface, self.get_position(surface, x, y))
        if target_surface is None:
            buffer = pygame.transform.rotate(buffer, self.rotation)
            self.screen.blit(buffer, (0, 0))
        else:
            target_surface.blit(buffer, (0, 0))

    def fade_in_surface(self, surface, x, y, fade_time, fade_steps=50):
        background = self.create_transparent_buffer((self.width, self.height))
        self.display_surface(
            self.images["background"], Position.CENTER, Position.CENTER, background
        )

        buffer = self.create_transparent_buffer(surface.get_size())
        fade_delay = round(
            fade_time / fade_steps * 1000
        )  # Time to delay in ms between each fade step

        for alpha in range(0, 255, round(255 / fade_steps)):
            buffer.blit(background, (-x, -y))
            surface.set_alpha(alpha)
            buffer.blit(surface, (0, 0))
            self.display_surface(buffer, x, y)
            pygame.display.update()
            pygame.time.wait(fade_delay)

    def display_current_page(self):
        self.display_surface(
            self.images["background"], Position.CENTER, Position.CENTER
        )
        pygame.display.update()

        page_data = self.pages[self.page]

        # Display the title
        if page_data["title"]:
            self.display_title()

        self.fade_in_surface(
            page_data["buffer"],
            self.textarea.x,
            page_data["text_position"],
            TEXT_FADE_TIME,
            TEXT_FADE_STEPS,
        )

        # Display the navigation buttons
        if self.page > 0:
            self.back_button.show()

        if self.page < len(self.pages) - 1:
            self.next_button.show()
        pygame.display.update()

    @staticmethod
    def create_transparent_buffer(size):
        if isinstance(size, (tuple, list)):
            (width, height) = size
        elif isinstance(size, dict):
            width = size["width"]
            height = size["height"]
        else:
            raise ValueError(f"Invalid size {size}. Should be tuple, list, or dict.")
        buffer = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        buffer = buffer.convert_alpha()
        return buffer

    def display_title(self):
        # Render the title as multiple lines if too big
        lines = self.wrap_text(self.title, self.fonts["title"], self.textarea.width)
        self.cursor["y"] = 0
        for line in lines:
            words = line.split(" ")
            self.cursor["x"] = (
                self.textarea.width // 2 - self.fonts["title"].size(line)[0] // 2
            )
            for word in words:
                text = self.fonts["title"].render(word + " ", True, TITLE_COLOR)
                self.fade_in_surface(
                    text,
                    self.cursor["x"] + self.textarea.x,
                    self.cursor["y"] + self.textarea.y,
                    TITLE_FADE_TIME,
                    TITLE_FADE_STEPS,
                )
                pygame.display.update()
                self.cursor["x"] += text.get_width()
                time.sleep(WORD_DELAY)
            self.cursor["y"] += self.fonts["title"].size(line)[1]

    def title_height(self):
        lines = self.wrap_text(self.title, self.fonts["title"], self.textarea.width)
        height = 0
        for line in lines:
            height += self.fonts["title"].size(line)[1]
        return height

    @staticmethod
    def wrap_text(text, font, width):
        lines = []
        line = ""
        for word in text.split(" "):
            if font.size(line + word)[0] < width:
                line += word + " "
            else:
                lines.append(line)
                line = word + " "
        lines.append(line)
        return lines

    def previous_page(self):
        if self.page > 0:
            self.page -= 1
            self.display_current_page()

    def next_page(self):
        if self.page < len(self.pages) - 1:
            self.page += 1
            self.display_current_page()

    def display_loading(self):
        self.display_surface(self.images["loading"], Position.CENTER, Position.CENTER)
        pygame.display.update()

    def display_welcome(self):
        self.display_surface(self.images["welcome"], Position.CENTER, Position.CENTER)
        pygame.display.update()

    # Parse out the title and story and separage into pages
    def parse_story(self, story):
        self.title = story.split("Title: ")[1].split("\n\n")[0]
        paragraphs = story.split("\n\n")[1:]
        page = self.add_page()
        for paragraph in paragraphs:
            lines = self.wrap_text(paragraph, self.fonts["text"], self.textarea.width)
            for line in lines:
                self.cursor["x"] = 0
                text = self.fonts["text"].render(line, True, TEXT_COLOR)
                self.display_surface(
                    text, self.cursor["x"], self.cursor["y"], page["buffer"]
                )
                self.cursor["y"] += self.fonts["text"].size(line)[1]
                if (
                    self.cursor["y"] + self.fonts["text"].get_height()
                    > page["buffer"].get_height()
                ):
                    page = self.add_page()
            if self.cursor["y"] > 0:
                self.cursor["y"] += PARAGRAPH_SPACING

    def add_page(self):
        page = {
            "title": False,
            "text_position": 0,
        }
        if len(self.pages) == 0:
            page["title"] = True
            page["text_position"] = self.title_height() + PARAGRAPH_SPACING
        page["buffer"] = self.create_transparent_buffer(
            (self.textarea.width, self.textarea.height - page["text_position"])
        )
        self.cursor["y"] = 0
        self.pages.append(page)
        return page

    # save settings?
    # load settings?
