# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import audiobusio
import audiocore
import audiodelays
import audiofilewriter
import audiofilters
import audioi2sin
import audiomixer
import board
from pwmio import PWMOut
import usb.core

import adafruit_midi
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.control_change import ControlChange
import adafruit_midi_parser
import adafruit_tlv320
import adafruit_usb_host_midi
from neopixel import NeoPixel


OUTPUT_PATH = "/sd/sample0.wav"
SONG_PATH = "/anna-magdalena-20a.mid"
CC_RECORD = 77  # midi CC control value to initiate recording
CC_PLAY_SONG = 78  # midi CC control value to initiate playing a song
SONG_PLAYBACK_BPM = 135

# Default debounce window (seconds) for control change messages.
CC_DEBOUNCE_DEFAULT = 1.0
# Per-control overrides, keyed by CC number, for buttons that need a longer
# or shorter debounce window than the default.
CC_COOLDOWNS = {
    CC_PLAY_SONG: 3.0,
}
# Tracks the last accepted time for each CC number so duplicates arriving
# within the debounce window can be ignored.
last_cc_time = {}

SAMPLE_RATE = 16000
STATE = "playing"
pixels = NeoPixel(board.NEOPIXEL, 5, brightness=0.1)


def cc_debounced(control):
    """Return True if this control change should be acted on.

    Looks up (or falls back to the default) cooldown window for `control`,
    compares against the last time this control was accepted, and - if
    enough time has passed - records the new time and returns True. This
    replaces having a separate `last_*` variable and cooldown check for
    every individual CC button.
    """
    now = time.monotonic()
    cooldown = CC_COOLDOWNS.get(control, CC_DEBOUNCE_DEFAULT)
    if now >= last_cc_time.get(control, 0) + cooldown:
        last_cc_time[control] = now
        return True
    return False


# --- Set up USB Host Midi keyboard ---
print("Looking for midi device")
raw_midi = None
while raw_midi is None:
    for device in usb.core.find(find_all=True):
        try:
            raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=0.01)
            print("Found midi device: ", hex(device.idVendor), hex(device.idProduct))
        except ValueError:
            continue
midi = adafruit_midi.MIDI(midi_in=raw_midi, in_channel=0, debug=True)

# --- Set up DAC & 3.5mm output ---
mclk_pwm = PWMOut(board.I2S_MCLK, frequency=15_000_000, duty_cycle=2**15)
i2c = board.I2C()
dac = adafruit_tlv320.TLV320DAC3100(i2c)
dac.configure_clocks(sample_rate=44100, bit_depth=16, mclk_freq=15_000_000)
dac.headphone_output = True
dac.dac_volume = 0  # dB
dac.headphone_volume = -10
audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)


# --- Set up polyphony ---
# audiomixer with 4 voices to play up to 4 things at once
mixer = audiomixer.Mixer(
    voice_count=4,
    sample_rate=16000,
    channel_count=1,
    bits_per_sample=16,
    samples_signed=True,
)
audio.play(mixer)

# --- Set up I2S Microphone ---
mic = audioi2sin.I2SIn(
    bit_clock=board.D6,
    word_select=board.D7,
    data=board.D9,
    sample_rate=SAMPLE_RATE,
    bit_depth=32,
    output_bit_depth=16,
    mono=True,
    left_justified=False,  # True for SPH0645LM4H
)
actual_rate = mic.sample_rate

# --- General variables ---
effect_chains = []
samples = []
recording_file = None


# --- Set up samples ---
class DataContext:
    def __init__(self):
        self.data_start = None
        self.pcm = None
        self.cur_voice_index = 0

        # Lazily created the first time CC 78 arrives.
        self.song_player = None


data_context = DataContext()


def load_samples():
    with open(OUTPUT_PATH, "rb") as f:
        raw = f.read()
    data_context.data_start = raw.find(b"data") + 8  # skip 'data' + length field
    data_context.pcm = memoryview(raw)[data_context.data_start :].cast(
        "h"
    )  # signed 16-bit view, matches the chain

    samples.clear()
    for _ in range(len(mixer.voice)):
        # per voice, pre-allocate a RawSample
        sample = audiocore.RawSample(
            data_context.pcm, sample_rate=16000, channel_count=1
        )
        samples.append(sample)


try:
    load_samples()
except OSError:
    print("No sample file")

# --- Set up effects chains ---
# One chain instance per mixer voice
for i in range(len(mixer.voice)):
    new_chain = []

    # amp used for pre_gain only to boost volume
    amp = audiofilters.Distortion(
        pre_gain=23.6,
        drive=0.0,  # drive 0.0 for no distortion
        mode=audiofilters.DistortionMode.LOFI,
        soft_clip=True,
        mix=1.0,
        buffer_size=1024,
        sample_rate=SAMPLE_RATE,
        bits_per_sample=16,
        samples_signed=True,
        channel_count=1,
    )

    # pitch shifter to tune sample up or down
    gran_pitch_shift = audiodelays.GranularPitchShift(
        semitones=7.0,
        mix=1.0,
        grain_size=1024,
        spread=0.125,
        density=4,
        buffer_size=1024,
        channel_count=1,
        sample_rate=16000,
    )

    # add both effects to the new chain
    new_chain.append(amp)
    new_chain.append(gran_pitch_shift)

    # add the chain to the list of chains
    effect_chains.append(new_chain)


