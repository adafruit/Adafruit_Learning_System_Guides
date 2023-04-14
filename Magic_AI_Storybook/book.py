# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import sys
import os
import time
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
CHARACTER_DELAY = 0.03
WORD_DELAY = 0.2
SENTENCE_DELAY = 1
PARAGRAPH_DELAY = 2

#   Letter by Letter
# CHARACTER_DELAY = 0.1
# WORD_DELAY = 0
# SENTENCE_DELAY = 0
# PARAGRAPH_DELAY = 0

#   Word by Word
# CHARACTER_DELAY = 0
# WORD_DELAY = 0.3
# SENTENCE_DELAY = 0.5
# PARAGRAPH_DELAY = 0

#   No Delays
# CHARACTER_DELAY = 0
# WORD_DELAY = 0
# SENTENCE_DELAY = 0
# PARAGRAPH_DELAY = 0


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
    def __init__(self, x, y, image, action):
        self.x = x
        self.y = y
        self.image = image
        self.action = action
        self._width = self.image.get_width()
        self._height = self.image.get_height()

    def is_in_bounds(self, position):
        x, y = position
        return (
            self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
        )

    def is_pressed(self):
        pass

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height


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
        self.cursor = None

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
            button_spacing, button_ypos, back_button_image, self.previous_page
        )
        self.next_button = Button(
            self.width - button_spacing - next_button_image.get_width(),
            button_ypos,
            next_button_image,
            self.next_page,
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
                    # If clicked in text area and book is still rendering, skip to the end
                    print(f"Left mouse button pressed at {event.pos}")
                    # If button pressed while visible, trigger action
                    if self.back_button.is_in_bounds(event.pos):
                        self.back_button.action()
            elif event.type == pygame.MOUSEBUTTONUP:
                # Not sure if we will need this
                print("Mouse button has been released")

    def add_page(self, paragraph=0, word=0):
        # Add rendered page information to make flipping between them easier
        self.pages.append(
            {
                "paragraph": paragraph,
                "word": word,
            }
        )

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
    def display_image(self, image, x=Position.CENTER, y=Position.CENTER, surface=None):
        buffer = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
        buffer = buffer.convert_alpha()
        buffer.blit(image, self.get_position(image, x, y))
        if surface is None:
            buffer = pygame.transform.rotate(buffer, self.rotation)
            self.screen.blit(buffer, (0, 0))
        else:
            surface.blit(buffer, (0, 0))

    def display_current_page(self):
        self.display_image(self.images["background"], Position.CENTER, Position.CENTER)
        pygame.display.update()

        # Use a cursor to keep track of where we are on the page
        # These values are relative to the text area
        self.cursor = {"x": 0, "y": 0}

        # Display the title
        if self.page == 0:
            title = self.render_title()
            self.display_image(
                title,
                self.cursor["x"] + self.textarea.x,
                self.cursor["y"] + self.textarea.y,
            )
            pygame.display.update()
            self.cursor["y"] += title.get_height() + PARAGRAPH_SPACING
            time.sleep(PARAGRAPH_DELAY)

        self.display_page_text()

        # Display the navigation buttons
        if self.page > 0:
            self.display_image(
                self.back_button.image, self.back_button.x, self.back_button.y
            )

        # TODO: If we are on the last page, don't display the next button
        self.display_image(
            self.next_button.image, self.next_button.x, self.next_button.y
        )
        pygame.display.update()

    def render_character(self, character):
        return self.fonts["text"].render(character, True, (0, 0, 0))

    def display_page_text(self):
        # TODO: We need an accurate way to determine when a
        # previous page has already been added so we don't add it again

        paragraph_number = self.pages[self.page]["paragraph"]
        word_number = self.pages[self.page]["word"]

        # Display a paragraph at a time
        while self.paragraph_number < len(self.paragraphs):
            paragraph = self.paragraphs[paragraph_number]
            while word_number < len(paragraph):
                word = paragraph[word_number]
                # Check if there is enough space to display the word
                if (
                    self.cursor["x"] + self.fonts["text"].size(word)[0]
                    > self.textarea.width
                ):
                    # If not, move to the next line
                    self.cursor["x"] = 0
                    self.cursor["y"] += (
                        self.fonts["text"].get_height() + EXTRA_LINE_SPACING
                    )
                    # If we have reached the end of the page, stop displaying paragraphs
                    if (
                        self.cursor["y"] + self.fonts["text"].get_height()
                        > self.textarea.height
                    ):
                        self.add_page(paragraph_number, word_number)
                        return

                # Display the word one character at a time
                for character in word:
                    character_surface = self.render_character(character)
                    self.display_image(
                        character_surface,
                        self.cursor["x"] + self.textarea.x,
                        self.cursor["y"] + self.textarea.y,
                    )
                    pygame.display.update()
                    self.cursor["x"] += character_surface.get_width() + 1
                    if character != " ":
                        time.sleep(CHARACTER_DELAY)

                # Advance the cursor by a spaces width
                self.cursor["x"] += self.render_character(" ").get_width() + 1

                # Look at last character only to avoid long delays on stuff
                # like "!!!" or "?!" or "..."
                if word[-1:] in [".", "!", "?"]:
                    time.sleep(SENTENCE_DELAY)
                else:
                    time.sleep(WORD_DELAY)
                word_number += 1

            # We have reached the end of the paragraph, so we need to move to the next line
            time.sleep(PARAGRAPH_DELAY)
            self.cursor["x"] = 0
            self.cursor["y"] += self.fonts["text"].get_height() + PARAGRAPH_SPACING
            word_number = 0
            paragraph_number += 1

            # If we have reached the end of the page, stop displaying paragraphs
            if (
                self.cursor["y"] + self.fonts["text"].get_height()
                > self.textarea.height
            ):
                self.add_page(paragraph_number, word_number)
                return

    @staticmethod
    def create_transparent_buffer(size):
        if isinstance(size, (tuple, list)):
            (width, height) = size
        elif isinstance(size, dict):
            width = size["width"]
            height = size["height"]
        buffer = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        buffer = buffer.convert_alpha()
        return buffer

    def render_title(self):
        # The title should be centered and wrapped if it is too wide for the screen
        buffer = self.create_transparent_buffer(self.textarea.size)

        # Render the title as multiple lines if too big
        lines = self.wrap_text(self.title, self.fonts["title"], self.textarea.width)
        text_height = 0
        for line in lines:
            text = self.fonts["title"].render(line, True, TITLE_COLOR)
            buffer.blit(
                text, (buffer.get_width() // 2 - text.get_width() // 2, text_height)
            )
            text_height += text.get_height()

        new_buffer = self.create_transparent_buffer((self.textarea.width, text_height))
        new_buffer.blit(buffer, (0, 0))

        return new_buffer

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
        self.display_image(self.images["loading"], Position.CENTER, Position.CENTER)
        pygame.display.update()

    def display_welcome(self):
        self.display_image(self.images["welcome"], Position.CENTER, Position.CENTER)
        pygame.display.update()

    # Parse out the title and story and separage into pages
    def parse_story(self, story):
        self.title = story.split("Title: ")[1].split("\n\n")[0]
        paragraphs = story.split("\n\n")[1:]
        for paragraph in paragraphs:
            self.paragraphs.append(paragraph.split(" "))
        self.add_page()

    # save settings
    # load settings
