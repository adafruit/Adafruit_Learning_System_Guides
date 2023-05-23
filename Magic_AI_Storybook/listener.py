# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from queue import Queue
import time

import speech_recognition as sr


class Listener:
    def __init__(
        self, api_key, energy_threshold=300, phrase_timeout=3.0, record_timeout=30
    ):
        self.listener_handle = None
        self.microphone = sr.Microphone()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1
        self.last_sample = bytes()
        self.phrase_time = time.monotonic()
        self.phrase_timeout = phrase_timeout
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(
                source
            )  # we only need to calibrate once, before we start listening
        self.record_timeout = record_timeout
        self.phrase_complete = False
        self.data_queue = Queue()
        self.listener_handle = None
        self.api_key = api_key

    def listen(self, ready_callback=None):
        print("Start listening...")
        self.phrase_complete = False
        start = time.monotonic()
        self._start_listening()
        if ready_callback:
            ready_callback()
        while (
            (self.listener_handle
            and not self.speech_waiting())
            or not self.phrase_complete
        ):
            if self.phrase_time and time.monotonic() > start + self.phrase_timeout:
                self.last_sample = bytes()
                self.phrase_complete = True
            self.phrase_time = time.monotonic() - start
        self.stop_listening()

    def _save_audio_callback(self, _, audio):
        print("Saving audio")
        data = audio.get_raw_data()
        self.data_queue.put(data)

    def _get_audio(self):
        """Concatenate and convert the queued raw data back to audio and return it"""
        start = time.monotonic()
        if self.speech_waiting():
            self.phrase_complete = False
            if self.phrase_time and time.monotonic() > start + self.phrase_timeout:
                self.last_sample = bytes()
                self.phrase_complete = True
            self.phrase_time = time.monotonic() - start

            # Concatenate our current audio data with the latest audio data.
            while self.speech_waiting():
                data = self.data_queue.get()
                self.last_sample += data

            # Use AudioData to convert the raw data to wav data.
            return sr.AudioData(
                self.last_sample,
                self.microphone.SAMPLE_RATE,
                self.microphone.SAMPLE_WIDTH,
            )
        return None

    def _start_listening(self):
        if not self.listener_handle:
            self.listener_handle = self.recognizer.listen_in_background(
                self.microphone,
                self._save_audio_callback,
                phrase_time_limit=self.record_timeout,
            )

    def stop_listening(self, wait_for_stop=False):
        if self.listener_handle:
            self.listener_handle(wait_for_stop=wait_for_stop)
            self.listener_handle = None
        print("Stop listening...")

    def is_listening(self):
        return self.listener_handle is not None

    def speech_waiting(self):
        return not self.data_queue.empty()

    def recognize(self):
        audio = self._get_audio()
        if audio:
            # Transcribe the audio data to text using Whisper
            print("Recognizing...")
            attempts = 0
            while attempts < 3:
                try:
                    result = self.recognizer.recognize_whisper_api(
                        audio, api_key=self.api_key
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
