# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timedelta
from queue import Queue

import speech_recognition as sr


class Listener:
    def __init__(self, energy_threshold=1000, phrase_timeout=3.0, record_timeout=30):
        self.listener_handle = None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1
        self.last_sample = bytes()
        self.phrase_time = datetime.utcnow()
        self.phrase_timeout = phrase_timeout
        self.record_timeout = record_timeout
        self.phrase_complete = False
        # Thread safe Queue for passing data from the threaded recording callback.
        self.data_queue = Queue()
        self.mic_dev_index = None

    def listen(self, ready_callback=None):
        self.phrase_complete = False
        start = datetime.utcnow()
        self.start_listening()
        if ready_callback:
            ready_callback()
        while (
            self.listener_handle
            and not self.speech_waiting()
            or not self.phrase_complete
        ):
            if self.phrase_time and start - self.phrase_time > timedelta(
                seconds=self.phrase_timeout
            ):
                self.last_sample = bytes()
                self.phrase_complete = True
            self.phrase_time = start
        self.stop_listening()

    def start_listening(self):
        if not self.listener_handle:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
            self.listener_handle = self.recognizer.listen_in_background(
                sr.Microphone(),
                self.record_callback,
                phrase_time_limit=self.record_timeout,
            )

    def stop_listening(self, wait_for_stop=False):
        if self.listener_handle:
            self.listener_handle(wait_for_stop=wait_for_stop)
            self.listener_handle = None

    def is_listening(self):
        return self.listener_handle is not None

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
