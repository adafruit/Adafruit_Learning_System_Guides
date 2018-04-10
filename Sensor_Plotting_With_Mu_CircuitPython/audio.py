import audiobusio
import board
import array
import math
import time


def mean(values):
    return sum(values) / len(values)


def normalized_rms(values):
    minbuf = int(mean(values))
    return math.sqrt(sum(float((sample-minbuf)*(sample-minbuf)) for sample in values)/len(values))


mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA, frequency=16000, bit_depth=16)
samples = array.array('H', [0] * 160)
mic.record(samples, len(samples))

while True:
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    print(((magnitude),))
    time.sleep(0.1)
