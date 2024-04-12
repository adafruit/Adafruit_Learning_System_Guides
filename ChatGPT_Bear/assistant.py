# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import threading
import os
import sys
import time
import random
import configparser
from tempfile import NamedTemporaryFile

import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI

import board
import digitalio
from adafruit_motorkit import MotorKit

from listener import Listener

API_KEYS_FILE = "~/keys.txt"

# ChatGPT Parameters
SYSTEM_ROLE = (
    "You are a helpful voice assistant in the form of a talking teddy bear"
    " that answers questions and gives information"
)
CHATGPT_MODEL = "gpt-3.5-turbo"
WHISPER_MODEL = "whisper-1"

# Azure Parameters
AZURE_SPEECH_VOICE = "en-GB-OliverNeural"
DEVICE_ID = None

# Speech Recognition Parameters
ENERGY_THRESHOLD = 1000  # Energy level for mic to detect
RECORD_TIMEOUT = 30

# Motor Parameters
ARM_MOVEMENT_TIME = 0.5
BASE_MOUTH_DURATION = 0.2  # A higher number means slower mouth movement
SPEECH_VARIANCE = 0.1  # Higher allows more mouth movement variance.
                       # It pauses for BASE_MOUTH_DURATION ± SPEECH_VARIANCE
MOTOR_DUTY_CYCLE = 1.0  # Lower provides less power to the motors

# Do some checks and Import API keys from API_KEYS_FILE
config = configparser.ConfigParser()

username = os.environ["USER"]
user_homedir = os.path.expanduser(f"~{username}")
API_KEYS_FILE = API_KEYS_FILE.replace("~", user_homedir)

def get_config_value(section, key, min_length=None):
    if not config.has_section(section):
        print("Please make sure API_KEYS_FILE points to "
              f"a valid file and has an [{section}] section.")
        sys.exit(1)
    if key not in config[section]:
        print(
            f"Please make sure your API keys file contains an {key} under the {section} section."
        )
        sys.exit(1)
    value = config[section][key]
    if min_length and len(value) < min_length:
        print(f"Please set {key} in your API keys file with a valid key.")
        sys.exit(1)
    return config[section][key]

print(os.path.expanduser(API_KEYS_FILE))
config.read(os.path.expanduser(API_KEYS_FILE))
openai = OpenAI(
    # This is the default and can be omitted
    api_key=get_config_value("openai", "OPENAI_API_KEY", 10)
)

speech_key = get_config_value("azure", "SPEECH_KEY", 15)
service_region = get_config_value("azure", "SPEECH_REGION")

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = AZURE_SPEECH_VOICE


def sendchat(prompt):
    response = ""
    stream = openai.chat.completions.create(
        model=CHATGPT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_ROLE},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    # Send the heard text to ChatGPT and return the result
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content

    # Send the heard text to ChatGPT and return the result
    return response

def transcribe(wav_data):
    # Read the transcription.
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


class Bear:
    def __init__(self, azure_speech_config):
        kit = MotorKit(i2c=board.I2C())
        self._arms_motor = kit.motor1
        self._mouth_motor = kit.motor2

        # Setup Foot Button
        self._foot_button = digitalio.DigitalInOut(board.D16)
        self._foot_button.direction = digitalio.Direction.INPUT
        self._foot_button.pull = digitalio.Pull.UP

        self.do_mouth_movement = False
        self._mouth_thread = threading.Thread(target=self.move_mouth, daemon=True)
        self._mouth_thread.start()
        if DEVICE_ID is None:
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        else:
            audio_config = speechsdk.audio.AudioOutputConfig(device_name=DEVICE_ID)
        self._speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=azure_speech_config, audio_config=audio_config
        )

        self._speech_synthesizer.synthesizing.connect(self.start_moving_mouth)
        self._speech_synthesizer.synthesis_completed.connect(self.stop_moving_mouth)

    def start_moving_mouth(self, _event):
        self.do_mouth_movement = True

    def stop_moving_mouth(self, _event):
        self.do_mouth_movement = False

    def deinit(self):
        self.do_mouth_movement = False
        self._mouth_thread.join()
        self._arms_motor.throttle = None
        self._mouth_motor.throttle = None
        self._speech_synthesizer.synthesis_started.disconnect_all()
        self._speech_synthesizer.synthesis_completed.disconnect_all()

    def _move_arms_motor(self, dir_up=True):
        direction = -1 if dir_up else 1
        self._arms_motor.throttle = MOTOR_DUTY_CYCLE * direction
        time.sleep(ARM_MOVEMENT_TIME)
        # Remove Power from the motor to avoid overheating
        self._arms_motor.throttle = None

    def _move_mouth_motor(self, dir_open=True):
        duration = (
            BASE_MOUTH_DURATION
            + random.random() * SPEECH_VARIANCE
            - (SPEECH_VARIANCE / 2)
        )
        # Only power the motor while opening and let the spring close it
        self._mouth_motor.throttle = MOTOR_DUTY_CYCLE if dir_open else None
        time.sleep(duration)
        # Remove Power from the motor and let close to avoid overheating
        self._mouth_motor.throttle = None

    def foot_pressed(self):
        return not self._foot_button.value

    def move_mouth(self):
        print("Starting mouth movement thread")
        while True:
            if self.do_mouth_movement:
                self._move_mouth_motor(dir_open=True)
                self._move_mouth_motor(dir_open=False)

    def move_arms(self, hide=True):
        self._move_arms_motor(dir_up=hide)

    def speak(self, text):
        result = self._speech_synthesizer.speak_text_async(text).get()

        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Speech synthesized for text [{}]".format(text))
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))

def main():
    listener = Listener(openai.api_key, ENERGY_THRESHOLD, RECORD_TIMEOUT)
    bear = Bear(speech_config)

    transcription = [""]
    bear.speak(
        "Hello there! Just give my left foot a squeeze if you would like to get my attention."
    )

    while True:
        try:
            # If button is pressed, start listening
            if bear.foot_pressed():
                bear.speak("How may I help you?")
                listener.listen()

            if listener.speech_waiting():
                bear.speak("Let me think about that")
                bear.move_arms(hide=True)
                text = listener.recognize()

                if text:
                    transcription.append(text)
                    print(f"Phrase Complete. Sent '{text}' to ChatGPT.")
                    chat_response = sendchat(text)
                    transcription.append(f"> {chat_response}")
                    print("Got response from ChatGPT. Beginning speech synthesis.")
                    bear.move_arms(hide=False)
                    bear.speak(chat_response)

                os.system("clear")
                for line in transcription:
                    print(line)
                print("", end="", flush=True)
                time.sleep(0.25)
        except KeyboardInterrupt:
            break
    bear.deinit()


if __name__ == "__main__":
    main()