# --- note and song playback handling ---
def trigger_note(note):
    """Play the current sample pitch-shifted to `note` on the next mixer voice.

    Shared by the live keyboard and the MIDI-file song player so both behave
    identically (semitones relative to middle C, round-robin voice stealing).
    """

    effect_chain = effect_chains[data_context.cur_voice_index]
    # set the pitch shift semi-tone for note
    effect_chain[1].semitones = note - 60
    # walk thru the chain and call play() on each effect
    for chain_index in range(len(effect_chain)):
        if chain_index == 0:
            # 0 index effect calls play() on the sample
            effect_chain[chain_index].play(samples[data_context.cur_voice_index])
        else:
            # all other effects call play() on the prior effect in the chain
            effect_chain[chain_index].play(effect_chain[chain_index - 1])

    # play the last link in the effect chain on the current mixer voice
    mixer.voice[data_context.cur_voice_index].play(effect_chain[-1])

    # increment current voice index for next time
    data_context.cur_voice_index = (data_context.cur_voice_index + 1) % len(mixer.voice)


class SamplerMIDIPlayer(adafruit_midi_parser.MIDIPlayer):
    """Drives the sampler voices from a parsed MIDI file.

    Each note-on re-triggers the sample pitch-shifted to that note, exactly like
    pressing a key. Notes are one-shot RawSamples that ring out, so note-off is
    a no-op, matching the live keyboard's behavior.
    """

    # pylint: disable=unused-argument, no-self-use
    # `self`, `velocity`, and `channel` are required by the parent interface
    # even though they are unused by this subclass implementation.
    def on_note_on(self, note, velocity, channel):
        trigger_note(note)


def start_song():
    """Parse (once) and (re)start playback of SONG_PATH."""

    if data_context.song_player is None:
        try:
            parser = adafruit_midi_parser.MIDIParser()
            parser.parse(SONG_PATH)
            parser.bpm = SONG_PLAYBACK_BPM
            print(
                f"Parsed {SONG_PATH}: {len(parser.events)} events, "
                + f"{parser.note_count} notes, {parser.bpm:.1f} BPM"
            )
            data_context.song_player = SamplerMIDIPlayer(parser)

        except adafruit_midi_parser.MIDIParseError as e:
            print("Could not load song:", e)
            return False
    else:
        # Rewind so a fresh CC_PLAY_SONG restarts from the top.
        data_context.song_player.stop()
        data_context.song_player.parser.reset()
    return True


# --- main loop ---
while True:
    # Advance MIDI-file playback (non-blocking) while a song is active.
    if STATE == "song" and data_context.song_player is not None:
        data_context.song_player.play()
        if data_context.song_player.finished:
            STATE = "playing"
            pixels[0] = 0x000000

    try:
        msg = midi.receive()
    except usb.core.USBError as usbe:
        print("Ignoring USB error", usbe)

    # if keyboard note was pressed
    if isinstance(msg, NoteOn) and msg.velocity != 0:
        # if we're in live play state
        if STATE == "playing":
            print(
                "noteOn: ", msg.note, "vel:", msg.velocity, data_context.cur_voice_index
            )
            trigger_note(msg.note)

        # if we're waiting to start recording
        elif STATE == "recording_prompt":
            # turn pixel red and begin recording
            pixels[0] = 0xFF0000
            STATE = "recording"

            # cannot use `with` because file must remain open beyond this context
            recording_file = open(OUTPUT_PATH, "wb")
            writer = audiofilewriter.AudioFileWriter(recording_file)
            writer.play(mic)

    # if keyboard note was released
    elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
        # only care about note release if we're recording
        if STATE == "recording":
            # stop the recording and load the new sample
            print("noteOff:", msg.note, "vel:", msg.velocity)
            print("ending recording")
            writer.stop()
            recording_file.close()
            load_samples()
            # turn pixel off and change state to live play
            pixels[0] = 0x000000
            STATE = "playing"

    # if control change button was pressed
    elif isinstance(msg, ControlChange):

        # print(msg)
        # print(msg.__bytes__())

        if not cc_debounced(msg.control):
            # duplicate event from the keyboard within the cooldown window;
            # ignore it
            pass

        # prompt to start recording
        elif msg.control == CC_RECORD:
            print("recording prompt")
            STATE = "recording_prompt"
            pixels[0] = 0xFFFF00

        # start playing midi song
        elif msg.control == CC_PLAY_SONG:
            print("play song")
            if start_song():
                pixels[0] = 0x00FF00
                STATE = "song"

    # print unknown event messages
    elif msg is not None:
        print(msg)
        print(dir(msg))
