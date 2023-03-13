# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import subprocess

import argparse
import os
import sys

from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from tempfile import NamedTemporaryFile

import speech_recognition as sr
import openai

# Add your OpenAI API key here
openai.api_key = "sk-..."
SYSTEM_ROLE = (
    "You are a helpful voice assistant that answers questions and gives information"
)

def speak(text):
    subprocess.run(["espeak-ng", text, "&"], check=False)


def sendchat(prompt):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
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
    with NamedTemporaryFile(suffix=".wav") as temp_file:
        result = openai.Audio.translate_raw("whisper-1", wav_data, temp_file.name)
    return result["text"].strip()


class Listener:
    def __init__(
        self, default_microphone, record_timeout, energy_threshold, phrase_timeout
    ):
        self.listener_handle = None
        self.recorder = sr.Recognizer()
        self.record_timeout = record_timeout
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = False
        self.recorder.pause_threshold = 1
        self.source = None
        self.last_sample = bytes()
        self.phrase_time = datetime.utcnow()
        self.phrase_timeout = phrase_timeout
        self.phrase_complete = False
        self.default_microphone = default_microphone
        # Thread safe Queue for passing data from the threaded recording callback.
        self.data_queue = Queue()
        self.source = self._get_microphone()

    def _get_microphone(self):
        if self.source:
            return self.source
        mic_name = self.default_microphone
        source = None
        if not mic_name or mic_name == "list":
            print("Available microphone devices are: ")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f'Microphone with name "{name}" found')
            sys.exit()
        else:
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                if mic_name in name:
                    print(f'Microphone with name "{name}" at index "{index}" found')
                    source = sr.Microphone(sample_rate=16000, device_index=index)
                    break
        if not source:
            print(f'Microphone with name "{mic_name}" not found')
            sys.exit()

        with source:
            self.recorder.adjust_for_ambient_noise(source)

        return source

    def listen(self):
        if not self.listener_handle:
            with self._get_microphone() as source:
                audio = self.recorder.listen(source)
            data = audio.get_raw_data()
            self.data_queue.put(data)

    def start(self):
        if not self.listener_handle:
            self.listener_handle = self.recorder.listen_in_background(
                self._get_microphone(),
                self.record_callback,
                phrase_time_limit=self.record_timeout,
            )

    def stop(self, wait_for_stop: bool = False):
        self.listener_handle(wait_for_stop=wait_for_stop)
        self.listener_handle = None

    def record_callback(self, _, audio: sr.AudioData) -> None:
        """
        Threaded callback function to recieve audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
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

            source = self._get_microphone()

            # Use AudioData to convert the raw data to wav data.
            return sr.AudioData(
                self.last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH
            )
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
        "--record_timeout",
        default=2,
        help="How real time the recording is in seconds.",
        type=float,
    )
    parser.add_argument(
        "--phrase_timeout",
        default=3,
        help="How much empty space between recordings before we "
        "consider it a new line in the transcription.",
        type=float,
    )
    parser.add_argument(
        "--default_microphone",
        default="pulse",
        help="Default microphone name for SpeechRecognition. "
        "Run this with 'list' to view available Microphones.",
        type=str,
    )
    args = parser.parse_args()

    listener = Listener(
        args.default_microphone,
        args.record_timeout,
        args.energy_threshold,
        args.phrase_timeout,
    )

    transcription = [""]

    print("How may I help you?")
    speak("How may I help you?")

    while True:
        try:
            # Pull raw recorded audio from the queue.
            listener.listen()
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
                        speak(chat_response)
                        print("Done speaking.")
                    else:
                        print("Partial Phrase...")
                        transcription[-1] = text

                os.system("clear")
                for line in transcription:
                    print(line)
                print("", end="", flush=True)
                sleep(0.25)
        except (AssertionError, AttributeError):
            pass
        except KeyboardInterrupt:
            break

    print("\n\nTranscription:")
    for line in transcription:
        print(line)


if __name__ == "__main__":
    main()
