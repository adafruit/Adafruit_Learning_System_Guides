# FT8 (and now FT4) library 

C implementation of a lightweight FT8/FT4 decoder and encoder, mostly intended for experimental use on microcontrollers.

The intent of this library is to allow FT8/FT4 encoding and decoding in standalone environments (i.e. without a PC or RPi), e.g. automated beacons or SDR transceivers. It's also my learning process, optimization problem and source of fun.

The encoding process is relatively light on resources, and an Arduino should be perfectly capable of running this code.

The decoder is designed with memory and computing efficiency in mind, in order to be usable with a fast enough microcontroller. It is shown to be working on STM32F7 boards fast enough for real work, but the embedded application itself is beyond this repository. This repository provides an example decoder which can decode a 15-second WAV file on a desktop machine or SBC. The decoder needs to access the whole 15-second window in spectral magnitude representation (the window can be also shorter, and messages can have varying starting time within the window). The example FT8 decoder can work with slightly less than 200 KB of RAM. 

# Current state

Currently the basic message set for establishing QSOs, as well as telemetry and free-text message modes are supported:
* CQ {call} {grid}, e.g. CQ CA0LL GG77
* CQ {xy} {call} {grid}, e.g. CQ JA CA0LL GG77
* {call} {call} {report}, e.g. CA0LL OT7ER R-07
* {call} {call} 73/RRR/RR73, e.g. OT7ER CA0LL 73
* Free-text messages (up to 13 characters from a limited alphabet) (decoding only, untested)
* Telemetry data (71 bits as 18 hex symbols)

Encoding and decoding works for both FT8 and FT4. For encoding and decoding, there is a console application provided for each, which serves mostly as test code, and could be a starting point for your potential application on an MCU. The console apps should run perfectly well on a RPi or a PC/Mac. I don't provide a concrete example for a particular MCU hardware here, since it would be very specific.

The code is not yet really a library, rather a collection of routines and example code.

# Future ideas

Incremental decoding (processing during the 15 second window) is something that I would like to explore, but haven't started.

These features are low on my priority list:
* Contest modes
* Compound callsigns with country prefixes and special callsigns

# What to do with it

You can generate 15-second WAV files with your own messages as a proof of concept or for testing purposes. They can either be played back or opened directly from WSJT-X. To do that, run ```make```. Then run ```gen_ft8``` (run it without parameters to check what parameters are supported). Currently messages are modulated at 1000-1050 Hz.

You can decode 15-second (or shorter) WAV files with ```decode_ft8```. This is only an example application and does not support live processing/recording. For that you could use third party code (PortAudio, for example).

# References and credits

Thanks goes out to:
* my contributors who have provided me with various improvements which have often been beyond my skill set.
* Robert Morris, AB1HL, whose Python code (https://github.com/rtmrtmrtmrtm/weakmon) inspired this and helped to test various parts of the code.
* Mark Borgerding for his FFT implementation (https://github.com/mborgerding/kissfft). I have included a portion of his code.
* WSJT-X authors, who developed a very interesting and novel communications protocol

The details of FT4 and FT8 procotols and decoding/encoding are described here: https://physics.princeton.edu/pulsar/k1jt/FT4_FT8_QEX.pdf

The public part of FT4/FT8 implementation is included in this repository under ft4_ft8_public.

Of course in moments of frustration I have looked up the original WSJT-X code, which is mostly written in Fortran (http://physics.princeton.edu/pulsar/K1JT/wsjtx.html). However, this library contains my own original DSP routines and a different implementation of the decoder which is suitable for resource-constrained embedded environments.

Karlis Goba,
YL3JG
