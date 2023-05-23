# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import speech_recognition as sr


class Listener:
    def __init__(self, api_key, energy_threshold=300, record_timeout=30):
        self.listener_handle = None
        self.microphone = sr.Microphone()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(
                source
            )  # we only need to calibrate once, before we start listening
        self.record_timeout = record_timeout
        self.listener_handle = None
        self.audio = None
        self.api_key = api_key

    def listen(self, ready_callback=None):
        self._start_listening()
        if ready_callback:
            ready_callback()
        while self.listener_handle and self.audio is None:
            time.sleep(0.1)
        self.stop_listening()

    def _save_audio_callback(self, _recognizer, audio):
        self.audio = audio

    def _start_listening(self):
        self.listener_handle = self.recognizer.listen_in_background(
            self.microphone, self._save_audio_callback
        )

    def stop_listening(self, wait_for_stop=False):
        if self.listener_handle:
            self.listener_handle(wait_for_stop=wait_for_stop)
            self.listener_handle = None

    def is_listening(self):
        return self.listener_handle is not None

    def speech_waiting(self):
        return self.audio is not None

    def recognize(self):
        if self.audio:
            # Transcribe the audio data to text using Whisper
            print("Recognizing...")
            attempts = 0
            while attempts < 3:
                try:
                    result = self.recognizer.recognize_whisper_api(
                        self.audio, api_key=self.api_key
                    )

                    return result.strip()
                except sr.RequestError as e:
                    print(f"Error: {e}")
                    time.sleep(3)
                attempts += 1
                print("Retry attempt: ", attempts)
            print("Failed to recognize")
            return None
        return None
