# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from audiocore import WaveFile


class SampleJukeboxError(OSError):
    """Exception raised for any missing audio files.
    """

    def __init__(self, files):
        self.files = files
        super().__init__("Missing audio files: " + ", ".join(files))


class SampleJukebox():
    """This plays wav files and tries to control the timing of memory
       allocations within the nRF52840 PWMAudioOut library to minimise
       the chance of MemoryError exceptions (2048 bytes)."""

    _file_buf = None  # Use for WaveFile objects

    def _init_wave_files(self, files, directory):
        """Open files from AUDIO_DIR and return a dict with FileIO objects
           or None if file not present."""

        # 2048 triggers bug in https://github.com/adafruit/circuitpython/issues/3030
        self._file_buf = bytearray(512)  # DO NOT CHANGE size til #3030 is fixed

        missing = []
        fhs = {}
        for file in files:
            wav_file = None
            filename = directory + "/" + file + ".wav"
            try:
                wav_file = open(filename, "rb")
                fhs[file] = WaveFile(wav_file, self._file_buf)
            except OSError:
                # OSError: [Errno 2] No such file/directory: 'filename.ext'
                missing.append(filename)

        # Raises an exception at the end to allow it to report ALL
        # of the missing files in one go to help out the user
        if missing:
            raise SampleJukeboxError(missing)
        self._wave_files = fhs


    def __init__(self, audio_device, files,
                 directory="", error_output=None):
        self._audio_device = audio_device
        self._error_output = error_output
        self._wave_files = None  # keep pylint happy
        self._init_wave_files(files, directory=directory)

        # play a file that exists to get m_alloc called now
        # but immediately stop it with pause()
        for wave_file in self._wave_files.values():
            if wave_file is not None:
                self._audio_device.play(wave_file, loop=True)
                self._audio_device.pause()
                break


    def play(self, name, loop=False):
        wave_file = self._wave_files.get(name)
        if wave_file is None:
            return
        # This pairing of stop() and play() will cause an m_free
        # and immediate m_malloc() which reduces considerably the risk
        # of losing the 2048 contiguous bytes needed for this
        self._audio_device.stop()
        self._audio_device.play(wave_file, loop=loop)
        # https://github.com/adafruit/circuitpython/issues/2036
        # is a general ticket about efficient audio buffering


    def playing(self):
        return self._audio_device.playing


    def wait(self):
        while self._audio_device.playing:
            pass


    def stop(self):
        self._audio_device.pause() # This avoid m_free
