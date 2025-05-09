# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# sound_manager.py: CircuitPython Music Staff Application component
"""
# pylint: disable=import-error, trailing-whitespace
#
import math
import time
import array
import gc
import os
import digitalio
import busio


import adafruit_midi
import audiocore
import audiopwmio
import audiobusio
import audiomixer
import synthio
import board
import adafruit_tlv320
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import usb_midi


# pylint: disable=invalid-name,no-member,too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,broad-exception-caught
# pylint: disable=possibly-used-before-assignment,cell-var-from-loop
class SoundManager:
    """Handles playback of both MIDI notes and WAV samples, and synthio for channels 3-5"""

    def __init__(self, audio_output="pwm", seconds_per_eighth=0.25):
        """
        Initialize the sound manager

        Parameters:
        audio_output (str): The type of audio output to use - "pwm" or "i2s"
        seconds_per_eighth (float): Duration of an eighth note in seconds
        """
        # Initialize USB MIDI
        self.midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
        self.active_notes = {}  # {note_number: channel}

        # Store timing information
        self.seconds_per_eighth = seconds_per_eighth

        # Initialize audio output based on selected type
        self.audio_output_type = audio_output
        self.tlv = None

        # Initialize these variables to avoid use-before-assignment issues
        i2c = None
        bclck_pin = None
        wsel_pin = None
        din_pin = None

        if self.audio_output_type == "pwm":
            # Setup PWM audio output on D10
            self.audio = audiopwmio.PWMAudioOut(board.D10)
        else:  # i2s
            try:
                # Import libraries needed for I2S
                #check for Metro RP2350 vs. Fruit Jam
                board_type = os.uname().machine

                if 'Metro RP2350' in board_type:
                    print("Metro setup")
                    reset_pin = digitalio.DigitalInOut(board.D7)
                    reset_pin.direction = digitalio.Direction.OUTPUT
                    reset_pin.value = False  # Set low to reset
                    time.sleep(0.1)  # Pause 100ms
                    reset_pin.value = True  # Set high to release from reset

                    i2c = board.STEMMA_I2C()  # initialize I2C

                    bclck_pin = board.D9
                    wsel_pin = board.D10
                    din_pin = board.D11

                elif 'Fruit Jam' in board_type:
                    print("Fruit Jam setup")
                    reset_pin = digitalio.DigitalInOut(board.PERIPH_RESET)
                    reset_pin.direction = digitalio.Direction.OUTPUT
                    reset_pin.value = False
                    time.sleep(0.1)
                    reset_pin.value = True

                    i2c = busio.I2C(board.SCL, board.SDA)

                    bclck_pin = board.I2S_BCLK
                    wsel_pin = board.I2S_WS
                    din_pin = board.I2S_DIN

                # Initialize TLV320
                self.tlv = adafruit_tlv320.TLV320DAC3100(i2c)
                self.tlv.configure_clocks(sample_rate=11025, bit_depth=16)
                self.tlv.headphone_output = True
                self.tlv.headphone_volume = -15  # dB

                # Setup I2S audio output - important to do this AFTER configuring the DAC
                self.audio = audiobusio.I2SOut(
                    bit_clock=bclck_pin,
                    word_select=wsel_pin,
                    data=din_pin
                )

                print("TLV320 I2S DAC initialized successfully")
            except Exception as e:
                print(f"Error initializing TLV320 DAC: {e}")
                print("Falling back to PWM audio output")
                # Fallback to PWM if I2S initialization fails
                self.audio = audiopwmio.PWMAudioOut(board.D10)

        # Create an audio mixer with multiple voices
        self.mixer = audiomixer.Mixer(
            voice_count=6,
            sample_rate=11025,
            channel_count=1,
            bits_per_sample=16,
            samples_signed=True
        )
        self.audio.play(self.mixer)

        # Track which voices are being used for samples
        # First 3 for regular samples, next 3 for playback-only
        self.active_voices = [False, False, False, False, False, False]

        # Track which note position corresponds to which voice
        # This will help us stop samples when notes are erased
        self.position_to_voice = {}  # {(x_pos, y_pos): voice_index}

        # Track which voice is used for which channel during playback
        self.playback_voice_mapping = {}  # {(x_pos, y_pos, channel): voice_index}

        # Load multiple WAV samples at different pitches
        try:
            # Channel 1 samples
            self.samples = {
                59: audiocore.WaveFile("/samples/larso_B3.wav"),  # B3
                60: audiocore.WaveFile("/samples/larso_C4.wav"),  # C4
                62: audiocore.WaveFile("/samples/larso_D4.wav"),  # D4
                64: audiocore.WaveFile("/samples/larso_E4.wav"),  # E4
                65: audiocore.WaveFile("/samples/larso_F4.wav"),  # F4
                67: audiocore.WaveFile("/samples/larso_G4.wav"),  # G4
                69: audiocore.WaveFile("/samples/larso_A4.wav"),  # A4
                71: audiocore.WaveFile("/samples/larso_B4.wav"),  # B4
                72: audiocore.WaveFile("/samples/larso_C5.wav"),  # C5
                74: audiocore.WaveFile("/samples/larso_D5.wav"),  # D5
                76: audiocore.WaveFile("/samples/larso_E5.wav"),  # E5
                77: audiocore.WaveFile("/samples/larso_F5.wav"),  # F5
                79: audiocore.WaveFile("/samples/larso_G5.wav"),  # G5
            }
            print("Loaded channel 1 WAV samples")

            # Load samples for channel 2
            self.heart_samples = {
                59: audiocore.WaveFile("/samples/musicnote16_B3.wav"),  # B3
                60: audiocore.WaveFile("/samples/musicnote16_C4.wav"),  # C4
                62: audiocore.WaveFile("/samples/musicnote16_D4.wav"),  # D4
                64: audiocore.WaveFile("/samples/musicnote16_E4.wav"),  # E4
                65: audiocore.WaveFile("/samples/musicnote16_F4.wav"),  # F4
                67: audiocore.WaveFile("/samples/musicnote16_G4.wav"),  # G4
                69: audiocore.WaveFile("/samples/musicnote16_A4.wav"),  # A4
                71: audiocore.WaveFile("/samples/musicnote16_B4.wav"),  # B4
                72: audiocore.WaveFile("/samples/musicnote16_C5.wav"),  # C5
                74: audiocore.WaveFile("/samples/musicnote16_D5.wav"),  # D5
                76: audiocore.WaveFile("/samples/musicnote16_E5.wav"),  # E5
                77: audiocore.WaveFile("/samples/musicnote16_F5.wav"),  # F5
                79: audiocore.WaveFile("/samples/musicnote16_G5.wav"),  # G5
            }
            print("Loaded channel 2 WAV samples")

            # Load samples for channel 3 (drum samples)
            self.drum_samples = {}
            try:
                self.drum_samples = {
                    59: audiocore.WaveFile("/samples/kick_01.wav"),
                    60: audiocore.WaveFile("/samples/kick_01.wav"),
                    62: audiocore.WaveFile("/samples/kick_01.wav"),
                    64: audiocore.WaveFile("/samples/snare_01.wav"),
                    65: audiocore.WaveFile("/samples/snare_01.wav"),
                    67: audiocore.WaveFile("/samples/snare_01.wav"),
                    69: audiocore.WaveFile("/samples/chat_01.wav"),
                    71: audiocore.WaveFile("/samples/chat_01.wav"),
                    72: audiocore.WaveFile("/samples/chat_01.wav"),
                    74: audiocore.WaveFile("/samples/ohat_01.wav"),
                    76: audiocore.WaveFile("/samples/ohat_01.wav"),
                    77: audiocore.WaveFile("/samples/crash_01.wav"),
                    79: audiocore.WaveFile("/samples/crash_01.wav"),
                }
                print("Loaded channel 3 WAV samples (drums)")
            except Exception as e:
                print(f"Error loading drum samples: {e}")
                # Fallback - use the same samples as channel 1
                self.drum_samples = self.samples
                print("Using fallback samples for channel 3")

        except Exception as e:
            print(f"Error loading WAV samples: {e}")
            # Fallback to basic samples if there's an error
            self.samples = {
                65: audiocore.WaveFile("/samples/musicnote01.wav"),  # Default sample
            }
            self.heart_samples = self.samples  # Use same samples as fallback
            self.drum_samples = self.samples   # Use same samples as fallback

        # Initialize synthio for channels 4-6
        self.synth = synthio.Synthesizer(sample_rate=11025)
        # Use the last voice for synthio
        self.mixer.voice[5].play(self.synth)

        # Set lower volume for synthio channel
        self.mixer.voice[5].level = 0.3

        # Create waveforms for different synthio channels
        SAMPLE_SIZE = 512
        SAMPLE_VOLUME = 30000  # Slightly lower to avoid overflow
        half_period = SAMPLE_SIZE // 2

        # Sine wave for channel 4
        self.wave_sine = array.array("h", [0] * SAMPLE_SIZE)
        for i in range(SAMPLE_SIZE):
            # Use max() and min() to ensure we stay within bounds
            value = int(math.sin(math.pi * 2 * (i/2) / SAMPLE_SIZE) * SAMPLE_VOLUME)
            self.wave_sine[i] = max(-32768, min(32767, value))

        # Triangle wave for channel 5
        self.wave_tri = array.array("h", [0] * SAMPLE_SIZE)
        for i in range(SAMPLE_SIZE):
            if i < half_period:
                value = int(((i / (half_period)) * 2 - 1) * SAMPLE_VOLUME)
            else:
                value = int(((2 - (i / (half_period)) * 2)) * SAMPLE_VOLUME)
            self.wave_tri[i] = max(-32768, min(32767, value))

        # Sawtooth wave for channel 6
        self.wave_saw = array.array("h", [0] * SAMPLE_SIZE)
        for i in range(SAMPLE_SIZE):
            value = int(((i / SAMPLE_SIZE) * 2 - 1) * SAMPLE_VOLUME)
            self.wave_saw[i] = max(-32768, min(32767, value))

        # Map channels to waveforms
        self.channel_waveforms = {
            3: self.wave_sine,      # Channel 4: Sine wave (soft, pure tone)
            4: self.wave_tri,       # Channel 5: Triangle wave (mellow, soft)
            5: self.wave_saw,       # Channel 6: Sawtooth wave (brassy, sharp)
        }

        # Set different amplitudes for each waveform to balance volumes
        self.channel_amplitudes = {
            3: 1.0,    # Sine wave - normal volume
            4: 0.8,    # Triangle wave - slightly quieter
            5: 0.3,    # Sawtooth wave - much quieter (harmonically rich)
        }

        # Track active synth notes by channel and note
        self.active_synth_notes = {
            3: [],  # Channel 4
            4: [],  # Channel 5
            5: [],  # Channel 6
        }

        # Variables for timed release of preview notes
        self.note_release_time = 0
        self.note_to_release = None
        self.note_to_release_channel = None
        self.preview_mode = False

    def play_note(self, midi_note, channel):
        """Play a note using either MIDI, WAV, or synthio based on channel"""
        if channel == 0:  # Channel 1 uses WAV samples
            self.play_multi_sample(midi_note, channel)
        elif channel == 1:  # Channel 2 uses Heart note WAV samples
            self.play_multi_sample(midi_note, channel)
        elif channel == 2:  # Channel 3 uses Drum WAV samples
            self.play_multi_sample(midi_note, channel)
        elif channel in [3, 4, 5]:  # Channels 4-6 use synthio with different waveforms
            self.preview_mode = True
            self.play_synth_note(midi_note, channel)
            # Schedule note release
            self.note_release_time = time.monotonic() + self.seconds_per_eighth
            self.note_to_release_channel = channel
        else:
            # Send note on the correct MIDI channel (channels are 0-based in adafruit_midi)
            self.midi.send(NoteOn(midi_note, 100), channel=channel)
            # Store note with its channel for proper Note Off later
            self.active_notes[midi_note] = channel
            # print(f"Playing note: {midi_note} on channel {channel + 1}")

    def play_notes_at_position(self, notes_data):
        """Play all notes at a specific position simultaneously"""
        # Stop all sample voices first
        for i in range(5):  # Use first 5 voices for WAV samples (0-4)
            self.mixer.voice[i].stop()
            self.active_voices[i] = False

        # Clear the position to voice mapping
        self.position_to_voice = {}
        self.playback_voice_mapping = {}

        # Group notes by channel type
        sample_notes = {
            0: [],  # Channel 1 (Lars WAV samples)
            1: [],  # Channel 2 (Heart WAV samples)
            2: []   # Channel 3 (Drum WAV samples)
        }

        # Synthio channels (4-6)
        synth_notes = {
            3: [],  # Channel 4 (Sine wave)
            4: [],  # Channel 5 (Triangle wave)
            5: [],  # Channel 6 (Sawtooth wave)
        }

        midi_notes = {}    # Other channels (MIDI)

        for x_pos, y_pos, note_val, channel in notes_data:
            if channel in [0, 1, 2]:  # Sample-based channels
                sample_notes[channel].append((x_pos, y_pos, note_val))
            elif channel in [3, 4, 5]:  # Synthio channels
                synth_notes[channel].append(note_val)
            else:  # Other channels (MIDI)
                midi_notes[note_val] = channel

        # Voice allocation - we have 5 voices to distribute among sample notes
        remaining_voices = 5
        voice_index = 0

        # Play sample notes for channels 1-3
        for channel, notes in sample_notes.items():
            for x_pos, y_pos, midi_note in notes:
                if remaining_voices <= 0:
                    print(f"Warning: No more voices available for channel {channel+1}")
                    break

                # Get the appropriate sample set
                sample_set = None
                if channel == 0:
                    sample_set = self.samples
                elif channel == 1:
                    sample_set = self.heart_samples
                elif channel == 2:
                    sample_set = self.drum_samples

                # Find the closest sample
                closest_note = min(sample_set.keys(), key=lambda x: abs(x - midi_note))
                sample = sample_set[closest_note]

                # Play the sample
                self.mixer.voice[voice_index].play(sample, loop=False)
                self.active_voices[voice_index] = True

                # Store the position to voice mapping
                position_key = (x_pos, y_pos)
                self.position_to_voice[position_key] = voice_index
                self.playback_voice_mapping[(x_pos, y_pos, channel)] = voice_index

                # Adjust volume
                total_notes = sum(len(notes) for notes in sample_notes.values())
                volume_factor = 0.9 if total_notes <= 3 else 0.7 if total_notes <= 6 else 0.5
                self.mixer.voice[voice_index].level = 0.7 * volume_factor

                voice_index += 1
                remaining_voices -= 1

            # Log what we're playing
            # Channel names commented out as it was unused
            # channel_names = ["Lars", "Heart", "Drum"]
            # print(f"Playing {channel_names[channel]} sample {closest_note} for note {midi_note}")

        # Play synth notes for each channel (4-6)
        self.preview_mode = False
        for channel, notes in synth_notes.items():
            for note in notes:
                self.play_synth_note(note, channel)

        # Play MIDI notes
        for midi_note, channel in midi_notes.items():
            self.midi.send(NoteOn(midi_note, 100), channel=channel)
            self.active_notes[midi_note] = channel

    def play_multi_sample(self, midi_note, channel=0):
        """Play the most appropriate sample for the given MIDI note"""
        try:
            # Find an available voice (use first 3 voices for interactive play)
            voice_index = -1
            for i in range(3):  # Only use the first 3 voices for interactive playback
                if not self.active_voices[i]:
                    voice_index = i
                    break

            # If all voices are active, use the first one
            if voice_index == -1:
                voice_index = 0

            # Stop any currently playing sample in this voice
            self.mixer.voice[voice_index].stop()

            # Select the appropriate sample set based on channel
            if channel == 1:  # Heart samples
                sample_set = self.heart_samples
            elif channel == 2:  # Drum samples
                sample_set = self.drum_samples
            else:  # Default to channel 1 samples
                sample_set = self.samples

            # Find the closest sample
            closest_note = min(sample_set.keys(), key=lambda x: abs(x - midi_note))

            # Get the sample
            sample = sample_set[closest_note]

            # Play the sample
            self.mixer.voice[voice_index].play(sample, loop=False)
            self.active_voices[voice_index] = True

            # Adjust volume based on which sample we're using
            if closest_note == 65:  # F4
                self.mixer.voice[voice_index].level = 0.8
            elif closest_note == 69:  # A4
                self.mixer.voice[voice_index].level = 0.7
            elif closest_note == 72:  # C5
                self.mixer.voice[voice_index].level = 0.6
            else:
                self.mixer.voice[voice_index].level = 0.7

        except Exception as e:
            print(f"Error playing multi-sample: {e}")
            # Try to play any available sample as a fallback
            if len(self.samples) > 0:
                first_sample = next(iter(self.samples.values()))
                self.mixer.voice[0].play(first_sample, loop=False)

    def play_synth_note(self, midi_note, channel):
        """Play a note using synthio with different waveforms per channel"""
        try:
            # Convert MIDI note to frequency
            frequency = 440 * math.pow(2, (midi_note - 69) / 12)

            # Get the appropriate waveform for this channel
            waveform = self.channel_waveforms.get(channel, self.wave_sine)

            # Get the appropriate amplitude for this channel
            amplitude = self.channel_amplitudes.get(channel, 1.0)

            # Create synthio note with the specific waveform and amplitude
            note = synthio.Note(
                frequency,
                waveform=waveform,
                amplitude=amplitude
            )

            # Add to synth
            self.synth.press(note)

            # If we have an existing preview note to release, release it first
            if self.preview_mode and self.note_to_release and self.note_to_release_channel==channel:
                try:
                    self.synth.release(self.note_to_release)
                except Exception as e:
                    print(f"Error releasing previous note: {e}")

            # Store the new note for scheduled release if in preview mode
            if self.preview_mode:
                self.note_to_release = note
                self.note_to_release_channel = channel
            else:
                self.active_synth_notes[channel].append(note)

        except Exception as e:
            print(f"Error playing synthio note: {e}")
            # If there's an error with custom waveforms, fall back to default note
            try:
                frequency = 440 * math.pow(2, (midi_note - 69) / 12)
                note = synthio.Note(frequency)
                self.synth.press(note)

                # Store for later release
                if self.preview_mode:
                    self.note_to_release = note
                    self.note_to_release_channel = channel
                else:
                    self.active_synth_notes[channel].append(note)

            except Exception as e2:
                print(f"Fallback note error: {e2}")

    def stop_sample_at_position(self, x_pos, y_pos, channel):
        """Stop a sample that's playing at the given position for a specific channel"""
        position_key = (x_pos, y_pos, channel)
        if position_key in self.playback_voice_mapping:
            voice_index = self.playback_voice_mapping[position_key]

            # Stop the sample
            self.mixer.voice[voice_index].stop()
            self.active_voices[voice_index] = False

            # Remove from mappings
            del self.playback_voice_mapping[position_key]
            return True

        # Also check the simple position mapping
        simple_key = (x_pos, y_pos)
        if simple_key in self.position_to_voice:
            voice_index = self.position_to_voice[simple_key]

            # Stop the sample
            self.mixer.voice[voice_index].stop()
            self.active_voices[voice_index] = False

            # Remove from mapping
            del self.position_to_voice[simple_key]
            return True

        return False

    def update(self):
        """Update function to handle timed note releases"""
        # Check if we need to release a preview note
        if self.note_to_release and time.monotonic() >= self.note_release_time:
            try:
                self.synth.release(self.note_to_release)
                self.note_to_release = None
                self.note_to_release_channel = None
            except Exception as e:
                print(f"Error releasing preview note: {e}")
                self.note_to_release = None
                self.note_to_release_channel = None

    def stop_all_notes(self):
        """Stop all currently playing notes"""
        # Stop all MIDI notes
        for note_number, channel in self.active_notes.items():
            self.midi.send(NoteOff(note_number, 0), channel=channel)
        self.active_notes = {}

        # Stop all WAV samples
        for i in range(5):  # Use first 5 voices for WAV samples
            self.mixer.voice[i].stop()
            self.active_voices[i] = False

        # Clear position mappings
        self.position_to_voice = {}
        self.playback_voice_mapping = {}

        # Stop all synth notes
        try:
            # Release notes from all channels
            for channel, notes in self.active_synth_notes.items():
                for note in notes:
                    self.synth.release(note)
                self.active_synth_notes[channel] = []

            # Also release preview note if there is one
            if self.note_to_release:
                self.synth.release(self.note_to_release)
                self.note_to_release = None
                self.note_to_release_channel = None

        except Exception as e:
            print(f"Error releasing synth notes: {e}")
            # Reinitialize the synth as a fallback
            try:
                self.synth.deinit()
                self.synth = synthio.Synthesizer(sample_rate=11025)
                self.mixer.voice[5].play(self.synth)

                # Reset all active notes
                self.active_synth_notes = {
                    3: [],  # Channel 4
                    4: [],  # Channel 5
                    5: [],  # Channel 6
                }
            except Exception as e2:
                print(f"Error reinitializing synth: {e2}")

    def deinit(self):
        """Clean up resources when shutting down"""
        # Stop all sounds
        self.stop_all_notes()

        # Clean up audio resources
        try:
            self.audio.deinit()
        except Exception:
            pass

        # Power down the TLV320 if applicable
        if self.tlv:
            try:
                # For TLV320DAC3100, headphone_output = False will power down the output
                self.tlv.headphone_output = False
            except Exception:
                pass

        # Clean up synth
        try:
            self.synth.deinit()
        except Exception:
            pass

        # Force garbage collection
        gc.collect()

    def set_tempo(self, seconds_per_eighth):
        """Update the playback tempo"""
        self.seconds_per_eighth = seconds_per_eighth
        print(f"Playback tempo updated: {60 / (seconds_per_eighth * 2)} BPM")
