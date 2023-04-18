# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import threading
import sys
import os
import time
import argparse
import math
import pickle
from enum import Enum
from tempfile import NamedTemporaryFile

import board
import digitalio
import openai
import pygame
from rpi_backlight import Backlight

from listener import Listener

STORY_WORD_LENGTH = 800
REED_SWITCH_PIN = board.D17

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
TITLE_FONT = (FONTS_PATH + "Desdemona Black Regular.otf", 48)
TITLE_COLOR = (0, 0, 0)
TEXT_FONT = (FONTS_PATH + "times new roman.ttf", 24)
TEXT_COLOR = (0, 0, 0)

# Delays to control the speed of the text
WORD_DELAY = 0.1
WELCOME_IMAGE_DELAY = 3
TITLE_FADE_TIME = 0.05
TITLE_FADE_STEPS = 25
TEXT_FADE_TIME = 0.25
TEXT_FADE_STEPS = 51

# Whitespace Settings in Pixels
PAGE_TOP_MARGIN = 20
PAGE_SIDE_MARGIN = 20
PAGE_BOTTOM_MARGIN = 0
PAGE_NAV_HEIGHT = 100
EXTRA_LINE_SPACING = 0
PARAGRAPH_SPACING = 30

# ChatGPT Parameters
SYSTEM_ROLE = "You are a master AI Storyteller that can tell a story of any length."
CHATGPT_MODEL = "gpt-3.5-turbo"
WHISPER_MODEL = "whisper-1"

# Speech Recognition Parameters
ENERGY_THRESHOLD = 1000  # Energy level for mic to detect
PHRASE_TIMEOUT = 3.0  # Space between recordings for sepating phrases
RECORD_TIMEOUT = 30

# Import keys from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

