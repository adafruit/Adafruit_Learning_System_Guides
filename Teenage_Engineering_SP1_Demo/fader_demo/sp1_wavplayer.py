# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""SP-1 playback from ordinary WAV files on the eMMC's FAT volume."""

# pylint: skip-file
import gc
import time

import audiocore
import audiomixer

try:
    import ulab.numpy as _np
except ImportError:  # a host harness, or a build
    _np = None  # without ulab: use the loop

__version__ = "1.1.0"

RATE = 48000  # the only rate this board has
CHANNELS = 2
FRAME = 4  # bytes, 16-bit stereo

BLOCK = 512
BLOCK_FRAMES = BLOCK // FRAME  # 128
BLOCK_SECONDS = BLOCK_FRAMES / float(RATE)  # 2.6667 ms

HEADER_BYTES = 512  # where `data`'s payload starts in a prepared stem

PCM_BUDGET = 98304
MAX_CHUNK_BYTES = 16384  # per stem; 16 KiB reads are the card's best rate
MIN_CHUNK_BYTES = 2048

READ_US_BASE = 1023.0
READ_US_PER_BYTE = 0.6994
AUDIO_LOAD = 1.0  # already in the constants above; kept as a knob

FADE_US_PER_FRAME = 183.0
FADE_VEC_US_BASE = 470.0
FADE_VEC_US_PER_FRAME = 40.0
FADE_VEC_MIN_FRAMES = 8
FADE_BUDGET = 0.025  # of a chunk's playing time
GC_US = 5890.0  # one gc.collect() on this heap

MIXER_PAD_FRAMES = 1

DEFAULT_MOUNT = "/sd"
DEFAULT_SONG = "/sd/songs/real_existence"


class WavError(Exception):
    """A stem file this player cannot stream, and why."""


# ---------------------------------------------------------------------------
# the song: four prepared WAVs in a directory
# ---------------------------------------------------------------------------


def wav_info(f):
    """`(data_offset, data_bytes)` for an open 48 kHz/16-bit/stereo WAV.

    Walks the RIFF chunk list rather than assuming a 44-byte header.
    """
    import struct

    f.seek(0)
    head = f.read(12)
    if len(head) < 12 or head[0:4] != b"RIFF" or head[8:12] != b"WAVE":
        raise WavError("not a RIFF/WAVE file")
    fmt = None
    pos = 12
    while True:
        f.seek(pos)
        h = f.read(8)
        if len(h) < 8:
            raise WavError("no data chunk")
        cid = bytes(h[0:4])
        size = struct.unpack("<I", h[4:8])[0]
        if cid == b"fmt ":
            fmt = f.read(min(size, 16))
        elif cid == b"data":
            if fmt is None:
                raise WavError("data chunk before fmt")
            tag, ch, rate, _bps, _align, bits = struct.unpack("<HHIIHH", fmt)
            if tag != 1 or bits != 16:
                raise WavError("not 16-bit PCM (format %d, %d bits)" % (tag, bits))
            if ch != CHANNELS:
                raise WavError("%d channel(s), need %d" % (ch, CHANNELS))
            if rate != RATE:
                raise WavError("%d Hz, this board is %d Hz only" % (rate, RATE))
            return pos + 8, size
        pos += 8 + size + (size & 1)


class Song:
    """The four stem files of one song, opened and measured.

    `paths` are in stem order, so `paths[0]` is stem 0
    `blocks` is the playable length in 512-byte PCM blocks, taken from the
    shortest stem so no stem ever reads past its own data.
    """

    def __init__(self, path, paths, starts, sizes):
        self.path = path
        self.paths = paths
        self.starts = starts
        self.sizes = sizes
        self.nstems = len(paths)
        self.aligned = all(s % BLOCK == 0 for s in starts)
        self.blocks = min(sizes) // BLOCK
        self.frames = self.blocks * BLOCK_FRAMES
        self.seconds = self.frames / float(RATE)
        self.ragged = len(set(sizes)) != 1

    def __repr__(self):
        return "<Song %s %d stems %.1f s%s>" % (
            self.path,
            self.nstems,
            self.seconds,
            "" if self.aligned else " UNALIGNED",
        )


