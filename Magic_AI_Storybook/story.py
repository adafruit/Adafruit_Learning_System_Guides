# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import argparse
import os
import sys
from tempfile import NamedTemporaryFile
import signal

import openai

#from listener import Listener
from book import Book

STORY_WORD_LENGTH = 800
WELCOME_IMAGE_DELAY = 3
# TODO: This will be verbally prompted later
STORY_REQUEST = (
    "Please tell me a story about a fairy who lives in an"
    " oak tree and a little girl named Luna who goes on an adventure."
)

# ChatGPT Parameters
SYSTEM_ROLE = "You are a master AI Storyteller that can tell a story of any length."
CHATGPT_MODEL = "gpt-3.5-turbo"
WHISPER_MODEL = "whisper-1"

# Speech Recognition Parameters
ENERGY_THRESHOLD = 1000  # Energy level for mic to detect
PHRASE_TIMEOUT = 3.0  # Space between recordings for sepating phrases
RECORD_TIMEOUT = 30

# TODO: Tweak this to fix the issue of missing words
STORY_PROMPT = (
    f'Write a complete story with a title and a body of approximately '
    f'{STORY_WORD_LENGTH} words long and a happy ending. The specific '
    f'story request is "{STORY_REQUEST}". '
)

# Not sure if we will need this
def dont_quit(_signal, _frame):
    print("Caught signal: {}".format(_signal))


signal.signal(signal.SIGHUP, dont_quit)

# Import keys from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

if openai.api_key is None:
    print("Please set the OPENAI_API_KEY environment variable first.")
    sys.exit(1)

# Package up the text to send to ChatGPT
def sendchat(prompt):
    completion = openai.ChatCompletion.create(
        model=CHATGPT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_ROLE},
            {"role": "user", "content": prompt},
        ],
    )
    # Send the heard text to ChatGPT and return the result
    return completion.choices[0].message.content


# Transcribe the audio data to text using Whisper
def transcribe(wav_data):
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

    # Center and display the image
    book.display_welcome()
    time.sleep(WELCOME_IMAGE_DELAY)

    # To save on credits just use the response from last time
    if os.path.exists(os.path.dirname(sys.argv[0]) + "response.txt"):
        print("Using cached response")
        with open(os.path.dirname(sys.argv[0]) + "response.txt", "r") as f:
            response = f.read()
    else:
        print("Getting new response. This may take a minute or two...")
        book.display_loading()
        response = sendchat(STORY_PROMPT)
        with open(os.path.dirname(sys.argv[0]) + "response.txt", "w") as f:
            f.write(response)
        print(response)

    book.parse_story(response)
    book.display_current_page()

    while True:
        book.handle_events()
        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main(parse_args())
    except KeyboardInterrupt:
        pass