if openai.api_key is None:
    print("Please set the OPENAI_API_KEY environment variable first.")
    sys.exit(1)


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
        self._draw_function(self.image, self.x, self.y)
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
        self.pages = []
        self.stories = []
        self.story = 0
        self.rotation = rotation
        self.images = {}
        self.fonts = {}
        self.width = 0
        self.height = 0
        self.back_button = None
        self.next_button = None
        self.textarea = None
        self.screen = None
        self.saved_screen = None
        self.sleeping = False
        self.sleep_check_delay = 0.1
        self._sleep_check_thread = None
        self.running = True
        # Use a cursor to keep track of where we are in the text area
        self.cursor = {"x": 0, "y": 0}
        self.listener = Listener(ENERGY_THRESHOLD, PHRASE_TIMEOUT, RECORD_TIMEOUT)
        self.backlight = Backlight()

    def init(self):
        # Output to the LCD instead of the console
        os.putenv("DISPLAY", ":0")

        # Initialize the display
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_allow_screensaver(False)
        self.width = self.screen.get_height()
        self.height = self.screen.get_width()

        # Preload images
        self._load_image("welcome", WELCOME_IMAGE)
        self._load_image("background", BACKGROUND_IMAGE)
        self._load_image("loading", LOADING_IMAGE)

        # Preload fonts
        self._load_font("title", TITLE_FONT)
        self._load_font("text", TEXT_FONT)

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
            self._display_surface,
        )
        self.next_button = Button(
            self.width - button_spacing - next_button_image.get_width(),
            button_ypos,
            next_button_image,
            self.next_page,
            self._display_surface,
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
        self._sleep_check_thread = threading.Thread(target=self._handle_sleep)
        self._sleep_check_thread.start()

    def deinit(self):
        self.running = False
        self._sleep_check_thread.join()
        self.backlight.power = True

    def _handle_sleep(self):
        reed_switch = digitalio.DigitalInOut(REED_SWITCH_PIN)
        reed_switch.direction = digitalio.Direction.INPUT
        reed_switch.pull = digitalio.Pull.UP

        while self.running:
            if self.sleeping and reed_switch.value:  # Book Open
                self.wake()
            elif not self.sleeping and not reed_switch.value:  # Book Closed
                self.sleep()
            time.sleep(self.sleep_check_delay)

    def handle_events(self):
        if not self.sleeping:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mousedown_event(event)

    def _handle_mousedown_event(self, event):
        if event.button == 1:
            # If button pressed while visible, trigger action
            coords = self._rotate_mouse_pos(event.pos)
            for button in [self.back_button, self.next_button]:
                if button.visible and button.is_in_bounds(coords):
                    button.action()

    def _rotate_mouse_pos(self, point):
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

    def _load_image(self, name, filename):
        try:
            image = pygame.image.load(IMAGES_PATH + filename)
            self.images[name] = image
        except pygame.error:
            pass

    def _load_font(self, name, details):
        self.fonts[name] = pygame.font.Font(details[0], details[1])

    def _display_surface(self, surface, x=0, y=0, target_surface=None):
        # Display a surface either positionally or with a specific x,y coordinate
        buffer = self._create_transparent_buffer((self.width, self.height))
        buffer.blit(surface, (x, y))
        if target_surface is None:
            buffer = pygame.transform.rotate(buffer, self.rotation)
            self.screen.blit(buffer, (0, 0))
        else:
            target_surface.blit(buffer, (0, 0))

    def _fade_in_surface(self, surface, x, y, fade_time, fade_steps=50):
        background = self._create_transparent_buffer((self.width, self.height))
        self._display_surface(self.images["background"], 0, 0, background)

        buffer = self._create_transparent_buffer(surface.get_size())
        fade_delay = round(
            fade_time / fade_steps * 1000
        )  # Time to delay in ms between each fade step

        for alpha in range(0, 255, round(255 / fade_steps)):
            buffer.blit(background, (-x, -y))
            surface.set_alpha(alpha)
            buffer.blit(surface, (0, 0))
            self._display_surface(buffer, x, y)
            pygame.display.update()
            pygame.time.wait(fade_delay)

    def display_current_page(self):
        self._display_surface(self.images["background"], 0, 0)
        pygame.display.update()

        page_data = self.pages[self.page]

        # Display the title
        if page_data["title"]:
            self._display_title_text(page_data["title"])

        self._fade_in_surface(
            page_data["buffer"],
            self.textarea.x,
            self.textarea.y + page_data["text_position"],
            TEXT_FADE_TIME,
            TEXT_FADE_STEPS,
        )

        # Display the navigation buttons
        if self.page > 0 or self.story > 0:
            self.back_button.show()
        self.next_button.show()
        pygame.display.update()

    @staticmethod
    def _create_transparent_buffer(size):
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

    def _display_title_text(self, text, y=0):
        # Render the title as multiple lines if too big
        lines = self._wrap_text(text, self.fonts["title"], self.textarea.width)
        self.cursor["y"] = y
        for line in lines:
            words = line.split(" ")
            self.cursor["x"] = (
                self.textarea.width // 2 - self.fonts["title"].size(line)[0] // 2
            )
            for word in words:
                text = self.fonts["title"].render(word + " ", True, TITLE_COLOR)
                self._fade_in_surface(
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

    def _title_text_height(self, text):
        lines = self._wrap_text(text, self.fonts["title"], self.textarea.width)
        height = 0
        for line in lines:
            height += self.fonts["title"].size(line)[1]
        return height

    @staticmethod
    def _wrap_text(text, font, width):
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
        if self.page > 0 or self.story > 0:
            self.page -= 1
            if self.page < 0:
                self.story -= 1
                self.load_story(self.stories[self.story])
                self.page = len(self.pages) - 1
            self.display_current_page()

    def next_page(self):
        self.page += 1
        if self.page >= len(self.pages):
            if self.story < len(self.stories) - 1:
                self.story += 1
                self.load_story(self.stories[self.story])
                self.page = 0
            else:
                self.new_story()
        self.display_current_page()

    def display_loading(self):
        self._display_surface(self.images["loading"], 0, 0)
        pygame.display.update()

    def display_welcome(self):
        self._display_surface(self.images["welcome"], 0, 0)
        pygame.display.update()

    def display_message(self, message):
        self._display_surface(self.images["background"], 0, 0)
        height = self._title_text_height(message)
        self._display_title_text(message, self.height // 2 - height // 2)

    def load_story(self, story):
        # Parse out the title and story and render into pages
        self.pages = []
        title = story.split("Title: ")[1].split("\n\n")[0]
        page = self._add_page(title)
        paragraphs = story.split("\n\n")[1:]
        paragraphs.append("The End.")
        for paragraph in paragraphs:
            lines = self._wrap_text(paragraph, self.fonts["text"], self.textarea.width)
            for line in lines:
                self.cursor["x"] = 0
                text = self.fonts["text"].render(line, True, TEXT_COLOR)
                if (
                    self.cursor["y"] + self.fonts["text"].get_height()
                    > page["buffer"].get_height()
                ):
                    page = self._add_page()

                self._display_surface(
                    text, self.cursor["x"], self.cursor["y"], page["buffer"]
                )
                self.cursor["y"] += self.fonts["text"].size(line)[1]

            if self.cursor["y"] > 0:
                self.cursor["y"] += PARAGRAPH_SPACING
        print(f"Loaded story at index {self.story} with {len(self.pages)} pages")

    def _add_page(self, title=None):
        page = {
            "title": title,
            "text_position": 0,
        }
        if title:
            page["text_position"] = self._title_text_height(title) + PARAGRAPH_SPACING
        page["buffer"] = self._create_transparent_buffer(
            (self.textarea.width, self.textarea.height - page["text_position"])
        )
        self.cursor["y"] = 0
        self.pages.append(page)
        return page

    def load_settings(self):
        storydata = {
            "history": [],
            "settings": {
                "story": 0,
                "page": 0,
            },
        }
        # Load the story data if it exists
        if os.path.exists(os.path.dirname(sys.argv[0]) + "storydata.bin"):
            print("Loading previous story data")
            with open(os.path.dirname(sys.argv[0]) + "storydata.bin", "rb") as f:
                storydata = pickle.load(f)
                self.stories = storydata["history"]
                self.story = storydata["settings"]["story"]

        if storydata["history"] and storydata["settings"]["story"] < len(
            storydata["history"]
        ):
            # Load the last story
            self.load_story(storydata["history"][storydata["settings"]["story"]])
            self.page = storydata["settings"]["page"]
            # If something changed and caused the current page to be too
            # large, just go to the last page of the story
            if self.page >= len(self.pages):
                self.page = len(self.pages) - 1

    def save_settings(self):
        storydata = {
            "history": self.stories,
            "settings": {
                "story": self.story,
                "page": self.page,
            },
        }
        with open(os.path.dirname(sys.argv[0]) + "storydata.bin", "wb") as f:
            pickle.dump(storydata, f)

    def new_story(self):
        self.display_message("What story would you like to hear today?")

        while not self.listener.speech_waiting():
            self.listener.listen()

        story_request = self._transcribe(self.listener.get_speech())
        story_prompt = self._make_story_prompt(story_request)

        print("Getting new response. This may take a minute or two...")
        self.display_loading()
        response = self._sendchat(story_prompt)
        with open(os.path.dirname(sys.argv[0]) + "response.txt", "w") as f:
            f.write(response)
        print(response)

        self.stories.append(response)
        self.story = len(self.stories) - 1
        self.page = 0

        self.load_story(response)

    def sleep(self):
        self.sleeping = True
        self.sleep_check_delay = 1
        self.saved_screen = self.screen.copy()
        self.screen.fill((0, 0, 0))
        pygame.display.update()
        self.backlight.power = False

    def wake(self):
        # Turn on the screen
        self.backlight.power = True
        if self.saved_screen:
            self.screen.blit(self.saved_screen, (0, 0))
            pygame.display.update()
            self.saved_screen = None
        self.sleep_check_delay = 0.1
        self.sleeping = False

    @staticmethod
    def _make_story_prompt(request):
        return (
            f"Write a complete story with a title and a body of approximately "
            f"{STORY_WORD_LENGTH} words long and a happy ending. The specific "
            f'story request is "{request}". '
        )

    @staticmethod
    def _transcribe(wav_data):
        # Transcribe the audio data to text using Whisper
        print("Transcribing...")
        attempts = 0
        while attempts < 3:
            try:
                with NamedTemporaryFile(suffix=".wav") as temp_file:
                    result = openai.Audio.translate_raw(
                        WHISPER_MODEL, wav_data, temp_file.name
                    )
                    return result["text"].strip()
            except (openai.error.ServiceUnavailableError, openai.error.APIError):
                time.sleep(3)
            attempts += 1
        return "I wasn't able to understand you. Please repeat that."

    @staticmethod
    def _sendchat(prompt):
        # Package up the text to send to ChatGPT
        completion = openai.ChatCompletion.create(
            model=CHATGPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": prompt},
            ],
        )
        # Send the heard text to ChatGPT and return the result
        return completion.choices[0].message.content


def parse_args():
    parser = argparse.ArgumentParser()
    # Book will only be rendered vertically for the sake of simplicity
    parser.add_argument(
        "--rotation",
        type=int,
        choices=[90, 270],
        dest="rotation",
        action="store",
        default=90,
        help="Rotate everything on the display by this amount",
    )
    return parser.parse_args()


def main(args):
    book = Book(args.rotation)
    book.init()

    try:
        # Center and display the image
        book.display_welcome()
        start_time = time.monotonic()
        book.load_settings()

        # Continue showing the image until the minimum amount of time has passed
        time.sleep(max(0, WELCOME_IMAGE_DELAY - (time.monotonic() - start_time)))

        if not book.stories:
            book.new_story()

        book.display_current_page()

        while True:
            if not book.sleeping:
                book.handle_events()
                time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        book.save_settings()
        book.deinit()


if __name__ == "__main__":
    main(parse_args())

# TODO:
# * Play with prompt parameters
