# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# DTMF keypad phone Dial-a-Song
import time
import random
import board
import keypad
from audiocore import WaveFile
from audiopwmio import PWMAudioOut as AudioOut  # for RP2040 etc
import audiomixer

# time.sleep(3)  # let USB settle during development, remove when on battery

km = keypad.KeyMatrix(
    # 2500 phone ignoring first column store/redial/memory. reverse mount on Feather RP2040
    column_pins=(          board.A3, board.A2, board.A1,),
    row_pins=(
                board.D24,
                board.D25,
                board.SCK,
                board.MOSI,
                 ),
)

numbers = {
            "8675309" : "songs/beepbox.wav",
            "6358393" : "songs/streetchicken.wav",
            "5551212" : "songs/carpeter.wav",
            "7654321" : "songs/daisy.wav"
}

ringing = "songs/full_ring.wav"
wrong_number = "songs/blank_number.wav"
dial_tone = "songs/dial_tone_loop.wav"
busy_signal = "songs/busy_loop.wav"

button_tones = [
                "dtmf/tt_1.wav", "dtmf/tt_2.wav",  "dtmf/tt_3.wav",
                "dtmf/tt_4.wav", "dtmf/tt_5.wav", "dtmf/tt_6.wav",
                "dtmf/tt_7.wav", "dtmf/tt_8.wav", "dtmf/tt_9.wav",
                "dtmf/tt_star.wav", "dtmf/tt_0.wav", "dtmf/tt_pound.wav"
]

digits_entered = 0  # counter
dialed = []  # list of digits user enters to make one 7 digit number
dialed_str = ""  # stores the phone number string for dictionary comparison

audio = AudioOut(board.TX)  # PWM out pin
mixer = audiomixer.Mixer(
    voice_count=4,
    sample_rate=22050,
    channel_count=1,
    bits_per_sample=16,
    samples_signed=True,
)
audio.play(mixer)
mixer.voice[0].level = 1.0  # dial tone voice
mixer.voice[1].level = 1.0  # touch tone voice
mixer.voice[2].level = 0.0  # song/message voice
mixer.voice[3].level = 0.0  # busy signal

wave_file0 = open(dial_tone, "rb")
wave0 = WaveFile(wave_file0)
mixer.voice[0].play(wave0, loop=True)  # play dial tone

wave_file2 = open(wrong_number, "rb")
wave2 = WaveFile(wave_file2)

wave_file3 = open(busy_signal, "rb")
wave3 = WaveFile(wave_file3)
mixer.voice[3].play(wave3, loop=True)  # play dial tone


def reset_number():
    # pylint: disable=global-statement
    global digits_entered, dialed, dialed_str
    digits_entered = 0
    dialed = []
    dialed_str = ""
    km.events.clear()


while True:

    event = km.events.get()  # check for keypad presses
    if event:
        if event.pressed:
            mixer.voice[0].level = 0.0  # mute the dial tone
            wave_file1 = open(button_tones[event.key_number], "rb")  # play Touch Tone
            wave1 = WaveFile(wave_file1)
            mixer.voice[1].play(wave1)
            if event.key_number == 9 or event.key_number == 11:  # check for special keys
                if event.key_number == 9:  # pressed the '*' key
                    reset_number()   # or make some cool new function for this key
                if event.key_number == 11:  # pressed the '#' key
                    reset_number()  # or make some cool new function for this key

            else:  # number keys
                if digits_entered < 7:  # adding up to full number
                    # convert event to number printed on the keypad button, append to string
                    if event.key_number < 9:  # 1-9 on keypad
                        dialed.append(event.key_number+1)
                    if event.key_number == 10:  # the 0 key, ignore '*' and "#'
                        dialed.append(0)
                    dialed_str = "".join(str(n) for n in dialed)
                    digits_entered = digits_entered + 1  # increment counter

                if digits_entered == 7:  # a full number has been entered
                    if not mixer.voice[2].playing:
                        dialed_str = "".join(str(n) for n in dialed)
                        if dialed_str in numbers:  # check if dialed string is one in the directory
                            value = numbers[dialed_str]
                            time.sleep(0.6)

                            wave_file2 = open(ringing, "rb")  # ring before it answers
                            wave2 = WaveFile(wave_file2)
                            mixer.voice[2].level = 1.0
                            mixer.voice[2].play(wave2, loop=True)

                            time.sleep(random.uniform(4.0, 9.5))  # random ring before "answer"

                            wave_file2 = open(value, "rb")  # answered
                            wave2 = WaveFile(wave_file2)
                            mixer.voice[2].level = 1.0
                            mixer.voice[2].play(wave2, loop=True)

                        else:  # number is not in directory
                            time.sleep(0.5)
                            weighted_coin_toss = random.randint(0, 4)
                            if weighted_coin_toss < 3:  # favor the "not in service" message
                                mixer.voice[2].level = 1.0
                                mixer.voice[2].play(wave2)
                            else:
                                mixer.voice[3].level = 1.0

                        reset_number()

                    if mixer.voice[2].playing:
                        reset_number() # stop #s dialed during message play from doing anything
