# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import subprocess

import argparse
import os

from datetime import datetime, timedelta
from queue import Queue
import time
import random
from tempfile import NamedTemporaryFile

import speech_recognition as sr
import openai

import board
import digitalio
from adafruit_motorkit import MotorKit

openai.api_key = "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"
SYSTEM_ROLE = (
    "You are a helpful voice assistant that answers questions and gives information"
)
CHATGPT_MODEL = "gpt-3.5-turbo"
WHISPER_MODEL = "whisper-1"
ARM_MOVEMENT_TIME = 0.5
BASE_MOUTH_DURATION = 0.2  # A higher number means slower mouth movement
SPEECH_VARIANCE = 0.03   # A higher number means more variance in the mouth movement
RECORD_TIMEOUT = 30

# Setup Motors
kit = MotorKit(i2c=board.I2C())
arms_motor = kit.motor1
mouth_motor = kit.motor2

# Setup Foot Button
foot_button = digitalio.DigitalInOut(board.D16)
foot_button.direction = digitalio.Direction.INPUT
foot_button.pull = digitalio.Pull.UP

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

def move_arms_motor(dir_up=True, speed=1.0):
    direction = 1 if dir_up else -1
    arms_motor.throttle = speed * direction
    time.sleep(ARM_MOVEMENT_TIME)
    arms_motor.throttle = 0

def move_mouth_motor(dir_open=True, duration=0.5, speed=1.0):
    direction = 1 if dir_open else -1
    mouth_motor.throttle = speed * direction
    time.sleep(duration)
    mouth_motor.throttle = 0

def move_mouth():
    move_mouth_motor(dir_open=True, duration=random_mouth_duration())
    move_mouth_motor(dir_open=False, duration=random_mouth_duration())

def random_mouth_duration():
    return BASE_MOUTH_DURATION + random.random() * SPEECH_VARIANCE - (SPEECH_VARIANCE / 2)

def move_arms(hide=True):
    move_arms_motor(dir_up= not hide)

def speak(text):
    # while the subprocess is still running, move the mouth
    with subprocess.Popen(["espeak-ng", text, "&"]) as proc:
        while proc.poll() is None:
            move_mouth()

def transcribe(wav_data):
    # Read the transcription.
    print("Transcribing...")
    speak("Let me think about that")
    move_arms(hide=True)
    attempts = 0
    while attempts < 3:
        try:
            with NamedTemporaryFile(suffix=".wav") as temp_file:
                result = openai.Audio.translate_raw(WHISPER_MODEL, wav_data, temp_file.name)
                return result["text"].strip()
        except (
            openai.error.ServiceUnavailableError,
            openai.error.APIError
        ):
            time.sleep(3)
        attempts += 1
    return "I wasn't able to understand you. Please repeat that."

class Listener:
    def __init__(
        self, energy_threshold, phrase_timeout
    ):
        self.listener_handle = None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1
        self.last_sample = bytes()
        self.phrase_time = datetime.utcnow()
        self.phrase_timeout = phrase_timeout
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
                audio_data  = sr.AudioData(
                    self.last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH
                )
            return audio_data

        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--energy_threshold",
        default=1000,
        help="Energy level for mic to detect.",
        type=int,
    )
    parser.add_argument(
        "--phrase_timeout",
        default=3,
        help="How much empty space between recordings before we "
        "consider it a new line in the transcription.",
        type=float,
    )

    args = parser.parse_args()

    listener = Listener(
        args.energy_threshold,
        args.phrase_timeout,
    )

    transcription = [""]

    while True:
        try:
            # If button is pressed, start listening
            if not foot_button.value:
                print("How may I help you?")
                speak("How may I help you?")
                listener.listen()

            # Pull raw recorded audio from the queue.
            if listener.speech_waiting():
                audio_data = listener.get_audio_data()
                text = transcribe(audio_data.get_wav_data())

                if text:
                    if listener.phrase_complete:
                        transcription.append(text)
                        print(f"Phrase Complete. Sent '{text}' to ChatGPT.")
                        chat_response = sendchat(text)
                        transcription.append(f"> {chat_response}")
                        print("Got response from ChatGPT. Beginning speech synthesis.")
                        move_arms(hide=False)
                        speak(chat_response)
                        print("Done speaking.")
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
    move_arms(hide=False)
    print("\n\nTranscription:")
    for line in transcription:
        print(line)


if __name__ == "__main__":
    main()
