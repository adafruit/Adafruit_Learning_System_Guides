# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import threading
import sys
import os
import re
import time
import argparse
import math
import configparser
from enum import Enum
from collections import deque

import board
import digitalio
import neopixel
import openai
import pygame
from rpi_backlight import Backlight
from adafruit_led_animation.animation.pulse import Pulse

from listener import Listener

# Base Path is the folder the script resides in
BASE_PATH = os.path.dirname(sys.argv[0])
if BASE_PATH != "":
    BASE_PATH += "/"

# General Settings
STORY_WORD_LENGTH = 800
REED_SWITCH_PIN = board.D17
NEOPIXEL_PIN = board.D18
API_KEYS_FILE = "~/keys.txt"
PROMPT_FILE = "/boot/bookprompt.txt"

# Quit Settings (Close book QUIT_CLOSES within QUIT_TIME_PERIOD to quit)
QUIT_CLOSES = 3
QUIT_TIME_PERIOD = 5  # Time period in Seconds
QUIT_DEBOUNCE_DELAY = 0.25  # Time to wait before counting next closeing

# Neopixel Settings
NEOPIXEL_COUNT = 1
NEOPIXEL_BRIGHTNESS = 0.2
NEOPIXEL_ORDER = neopixel.GRBW
NEOPIXEL_LOADING_COLOR = (0, 255, 0, 0)  # Loading/Dreaming (Green)
NEOPIXEL_SLEEP_COLOR = (0, 0, 0, 0)  # Sleeping (Off)
NEOPIXEL_WAITING_COLOR = (255, 255, 0, 0)  # Waiting for Input (Yellow)
NEOPIXEL_READING_COLOR = (0, 0, 255, 0)  # Reading (Blue)
NEOPIXEL_PULSE_SPEED = 0.1

# Image Settings
WELCOME_IMAGE = "welcome.png"
BACKGROUND_IMAGE = "paper_background.png"
LOADING_IMAGE = "loading.png"
BUTTON_BACK_IMAGE = "button_back.png"
BUTTON_NEXT_IMAGE = "button_next.png"
BUTTON_NEW_IMAGE = "button_new.png"

# Asset Paths
IMAGES_PATH = BASE_PATH + "images/"
FONTS_PATH = BASE_PATH + "fonts/"

# Font Path & Size
TITLE_FONT = (FONTS_PATH + "Desdemona Black Regular.otf", 48)
TITLE_COLOR = (0, 0, 0)
TEXT_FONT = (FONTS_PATH + "times new roman.ttf", 24)
TEXT_COLOR = (0, 0, 0)

# Delays Settings
# Used to control the speed of the text
WORD_DELAY = 0.1
TITLE_FADE_TIME = 0.05
TITLE_FADE_STEPS = 25
TEXT_FADE_TIME = 0.25
TEXT_FADE_STEPS = 51
ALSA_ERROR_DELAY = 1.0  # Delay to wait after an ALSA errors

# Whitespace Settings (in Pixels)
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
ENERGY_THRESHOLD = 300  # Energy level for mic to detect
RECORD_TIMEOUT = 30  # Maximum time in seconds to wait for speech

# Do some checks and Import API keys from API_KEYS_FILE
config = configparser.ConfigParser()

if os.geteuid() != 0:
    print("Please run this script as root.")
    sys.exit(1)
username = os.environ["SUDO_USER"]
user_homedir = os.path.expanduser(f"~{username}")
API_KEYS_FILE = API_KEYS_FILE.replace("~", user_homedir)

print(os.path.expanduser(API_KEYS_FILE))
config.read(os.path.expanduser(API_KEYS_FILE))
if not config.has_section("openai"):
    print("Please make sure API_KEYS_FILE points to a valid file.")
    sys.exit(1)
if "OPENAI_API_KEY" not in config["openai"]:
    print(
        "Please make sure your API keys file contains an OPENAI_API_KEY under the openai section."
    )
    sys.exit(1)
if len(config["openai"]["OPENAI_API_KEY"]) < 10:
    print("Please set OPENAI_API_KEY in your API keys file with a valid key.")
    sys.exit(1)