def open_song(path=DEFAULT_SONG, names=None):
    """Find and validate a song directory: `stem1.wav` ... `stem4.wav`."""
    import os

    if names is None:
        names = sorted([n for n in os.listdir(path) if n.lower().endswith(".wav")])
    if not names:
        raise WavError("no .wav files in %s" % path)
    paths, starts, sizes = [], [], []
    for name in names:
        full = path + "/" + name
        f = open(full, "rb")
        try:
            off, size = wav_info(f)
        except WavError as err:
            raise WavError("%s: %s" % (name, err))
        finally:
            f.close()
        paths.append(full)
        starts.append(off)
        sizes.append(size)
    return Song(path, paths, starts, sizes)


# ---------------------------------------------------------------------------
# the player
# ---------------------------------------------------------------------------


class Player:
    """Stream a `Song`'s stems through an `sp1_audio.Audio`.

    `song` is an `open_song()` result on a mounted volume, `audio` an
    `sp1_audio.Audio` that is already constructed. The player owns the mixer,
    the chunk buffers and the open files; it does not own the mount or the
    audio path, and deinits neither.

    `stems` is which of the song's stems to play and in what voice order,
    `levels` one float per stem (settable at any time), `chunk_bytes` the PCM
    per stem per chunk.
    """

    def __init__(
        self,
        song,
        audio,
        stems=None,
        stem=None,
        levels=None,
        chunk_bytes=None,
        fade_ms=None,
        gc_every=16,
        mixer_buffer=None,
        mixer_pad=None,
    ):
        if stem is not None:
            stems = (stem,)
        if stems is None:
            stems = tuple(range(song.nstems))
        stems = tuple(stems)
        if not stems:
            raise ValueError("at least one stem")
        for s in stems:
            if not 0 <= s < song.nstems:
                raise ValueError("stem must be 0-%d" % (song.nstems - 1))
        self.song = song
        self.audio = audio
        self.stems = list(stems)
        self.nstems = len(stems)

        if chunk_bytes is None:
            chunk_bytes = min(MAX_CHUNK_BYTES, PCM_BUDGET // (2 * self.nstems))
        self.chunk_bytes = _round_blocks(chunk_bytes)
        self.fade_ms = fade_ms
        self.gc_every = max(1, gc_every)
        self.chunk_shrunk = False
        self._levels_want = levels
        self._files = None
        self._buf = self._bmv = self._mv = self._full = None

        self.mixer = None
        self.auto_mixer = mixer_buffer is None
        self.mixer_pad = (
            MIXER_PAD_FRAMES if mixer_pad is None else max(1, int(mixer_pad))
        )
        self._build_mixer(1024)

        want = self.chunk_bytes
        self.shapes = self._plan()
        self.fill_us_predicted = 0.0
        last = len(self.shapes) - 1
        for i in range(len(self.shapes)):
            cb, cost = self.shapes[i]
            self.chunk_bytes = cb
            self.fill_us_predicted = cost
            gc.collect()
            try:
                self._alloc()
            except MemoryError:
                self._release()
                if i == last:
                    raise
                continue
            nbytes = self._mixer_bytes(cb) if self.auto_mixer else mixer_buffer
            if self._build_mixer(nbytes) or i == last:
                break
            # The mixer is back to 1 KB and the chunk is what is in the way.
            self._release()
            self._build_mixer(1024)
        self.chunk_shrunk = self.chunk_bytes != want
        self.chunk_blocks = self.chunk_bytes // BLOCK
        self.chunk_frames = self.chunk_bytes // FRAME
        self.chunk_seconds = self.chunk_frames / float(RATE)
        self.fade_frames = self._fade_frames(self.chunk_bytes)
        self._ramp = self._ramps(self.fade_frames)
        self.fill_ratio_predicted = self.fill_us_predicted / (self.chunk_seconds * 1e6)

        self.levels = self._levels_want
        self.dead_air_ms = self.dead_air(self.chunk_bytes, self.mixer_buffer)

        self._open()
        self._started = False
        self.stats = {}

    # -- the mixer, sized to the chunk -------------------------------------

    def _mixer_bytes(self, chunk_bytes):
        """The buffer that leaves a chunk `mixer_pad` short of a whole
        production block. 4 bytes a frame, double buffered."""
        return 8 * (chunk_bytes // FRAME + self.mixer_pad)

    def dead_air(self, chunk_bytes, mixer_buffer):
        """Predicted silence per chunk boundary, in ms."""
        block = mixer_buffer // 8
        frames = chunk_bytes // FRAME
        return (block - frames % block) * 1000.0 / RATE

    def _build_mixer(self, nbytes):
        """(Re)build the mixer at `nbytes`, releasing any old one. Returns
        False if the heap refused and it came up at 1024 instead.
        """
        if self.mixer is not None:
            try:
                self.mixer.deinit()
            except Exception:
                pass
            self.mixer = None
            gc.collect()
        nvoices = 2 * self.nstems
        try:
            self.mixer = audiomixer.Mixer(
                voice_count=nvoices,
                buffer_size=nbytes,
                channel_count=CHANNELS,
                bits_per_sample=16,
                samples_signed=True,
                sample_rate=RATE,
            )
            self.mixer_buffer = nbytes
            return True
        except MemoryError:
            self.mixer = audiomixer.Mixer(
                voice_count=nvoices,
                buffer_size=1024,
                channel_count=CHANNELS,
                bits_per_sample=16,
                samples_signed=True,
                sample_rate=RATE,
            )
            self.mixer_buffer = 1024
            return nbytes == 1024

    # -- shopping for a shape the heap will take ---------------------------

    def fade_us(self, f):
        """What a ramp of `f` frames costs per chunk, both stems summed."""
        if f <= 0:
            return 0.0
        if _np is None or f < FADE_VEC_MIN_FRAMES:
            return f * FADE_US_PER_FRAME * self.nstems
        return (FADE_VEC_US_BASE + f * FADE_VEC_US_PER_FRAME) * self.nstems

    def _fade_frames(self, chunk_bytes):
        """The ramp is priced, not chosen (`fade_us`): `fade_ms=None` spends
        `FADE_BUDGET` of the chunk on it. Even two frames turn the step at a
        chunk edge into a slope."""
        frames = chunk_bytes // FRAME
        if self.fade_ms is None:
            budget = FADE_BUDGET * frames / float(RATE) * 1e6
            loop = int(budget / (FADE_US_PER_FRAME * self.nstems))
            if _np is None:
                f = loop
            else:
                vec = int(
                    (budget / self.nstems - FADE_VEC_US_BASE) / FADE_VEC_US_PER_FRAME
                )
                # Below the crossing the vector ramp is not on offer, so the
                # budget buys whichever is longer, not whichever is newer.
                f = vec if vec >= FADE_VEC_MIN_FRAMES else loop
            f = max(2, f)
        else:
            f = int(self.fade_ms * RATE / 1000.0)
        if f * 2 >= frames:
            f = 0
        return f

    def fill_us(self, chunk_bytes):
        """Predicted cost of one chunk's refill, in microseconds, from the
        measured constants above. `fill_us(cb) / (chunk seconds)` is the fill
        ratio `play()` will report, and 1.0 is an underrun by definition."""
        read = (READ_US_BASE + READ_US_PER_BYTE * chunk_bytes) * AUDIO_LOAD
        fade = self.fade_us(self._fade_frames(chunk_bytes))
        return read * self.nstems + fade + GC_US / self.gc_every

    def _plan(self):
        """Every chunk size worth trying, cheapest refill first."""
        out = []
        cb = self.chunk_bytes
        while True:
            out.append((cb, self.fill_us(cb)))
            if cb <= MIN_CHUNK_BYTES:
                break
            cb = max(MIN_CHUNK_BYTES, _round_blocks(cb - max(BLOCK, cb // 8)))
        out.sort(key=lambda row: row[1] / row[0])
        return out

    # -- what plays --------------------------------------------------------

    @property
    def stem(self):
        """The stem, for a one-stem player. Settable mid-song; it takes effect
        on the next chunk filled (and re-seeks that stem's file)."""
        if self.nstems != 1:
            raise ValueError("this player has %d stems; use .stems" % self.nstems)
        return self.stems[0]

    @stem.setter
    def stem(self, value):
        if self.nstems != 1:
            raise ValueError("this player has %d stems; use .stems" % self.nstems)
        if not 0 <= value < self.song.nstems:
            raise ValueError("stem must be 0-%d" % (self.song.nstems - 1))
        self.stems[0] = value
        self._open()

    @property
    def levels(self):
        """Per-stem voice level, 0.0-1.0. Writing it retunes the mix on the
        mixer's next block -- mid-chunk, no reallocation, so this is how a
        fader moves. `None` means unity."""
        return tuple(self._levels)

    @levels.setter
    def levels(self, value):
        if value is None:
            value = 1.0
        if isinstance(value, (int, float)):
            value = [float(value)] * self.nstems
        value = [float(v) for v in value]
        if len(value) != self.nstems:
            raise ValueError("levels needs %d value(s)" % self.nstems)
        self._levels = value
        voice = self.mixer.voice
        for bank in range(2):
            for j in range(self.nstems):
                voice[bank * self.nstems + j].level = value[j]

    # -- the buffers and the files ----------------------------------------

    def _alloc(self):
        """Two banks of one PCM chunk per stem, and the views over them."""
        n = self.chunk_bytes
        self._buf, self._bmv, self._mv, self._full = [], [], [], []
        for _ in range(2):
            bufs = [bytearray(n) for _ in range(self.nstems)]
            bmv = [memoryview(b) for b in bufs]
            mv = [memoryview(b).cast("h") for b in bufs]
            self._buf.append(bufs)
            self._bmv.append(bmv)
            self._mv.append(mv)
            self._full.append(
                [
                    audiocore.RawSample(m, channel_count=CHANNELS, sample_rate=RATE)
                    for m in mv
                ]
            )

    def _release(self):
        self._full = None
        self._mv = None
        self._bmv = None
        self._buf = None
        gc.collect()

    def _open(self):
        self._close()
        song = self.song
        self._files = [open(song.paths[s], "rb") for s in self.stems]
        self._fpos = [-1] * self.nstems

    def _close(self):
        if self._files:
            for f in self._files:
                try:
                    f.close()
                except Exception:
                    pass
        self._files = None

    # -- the two halves of a chunk ----------------------------------------

    def _fill(self, idx, block, count):
        """Read `count` blocks from `block` for every stem into bank `idx`."""
        n = count * BLOCK
        bufs = self._bmv[idx]
        files = self._files
        pos = self._fpos
        starts = self.song.starts
        stems = self.stems
        full = n == self.chunk_bytes
        for j in range(self.nstems):
            f = files[j]
            want = starts[stems[j]] + block * BLOCK
            if pos[j] != want:
                f.seek(want)
            got = f.readinto(bufs[j] if full else bufs[j][:n])
            pos[j] = want + got
            if got < n:
                self._buf[idx][j][got:n] = b"\x00" * (n - got)
        self._fade(idx, count)

    def _ramps(self, f):
        """The two edge ramps, interleaved to stereo"""
        if _np is None or f < FADE_VEC_MIN_FRAMES:
            return None
        up = _np.array([(i + 1) / f for i in range(f) for _ in (0, 1)])
        dn = _np.array([(f - i) / f for i in range(f) for _ in (0, 1)])
        return up, dn

    def _fade(self, idx, count):
        """Ramp the first and last `fade_frames` of every stem's chunk to zero."""
        f = self.fade_frames
        if not f:
            return
        n = count * BLOCK_FRAMES
        if self._ramp is not None:
            up, dn = self._ramp
            for buf in self._mv[idx]:
                h = _np.frombuffer(buf[0 : 2 * f], dtype=_np.int16)
                h[:] = _np.array(h * up, dtype=_np.int16)
                t = _np.frombuffer(buf[2 * (n - f) : 2 * n], dtype=_np.int16)
                t[:] = _np.array(t * dn, dtype=_np.int16)
            return
        last = n - 1
        for buf in self._mv[idx]:
            for i in range(f):
                g = i + 1
                j = 2 * i
                buf[j] = buf[j] * g // f
                buf[j + 1] = buf[j + 1] * g // f
                k = 2 * (last - i)
                buf[k] = buf[k] * g // f
                buf[k + 1] = buf[k + 1] * g // f

    def _samples(self, idx, count):
        """One `RawSample` per stem for bank `idx`."""
        if count * BLOCK == self.chunk_bytes:
            return self._full[idx]
        n = count * BLOCK_FRAMES * CHANNELS  # int16 items
        return [
            audiocore.RawSample(mv[:n], channel_count=CHANNELS, sample_rate=RATE)
            for mv in self._mv[idx]
        ]

    def _start(self, idx, samples):
        """Hand bank `idx`'s chunk to its voices, back to back."""
        voice = self.mixer.voice
        j = idx * self.nstems
        for s in samples:
            voice[j].play(s)
            j += 1

    # -- playing -----------------------------------------------------------

    def play(self, start_block=0, blocks=None, seconds=None, on_chunk=None):
        """Stream `blocks` 512-byte blocks from `start_block`, or `seconds`.

        Blocks until the audio has played out (or Ctrl-C). Returns `stats`:
        chunks, blocks, underruns, slips, dead_ms, the worst fill/chunk ratio
        and the wall clock.
        `underruns` is a chunk whose refill took longer than the chunk before
        it lasted makes an audible gap, not a boundary tick. `slips` is a
        handover where the stems did not all start on the same mixer block,
        which no fill ratio can show and a listener hears as one instrument
        stumbling.
        """
        if blocks is None:
            blocks = self.song.blocks - start_block
        if seconds is not None:
            want = int(seconds / BLOCK_SECONDS) + 1
            if want < blocks:
                blocks = want
        if blocks <= 0:
            raise ValueError("nothing to play")

        voice = self.mixer.voice
        ns = self.nstems
        if not self._started:
            # Audio.play() mutes across the swap and leaves the mute where it
            # found it, so the caller's `muted` state survives this.
            self.audio.play(self.mixer)
            self._started = True

        st = {
            "chunks": 0,
            "blocks": 0,
            "underruns": 0,
            "fill_ratio": 0.0,
            "fill_ms_max": 0.0,
            "seconds": 0.0,
            "slips": 0,
            "fill_ms_sum": 0.0,
            "fill_ratio_mean": 0.0,
            "dead_ms": 0.0,
            "stems": tuple(self.stems),
        }
        if ns == 1:
            st["stem"] = self.stems[0]
        self.stats = st

        pos = start_block
        left = blocks
        idx = 0
        n = min(self.chunk_blocks, left)
        self._fill(idx, pos, n)
        pos += n
        left -= n
        self._start(idx, self._samples(idx, n))
        t_start = time.monotonic()
        st["chunks"] = 1
        st["blocks"] = n

        try:
            while left:
                nxt = 1 - idx
                m = min(self.chunk_blocks, left)
                t0 = time.monotonic_ns()
                self._fill(nxt, pos, m)
                fill_ms = (time.monotonic_ns() - t0) / 1e6

                ratio = fill_ms / (n * BLOCK_SECONDS * 1e3)
                if ratio > st["fill_ratio"]:
                    st["fill_ratio"] = ratio
                if fill_ms > st["fill_ms_max"]:
                    st["fill_ms_max"] = fill_ms

                st["fill_ms_sum"] += fill_ms
                if ratio >= 1.0:
                    st["underruns"] += 1

                nextsamples = self._samples(nxt, m)
                while voice[idx * ns].playing:
                    pass
                self._start(nxt, nextsamples)

                j = idx * ns + 1
                end = idx * ns + ns
                while j < end:
                    if voice[j].playing:
                        st["slips"] += 1
                        break
                    j += 1

                if st["chunks"] % self.gc_every == 0:
                    gc.collect()

                pos += m
                left -= m
                idx = nxt
                n = m
                st["chunks"] += 1
                st["blocks"] += m
                if on_chunk is not None:
                    on_chunk(self, st)
            while voice[idx * ns].playing:
                pass
        except KeyboardInterrupt:
            self.stop()
            st["interrupted"] = True

        if st["chunks"] > 1:
            st["fill_ratio_mean"] = (
                st["fill_ms_sum"] / (st["chunks"] - 1) / (self.chunk_seconds * 1e3)
            )
        st["seconds"] = time.monotonic() - t_start
        st["audio_seconds"] = st["blocks"] * BLOCK_SECONDS
        st["frames"] = st["blocks"] * BLOCK_FRAMES
        if st["chunks"]:
            st["dead_ms"] = (st["seconds"] - st["audio_seconds"]) * 1e3 / st["chunks"]
        return st

    def solo(self, stem=None):
        """Hear one stem, or (with no argument) all of them again. A level
        change, so it lands on the mixer's next block rather than the next
        chunk."""
        if stem is None:
            self.levels = 1.0
        else:
            self.levels = [1.0 if s == stem else 0.0 for s in self.stems]

    def stop(self):
        for v in self.mixer.voice:
            v.stop()

    def deinit(self):
        """Drop the buffers, close the files and release the mixer. The mount
        and the `Audio` are the caller's."""
        self.stop()
        self._close()
        self._release()
        if self.mixer is not None:
            try:
                self.mixer.deinit()
            except Exception:
                pass
            self.mixer = None


def _round_blocks(n):
    """Down to a whole number of 512-byte blocks, never below one."""
    n = int(n) // BLOCK * BLOCK
    return max(BLOCK, n)


_MOUNTED = None


def _emmc_pins():
    """The board's eMMC wiring, as `emmcio.EMMC()` keyword arguments."""
    import board

    return {
        "clock": board.EMMC_CLK,
        "command": board.EMMC_CMD,
        "data": board.EMMC_DAT0,
        "reset": board.EMMC_RESET,
        "vccq": board.EMMC_VCCQ,
    }


def card_is_automounted(path=DEFAULT_MOUNT):
    """True when the supervisor already has the card mounted at `path`"""
    import storage

    try:
        return storage.getmount(path) is not storage.getmount("/")
    except Exception:
        return False


def mount_card(path=DEFAULT_MOUNT, high_speed=True):
    """Mount the eMMC read-only at `path` and return the `emmcio.EMMC`."""
    global _MOUNTED
    import storage
    import emmcio

    if _MOUNTED is not None:
        return _MOUNTED
    if card_is_automounted(path):
        return None
    # A previous run interrupted between mount and deinit leaves the mount
    # point occupied; REPL globals survive a soft reload.
    try:
        storage.umount(path)
    except Exception:
        pass
    emmc = emmcio.EMMC(high_speed=high_speed, **_emmc_pins())
    try:
        vfs = storage.VfsFat(emmc)
        storage.mount(vfs, path, readonly=True)
    except Exception:
        emmc.deinit()
        raise
    _MOUNTED = emmc
    return emmc


def umount_card(path=DEFAULT_MOUNT):
    """Unmount and deinit, so the next constructor can have the card."""
    global _MOUNTED
    import storage

    if _MOUNTED is None and card_is_automounted(path):
        return
    try:
        storage.umount(path)
    except Exception:
        pass
    if _MOUNTED is not None:
        try:
            _MOUNTED.deinit()
        except Exception:
            pass
    _MOUNTED = None


def info(path=DEFAULT_SONG, mount=True, high_speed=True):
    """Print what is on the card: the song, its stems, their alignment."""
    dev = mount_card(high_speed=high_speed) if mount else None
    try:
        if dev is not None:
            print("BUS|%d|%d" % (dev.frequency, 1 if dev.high_speed else 0))
        song = open_song(path)
        print(
            "SONG|%s|%d|%d|%.2f|%d|%d"
            % (
                song.path,
                song.nstems,
                song.blocks,
                song.seconds,
                1 if song.aligned else 0,
                1 if song.ragged else 0,
            )
        )
        for i in range(song.nstems):
            print(
                "STEM|%d|%s|%d|%d" % (i, song.paths[i], song.starts[i], song.sizes[i])
            )
        if not song.aligned:
            print(
                "  (a stem's `data` does not start on a 512 B boundary -- "
                "every read will leave f_read's fast path; re-prepare it "
                "with tools/sp1_wav_prep.py)"
            )
        return song
    finally:
        if mount:
            umount_card()


def listen(
    seconds=30,
    at=0.0,
    path=DEFAULT_SONG,
    stems=None,
    stem=None,
    levels=None,
    output="headphones",
    volume=0.35,
    minus6=False,
    chunk_bytes=None,
    fade_ms=None,
    gc_every=16,
    mixer_pad=None,
    mixer_buffer=None,
    high_speed=True,
    mount=True,
    audio=None,
    progress=5.0,
):
    """Play `seconds` of the song at `path`.
    `at` is seconds in, `stems` which of them to hear (all, summed by the
    mixer, by default), `seconds=None` plays the song out. Anything not passed
    in is constructed here and cleaned up on the way out, Ctrl-C included.
    """
    own_audio = audio is None
    player = None
    gc.collect()
    dev = mount_card(high_speed=high_speed) if mount else None
    try:
        if dev is not None:
            print("BUS|%d|%d" % (dev.frequency, 1 if dev.high_speed else 0))
        song = open_song(path)
        print(
            "SONG|%s|%d|%d|%.2f|%d|%d"
            % (
                song.path,
                song.nstems,
                song.blocks,
                song.seconds,
                1 if song.aligned else 0,
                1 if song.ragged else 0,
            )
        )
        if not song.aligned:
            print("  (unaligned stem data -- expect about half the read rate)")

        skip = int(at / BLOCK_SECONDS)
        if skip >= song.blocks:
            raise ValueError(
                "%.1f s is past the end of a %.1f s song" % (at, song.seconds)
            )
        start = skip
        count = song.blocks - skip

        if own_audio:
            import sp1_audio

            audio = sp1_audio.Audio(output=output, volume=volume, minus6=minus6)
        player = Player(
            song,
            audio,
            stems=stems,
            stem=stem,
            levels=levels,
            chunk_bytes=chunk_bytes,
            fade_ms=fade_ms,
            gc_every=gc_every,
            mixer_pad=mixer_pad,
            mixer_buffer=mixer_buffer,
        )
        played = ",".join([str(s) for s in player.stems])
        print(
            "PLAY|%s|%d|%d|%d|%.3f|%d|%d|%.3f|%d|%.2f"
            % (
                played,
                start,
                count,
                player.chunk_bytes,
                player.chunk_seconds,
                gc.mem_free(),
                player.fade_frames,
                player.fill_ratio_predicted,
                player.mixer_buffer,
                player.dead_air_ms,
            )
        )
        if player.chunk_shrunk:
            print(
                "  (the heap only had room for %d B chunks -- %.0f ms, so a "
                "boundary %.1f times a second)"
                % (
                    player.chunk_bytes,
                    player.chunk_seconds * 1e3,
                    1.0 / player.chunk_seconds,
                )
            )

        state = [time.monotonic()]

        def tick(p, st):
            if progress and time.monotonic() - state[0] >= progress:
                state[0] = time.monotonic()
                print(
                    "POS|%.1f|%d|%.2f"
                    % (st["blocks"] * BLOCK_SECONDS, st["underruns"], st["fill_ratio"])
                )

        audio.muted = False  # Audio comes up muted, like Codecs
        st = player.play(
            start, count, seconds=seconds, on_chunk=tick if progress else None
        )
        print(
            "STATS|%d|%d|%d|%.3f|%.1f|%.2f|%.2f|%d|%d|%.3f"
            % (
                st["chunks"],
                st["blocks"],
                st["underruns"],
                st["fill_ratio"],
                st["fill_ms_max"],
                st["audio_seconds"],
                st["seconds"],
                gc.mem_free(),
                st["slips"],
                st["fill_ratio_mean"],
            )
        )
        print(
            "  %s -- stem%s %s, %.1f s played in %.1f s, %d chunk(s) of "
            "%.0f ms, %d underrun(s), %d slip(s), worst fill %.0f%% of a chunk"
            % (
                song.path,
                "" if player.nstems == 1 else "s",
                played,
                st["audio_seconds"],
                st["seconds"],
                st["chunks"],
                player.chunk_seconds * 1e3,
                st["underruns"],
                st["slips"],
                st["fill_ratio"] * 100,
            )
        )
        return st
    finally:
        # Mute over I2C before anything stops
        if audio is not None:
            audio.stop()
        if player is not None:
            player.deinit()
        if own_audio and audio is not None:
            audio.deinit()
        if mount:
            umount_card()
        gc.collect()
