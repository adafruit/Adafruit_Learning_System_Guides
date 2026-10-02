"""32 kHz mono PCM streaming to the Fruit Jam's 3.5 mm jack (TLV320DAC3100).

CircuitPython has no queue-style audio sample, so this plays a looped,
double-buffered audiocore.RawSample and refills its halves on a schedule. The
audio DMA copies one half every HALF samples, alternately half 0 then half 1:
at play() both are loaded, then half 0 again after 1 * HALF, half 1 after
2 * HALF, and so on. Half (j % 2) is therefore free to rewrite between
j * HALF and (j + 1) * HALF samples after play(), and what is written there
plays from (j + 2) * HALF. service() does that refill from a FIFO.

The schedule is kept with time.monotonic_ns(), which runs from the same crystal
as the I2S clock. At 150 MHz both the I2S rate (32000 * 192 Hz) and the 15 MHz
MCLK divide exactly, so the DAC runs at exactly the I2S rate. This needs an
adafruit_tlv320 version that supports 32 kHz with a 15 MHz MCLK.

The radio's rate comes from the dongle's crystal instead, so the FIFO level
drifts slowly. service() drops or repeats a few samples to keep it near the
target; the counters report how often.
"""

import array
import time

import audiobusio
import audiocore
import board
import digitalio
import microcontroller
import pwmio

import adafruit_tlv320

# pylint: disable=too-many-branches, attribute-defined-outside-init

RATE = 32000
MCLK = 15_000_000


class JackAudio:
    """Stream mono 16-bit PCM at 32 kHz to the headphone jack.

    write() queues samples, service() must be called often (every few ms,
    at least once per half = 64 ms). Latency is about 3 halves plus the FIFO.
    """

    def __init__(self, half=2048, fifo=16384, target=4096, volume=-10.0):
        if microcontroller.cpu.frequency != 150_000_000:
            # Other clocks give an inexact I2S divider and the DAC would slip.
            raise RuntimeError("jack audio timing assumes a 150 MHz CPU clock")
        self.half = half
        self.half_ns = half * 1_000_000_000 // RATE
        self.target = target
        self._reset_pin = digitalio.DigitalInOut(board.PERIPH_RESET)
        self._reset_pin.switch_to_output(False)
        time.sleep(0.1)
        self._reset_pin.value = True
        time.sleep(0.01)
        self._mclk = pwmio.PWMOut(board.I2S_MCLK, frequency=MCLK, duty_cycle=2**15)
        self.dac = adafruit_tlv320.TLV320DAC3100(board.I2C())
        self.dac.configure_clocks(sample_rate=RATE, mclk_freq=MCLK)
        self.dac.headphone_output = True
        self.dac.dac_volume = volume
        self._i2s = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
        self._fifo_len = fifo
        self._play = None
        self.fifo = None
        self.rd = self.wr = 0
        self._t0 = None
        self._next = 2
        self._primed = False
        self.late = self.underruns = self.dropped = self.repeated = 0
        self.max_lateness_ns = 0

    def _allocate(self):
        # Python objects go to internal SRAM first, then PSRAM. The play
        # buffer is allocated before play() so its DMA buffers still fit in
        # SRAM; the large FIFO afterwards, where it may land in PSRAM.
        half = self.half
        self._play = array.array("h", bytes(4 * half))
        self._playv = memoryview(self._play)
        self._sample = audiocore.RawSample(
            self._play, sample_rate=RATE, single_buffer=False
        )
        self._zeros = memoryview(array.array("h", bytes(2 * half)))

    # FIFO: samples live in fifo[rd:wr]. The producer writes at wr directly
    # (write_view) so the demodulator can output straight into it.

    def queued(self):
        return self.wr - self.rd

    def _reserve(self, count):
        if self.fifo is None:
            # Allocated on first use, so that SRAM-only buffers allocated
            # after start() (such as a USB bulk ring) get the SRAM first.
            self.fifo = array.array("h", bytes(2 * self._fifo_len))
            self._fifov = memoryview(self.fifo)
            self._fifob = self._fifov.cast("B")
        if self.wr + count > len(self.fifo):
            left = self.wr - self.rd
            self._fifov[:left] = self._fifov[self.rd : self.wr]
            self.rd = 0
            self.wr = left
            if self.wr + count > len(self.fifo):
                # Consumer stalled: keep the newest data.
                self.dropped += self.wr
                self.rd = self.wr = 0

    def write_view(self, count):
        """Return a writable view of count samples at the FIFO tail."""
        self._reserve(count)
        return self._fifov[self.wr : self.wr + count]

    def write_view_bytes(self, count):
        """write_view() as a byte view, for code that requires byte buffers."""
        self._reserve(count)
        return self._fifob[2 * self.wr : 2 * (self.wr + count)]

    def commit(self, count):
        self.wr += count

    def write(self, samples):
        n = len(samples)
        self.write_view(n)[:] = samples
        self.commit(n)

    def clear(self):
        """Forget queued audio and silence the output within ~3 halves."""
        self.rd = self.wr = 0
        self._primed = False

    def start(self):
        """Start playing silence. Raises if the DMA buffers do not fit."""
        if self._play is None:
            self._allocate()
        self._playv[: self.half] = self._zeros
        self._playv[self.half :] = self._zeros
        self._i2s.play(self._sample, loop=True)
        self._t0 = time.monotonic_ns()
        self._next = 2
        self._primed = False

    def stop(self):
        self._i2s.stop()
        self._t0 = None

    def service(self):
        """Refill the half that is free now. Returns True if it wrote one."""
        if self._t0 is None:
            return False
        now = time.monotonic_ns() - self._t0
        j = now // self.half_ns
        if j < self._next:
            return False
        if j > self._next:
            # Missed a whole window: that half already played stale audio.
            self.late += j - self._next
            self._next = j
        lateness = now - j * self.half_ns
        self.max_lateness_ns = max(self.max_lateness_ns, lateness)
        h = self.half
        dst = self._playv[(j & 1) * h : ((j & 1) + 1) * h]
        q = self.wr - self.rd
        if not self._primed:
            if q >= self.target + h:
                self._primed = True
            else:
                dst[:] = self._zeros
        if self._primed:
            if q < h:
                # Underrun: play what there is, then silence, and re-prime.
                dst[:q] = self._fifov[self.rd : self.wr]
                dst[q:] = self._zeros[q:]
                self.rd = self.wr = 0
                self.underruns += 1
                self._primed = False
            else:
                # Drift correction: take one sample more or less per half
                # when the FIFO is well off target.
                take = h
                if q > self.target + h + h // 2:
                    take = h + 1
                elif self.target - h // 2 > q > h:
                    take = h - 1
                if take == h:
                    dst[:] = self._fifov[self.rd : self.rd + h]
                elif take > h:
                    dst[:] = self._fifov[self.rd : self.rd + h]
                    self.dropped += 1
                else:
                    dst[: h - 1] = self._fifov[self.rd : self.rd + h - 1]
                    dst[h - 1] = dst[h - 2]
                    self.repeated += 1
                self.rd += take
        self._next = j + 1
        return True

    def stats(self):
        return {
            "late_halves": self.late,
            "underruns": self.underruns,
            "dropped": self.dropped,
            "repeated": self.repeated,
            "max_lateness_ms": self.max_lateness_ns / 1e6,
            "queued": self.wr - self.rd,
        }

    def deinit(self):
        self.stop()
        self._i2s.deinit()
        self._mclk.deinit()
        self._reset_pin.deinit()