openai.api_key = config["openai"]["OPENAI_API_KEY"]

# Check that the prompt file exists and load it
if not os.path.isfile(PROMPT_FILE):
    print("Please make sure PROMPT_FILE points to a valid file.")
    sys.exit(1)


def strip_fancy_quotes(text):
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201C\u201D]", '"', text)
    return text


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
        self.buttons = {}
        self.width = 0
        self.height = 0
        self.textarea = None
        self.screen = None
        self.saved_screen = None
        self._sleeping = False
        self.sleep_check_delay = 0.1
        self._sleep_check_thread = None
        self._sleep_request = False
        self._running = True
        self._busy = False
        self._loading = False
        # Use a Double Ended Queue to handle the heavy lifting
        self._closing_times = deque(maxlen=QUIT_CLOSES)
        # Use a cursor to keep track of where we are in the text area
        self.cursor = {"x": 0, "y": 0}
        self.listener = None
        self.backlight = Backlight()
        self.pixels = neopixel.NeoPixel(
            NEOPIXEL_PIN,
            NEOPIXEL_COUNT,
            brightness=NEOPIXEL_BRIGHTNESS,
            pixel_order=NEOPIXEL_ORDER,
            auto_write=False,
        )
        self._prompt = ""
        self._load_thread = threading.Thread(target=self._handle_loading_status)
        self._load_thread.start()

    def start(self):
        # Output to the LCD instead of the console
        os.putenv("DISPLAY", ":0")

        self._set_status_color(NEOPIXEL_LOADING_COLOR)

        # Initialize the display
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.screen.fill((255, 255, 255))
        self.width = self.screen.get_height()
        self.height = self.screen.get_width()

        # Preload welcome image and display it
        self._load_image("welcome", WELCOME_IMAGE)
        self.display_welcome()

        # Load the prompt file
        with open(PROMPT_FILE, "r") as f:
            self._prompt = f.read()

        # Initialize the Listener
        self.listener = Listener(openai.api_key, ENERGY_THRESHOLD, RECORD_TIMEOUT)

        # Preload remaining images
        self._load_image("background", BACKGROUND_IMAGE)
        self._load_image("loading", LOADING_IMAGE)

        # Preload fonts
        self._load_font("title", TITLE_FONT)
        self._load_font("text", TEXT_FONT)

        # Add buttons
        back_button_image = pygame.image.load(IMAGES_PATH + BUTTON_BACK_IMAGE)
        next_button_image = pygame.image.load(IMAGES_PATH + BUTTON_NEXT_IMAGE)
        new_button_image = pygame.image.load(IMAGES_PATH + BUTTON_NEW_IMAGE)
        button_spacing = (
            self.width
            - (
                back_button_image.get_width()
                + next_button_image.get_width()
                + new_button_image.get_width()
            )
        ) // 4
        button_ypos = (
            self.height
            - PAGE_NAV_HEIGHT
            + (PAGE_NAV_HEIGHT - next_button_image.get_height()) // 2
        )

        self._load_button(
            "back",
            button_spacing,
            button_ypos,
            back_button_image,
            self.previous_page,
            self._display_surface,
        )

        self._load_button(
            "new",
            button_spacing * 2 + back_button_image.get_width(),
            button_ypos,
            new_button_image,
            self.new_story,
            self._display_surface,
        )

        self._load_button(
            "next",
            button_spacing * 3
            + back_button_image.get_width()
            + new_button_image.get_width(),
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

        # Start the sleep check thread after everything is initialized
        self._sleep_check_thread = threading.Thread(target=self._handle_sleep)
        self._sleep_check_thread.start()

        self._set_status_color(NEOPIXEL_READING_COLOR)

    def deinit(self):
        self._running = False
        self._sleep_check_thread.join()
        self._load_thread.join()
        self.backlight.power = True

    def _handle_sleep(self):
        reed_switch = digitalio.DigitalInOut(REED_SWITCH_PIN)
        reed_switch.direction = digitalio.Direction.INPUT
        reed_switch.pull = digitalio.Pull.UP

        while self._running:
            if self._sleeping and reed_switch.value:  # Book Open
                self._wake()
            elif not self._sleeping and not reed_switch.value:
                self._sleep()
            time.sleep(self.sleep_check_delay)

    def _handle_loading_status(self):
        pulse = Pulse(
            self.pixels,
            speed=NEOPIXEL_PULSE_SPEED,
            color=NEOPIXEL_LOADING_COLOR,
            period=3,
        )

        while self._running:
            if self._loading:
                pulse.animate()
                time.sleep(0.1)

        # Turn off the Neopixels
        self.pixels.fill(0)
        self.pixels.show()

    def _set_status_color(self, status_color):
        if status_color not in [
            NEOPIXEL_READING_COLOR,
            NEOPIXEL_WAITING_COLOR,
            NEOPIXEL_SLEEP_COLOR,
            NEOPIXEL_LOADING_COLOR,
        ]:
            raise ValueError(f"Invalid status color {status_color}.")

        # Handle loading color by setting the loading flag
        self._loading = status_color == NEOPIXEL_LOADING_COLOR

        # Handle other status colors by setting the neopixels
        if status_color != NEOPIXEL_LOADING_COLOR:
            self.pixels.fill(status_color)
            self.pixels.show()

    def handle_events(self):
        if not self._sleeping:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mousedown_event(event)
        time.sleep(0.1)

    def _handle_mousedown_event(self, event):
        if event.button == 1:
            # If button pressed while visible, trigger action
            coords = self._rotate_mouse_pos(event.pos)
            for button in self.buttons.values():
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

    def _load_button(self, name, x, y, image, action, display_surface):
        self.buttons[name] = Button(x, y, image, action, display_surface)

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

        def draw_alpha(alpha):
            buffer.blit(background, (-x, -y))
            surface.set_alpha(alpha)
            buffer.blit(surface, (0, 0))
            self._display_surface(buffer, x, y)
            pygame.display.update()

        for alpha in range(0, 255, round(255 / fade_steps)):
            draw_alpha(alpha)
            pygame.time.wait(fade_delay)
            if self._sleep_request:
                draw_alpha(255)  # Finish up quickly
                return

    def display_current_page(self):
        self._busy = True
        self._display_surface(self.images["background"], 0, 0)
        pygame.display.update()

        print(f"Loading page {self.page} of {len(self.pages)}")
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
            self.buttons["back"].show()
        self.buttons["next"].show()
        self.buttons["new"].show()
        pygame.display.update()
        self._busy = False

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
        delay_value = WORD_DELAY
        for line in lines:
            words = line.split(" ")
            self.cursor["x"] = (
                self.textarea.width // 2 - self.fonts["title"].size(line)[0] // 2
            )
            for word in words:
                text = self.fonts["title"].render(word + " ", True, TITLE_COLOR)
                if self._sleep_request:
                    delay_value = 0
                    self._display_surface(
                        text,
                        self.cursor["x"] + self.textarea.x,
                        self.cursor["y"] + self.textarea.y,
                    )
                else:
                    self._fade_in_surface(
                        text,
                        self.cursor["x"] + self.textarea.x,
                        self.cursor["y"] + self.textarea.y,
                        TITLE_FADE_TIME,
                        TITLE_FADE_STEPS,
                    )

                pygame.display.update()
                self.cursor["x"] += text.get_width()
                time.sleep(delay_value)
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
                self.generate_new_story()
        self.display_current_page()

    def new_story(self):
        self.generate_new_story()
        self.display_current_page()

    def display_loading(self):
        self._display_surface(self.images["loading"], 0, 0)
        pygame.display.update()
        self._set_status_color(NEOPIXEL_LOADING_COLOR)

    def display_welcome(self):
        self._display_surface(self.images["welcome"], 0, 0)
        pygame.display.update()

    def display_message(self, message):
        self._busy = True
        self._display_surface(self.images["background"], 0, 0)
        height = self._title_text_height(message)
        self._display_title_text(message, self.height // 2 - height // 2)
        self._busy = False

    def load_story(self, story):
        # Parse out the title and story and render into pages
        self._busy = True
        self.pages = []
        if not story.startswith("Title: "):
            print("Unexpected story format from ChatGPT. Missing Title.")
            title = "A Story"
        else:
            title = story.split("Title: ")[1].split("\n\n")[0]
        page = self._add_page(title)
        paragraphs = story.split("\n\n")[1:]
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
        self._set_status_color(NEOPIXEL_READING_COLOR)
        self._busy = False

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

    def generate_new_story(self):
        self._busy = True
        self.display_message("Speak aloud the story you wish to read.")

        if self._sleep_request:
            self._busy = False
            time.sleep(0.2)
            print("Not busy anymore")
            return

        def show_waiting():
            # Pause for a beat because the listener doesn't
            # immediately start listening sometimes
            time.sleep(ALSA_ERROR_DELAY)
            self.pixels.fill(NEOPIXEL_WAITING_COLOR)
            self.pixels.show()

        self.listener.listen(ready_callback=show_waiting)

        if self._sleep_request:
            self._busy = False
            return

        if not self.listener.speech_waiting():
            # No response from user, so return
            return

        story_request = self.listener.recognize()

        story_prompt = self._make_story_prompt(story_request)
        self.display_loading()
        response = self._sendchat(story_prompt)
        if self._sleep_request:
            self._busy = False
            return
        print(response)

        self._busy = True
        self.stories.append(response)
        self.story = len(self.stories) - 1
        self.page = 0
        self._busy = False

        self.load_story(response)

    def _sleep(self):
        # Set a sleep request flag so that any busy threads know to finish up
        self._sleep_request = True
        if self.listener.is_listening():
            self.listener.stop_listening()
        while self._busy:
            print("Still busy")
            time.sleep(0.1)
        self._sleep_request = False

        if (
            len(self._closing_times) == 0
            or (time.monotonic() - self._closing_times[-1]) > QUIT_DEBOUNCE_DELAY
        ):
            self._closing_times.append(time.monotonic())

        # Check if we've closed the book a certain number of times
        # within a certain number of seconds
        if (
            len(self._closing_times) == QUIT_CLOSES
            and self._closing_times[-1] - self._closing_times[0] < QUIT_TIME_PERIOD
        ):
            self._running = False
            return

        self._sleeping = True
        self._set_status_color(NEOPIXEL_SLEEP_COLOR)
        self.sleep_check_delay = 0
        self.saved_screen = self.screen.copy()
        self.screen.fill((0, 0, 0))
        pygame.display.update()
        self.backlight.power = False

    def _wake(self):
        # Turn on the screen
        self.backlight.power = True
        if self.saved_screen:
            self.screen.blit(self.saved_screen, (0, 0))
            pygame.display.update()
            self.saved_screen = None
        self.sleep_check_delay = 0.1
        self._set_status_color(NEOPIXEL_READING_COLOR)
        self._sleeping = False

    def _make_story_prompt(self, request):
        return self._prompt.format(
            STORY_WORD_LENGTH=STORY_WORD_LENGTH, STORY_REQUEST=request
        )

    def _sendchat(self, prompt):
        response = ""
        print("Sending to chatGPT")
        # Package up the text to send to ChatGPT
        completion = openai.ChatCompletion.create(
            model=CHATGPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )

        for chunk in completion:
            if "delta" in chunk.choices[0] and "content" in chunk.choices[0]["delta"]:
                response += chunk.choices[0]["delta"]["content"]
            if self._sleep_request:
                return None

        # Send the heard text to ChatGPT and return the result
        return strip_fancy_quotes(response)

    @property
    def running(self):
        return self._running

    @property
    def sleeping(self):
        return self._sleeping


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
    try:
        book.start()
        while len(book.pages) == 0:
            if not book.sleeping:
                book.generate_new_story()
        book.display_current_page()

        while book.running:
            book.handle_events()
    except KeyboardInterrupt:
        pass
    finally:
        book.deinit()
        pygame.quit()


if __name__ == "__main__":
    main(parse_args())
