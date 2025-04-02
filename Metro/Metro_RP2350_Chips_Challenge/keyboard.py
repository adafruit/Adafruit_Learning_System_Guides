# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
import sys
import supervisor

class KeyboardBuffer:
    def __init__(self, valid_sequences):
        self.key_buffer = ""
        self._valid_sequences = valid_sequences

    def update(self):
        while supervisor.runtime.serial_bytes_available:
            self.key_buffer += sys.stdin.read(1)

    def print(self):
        print("buffer", end=": ")
        for key in self.key_buffer:
            print(hex(ord(key)), end=" ")

    def set_valid_sequences(self, valid_sequences):
        self._valid_sequences = valid_sequences

    def clear(self):
        self.key_buffer = ""

    def get_key(self):
        """
        Check for keyboard input and return the first valid key sequence.
        """
        # Check if serial data is available
        self.update()
        if self.key_buffer:
            for sequence in self._valid_sequences:
                if self.key_buffer.startswith(sequence):
                    key = sequence
                    self.key_buffer = self.key_buffer[len(sequence):]
                    return key
            # Remove first character
            self.key_buffer = self.key_buffer[1:]

        return None
