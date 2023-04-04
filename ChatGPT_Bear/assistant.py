# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import threading
import os
import sys

from datetime import datetime, timedelta
from queue import Queue
import time
import random
from tempfile import NamedTemporaryFile

import azure.cognitiveservices.speech as speechsdk
import speech_recognition as sr
import openai

import board
import digitalio
from adafruit_motorkit import MotorKit

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
PHRASE_TIMEOUT = 3.0  # Space between recordings for sepating phrases
RECORD_TIMEOUT = 30

# Motor Parameters
ARM_MOVEMENT_TIME = 0.5
BASE_MOUTH_DURATION = 0.2  # A higher number means slower mouth movement
SPEECH_VARIANCE = 0.1  # Higher allows more mouth movement variance.
                       # It pauses for BASE_MOUTH_DURATION ± SPEECH_VARIANCE
MOTOR_DUTY_CYCLE = 1.0  # Lower provides less power to the motors

# Import keys from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
speech_key = os.environ.get("SPEECH_KEY")
service_region = os.environ.get("SPEECH_REGION")

if openai.api_key is None or speech_key is None or service_region is None:
    print(
        "Please set the OPENAI_API_KEY, SPEECH_KEY, and SPEECH_REGION environment variables first."
    )
    sys.exit(1)

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = AZURE_SPEECH_VOICE


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


class Listener:
    def __init__(self):
        self.listener_handle = None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1
        self.last_sample = bytes()
        self.phrase_time = datetime.utcnow()
        self.phrase_timeout = PHRASE_TIMEOUT
        self.phrase_complete = False
        # Thread safe Queue for passing data from the threaded recording callback.
        self.data_queue = Queue()
        self.mic_dev_index = None

    def listen(self):
        if not self.listener_handle:
            with sr.Microphone() as source:
                print(source.stream)
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=RECORD_TIMEOUT)
            data = audio.get_raw_data()
            self.data_queue.put(data)

    def record_callback(self, _, audio: sr.AudioData) -> None:
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        self.data_queue.put(data)

    def speech_waiting(self):
        return not self.data_queue.empty()

    def get_speech(self):
        if self.speech_waiting():
            return self.data_queue.get()
        return None

    def get_audio_data(self):
        now = datetime.utcnow()
        if self.speech_waiting():
            self.phrase_complete = False
            if self.phrase_time and now - self.phrase_time > timedelta(
                seconds=self.phrase_timeout
            ):
                self.last_sample = bytes()
                self.phrase_complete = True
            self.phrase_time = now

            # Concatenate our current audio data with the latest audio data.
            while self.speech_waiting():
                data = self.get_speech()
                self.last_sample += data

            # Use AudioData to convert the raw data to wav data.
            with sr.Microphone() as source:
                audio_data = sr.AudioData(
                    self.last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH
                )
            return audio_data

        return None


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
    listener = Listener()
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

            # Pull raw recorded audio from the queue.
            if listener.speech_waiting():
                audio_data = listener.get_audio_data()
                bear.speak("Let me think about that")
                bear.move_arms(hide=True)
                text = transcribe(audio_data.get_wav_data())

                if text:
                    if listener.phrase_complete:
                        transcription.append(text)
                        print(f"Phrase Complete. Sent '{text}' to ChatGPT.")
                        chat_response = sendchat(text)
                        transcription.append(f"> {chat_response}")
                        print("Got response from ChatGPT. Beginning speech synthesis.")
                        bear.move_arms(hide=False)
                        bear.speak(chat_response)
                    else:
                        print("Partial Phrase...")
                        transcription[-1] = text

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
