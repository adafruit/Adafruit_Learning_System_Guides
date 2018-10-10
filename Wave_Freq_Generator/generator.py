import math
import array
import board
import audioio
from shapes import *

class Generator:

    sample = None
    dac = None
    shape = None
    frequency = None


    def __init__(self):
        self.dac = audioio.AudioOut(board.A0)


    def length(self, frequency):
        return int(64000 / frequency)


    def reallocate(self, frequency):
        self.sample = array.array("h", [0] * self.length(frequency))


    def make_sine(self):
        l = len(self.sample)
        for i in range(l):
            self.sample[i] = min(2 ** 15 -1, int(math.sin(math.pi * 2 * i / l) * (2 ** 15)))


    def make_square(self):
        l = len(self.sample)
        half_l = l // 2
        for i in range(l):
            if i < half_l:
                self.sample[i] = -1 * ((2 ** 15) - 1)
            else:
                self.sample[i] = (2 ** 15) - 1


    def make_triangle(self):
        l = len(self.sample)
        half_l = l // 2
        for i in range(l):
            if i <= half_l:
                self.sample[i] = min(2 ** 15 - 1, int((i / half_l) * (2 ** 16)) - (2 ** 15))
            else:
                self.sample[i] = min(2 ** 15 -1, int((1 - ((i - half_l) / half_l)) * (2 ** 16)) - (2 ** 15))



    def make_sawtooth(self):
        l = len(self.sample)
        for i in range(l):
            self.sample[i] = int((i / l) * (2 ** 16)) - (2 ** 15)


    def update(self, shape, frequency):
        if shape == self.shape and frequency == self.frequency:
            return

        if frequency != self.frequency:
            self.reallocate(frequency)
            self.frequency = frequency

        self.shape = shape
        if shape == SINE:
            self.make_sine()
        elif shape == SQUARE:
            self.make_square()
        elif shape == TRIANGLE:
            self.make_triangle()
        elif shape == SAWTOOTH:
            self.make_sawtooth()

        self.dac.stop()
        self.dac.play(audioio.RawSample(self.sample, channel_count=1, sample_rate=64000), loop=True)
