# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Record a USB microphone to a WAV file on a microSD card.

A bare-bones starting point for recording in your own project.
A USB microphone plugged into the board's USB host port is
recorded for RECORD_SECONDS, then saved as a new /sd/rec_NNNN.wav file.

It runs on the Metro ESP32-P4 and the Fruit Jam, and checks which one it is
running on to set up the USB host port and the microSD card.

audiofilewriter.AudioFileWriter does the work in the background. It fetches the
microphone's audio at the microphone's own rate and writes it to a file, so
the main loop is free for the rest of your program. Here it only watches for
dropouts.

The recording goes into RAM first and is copied to the SD card after it stops.
RAM limits the length of a recording: at 48 kHz mono, about 2 minutes on the
Metro ESP32-P4 and about 80 seconds on the Fruit Jam. Stereo halves that.
"""

import io
import os
import time

import adafruit_usb_host_descriptors
import board
import storage
import usb_host_audio
from audiofilewriter import AudioFileWriter

RECORD_SECONDS = 10
SAMPLE_RATE = 48000  # the nearest rate the microphone supports is used
SD_MOUNT = "/sd"


def sd_card_mounted():
    try:
        storage.getmount(SD_MOUNT)
    except OSError:
        return False
    return True


if board.board_id == "adafruit_fruit_jam":
    # The Fruit Jam powers and starts its USB host port by itself, and mounts
    # an inserted microSD card at /sd. Mount the card here only if it wasn't,
    # which happens when CIRCUITPY_SDCARD_USB = false is in settings.toml.
    if not sd_card_mounted():
        import busio
        import sdcardio

        spi = busio.SPI(board.SD_SCK, MOSI=board.SD_MOSI, MISO=board.SD_MISO)
        sd_card = sdcardio.SDCard(spi, board.SD_CS)
        storage.mount(storage.VfsFat(sd_card), SD_MOUNT)

elif board.board_id == "adafruit_metro_esp32p4":
    import digitalio
    import sdioio
    import usb_host

    # Mount the microSD card.
    sd_card = sdioio.SDCard(
        clock=board.SD_CLK,
        command=board.SD_CMD,
        data=(board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3),
        frequency=40_000_000,
    )
    storage.mount(storage.VfsFat(sd_card), SD_MOUNT)

    # The Metro's USB host port isn't started by the board: power it and start it.
    usb_power = digitalio.DigitalInOut(board.USB_HOST_POWER)
    usb_power.switch_to_output(value=True)
    usb_port = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)

else:
    raise RuntimeError(
        "This example runs on a Metro ESP32-P4 or a Fruit Jam, not " + board.board_id
    )

# Give a microphone that is already plugged in time to enumerate.
device = None
deadline = time.monotonic() + 3
while device is None and time.monotonic() < deadline:
    device = adafruit_usb_host_descriptors.find_microphone()
    time.sleep(0.1)
if device is None:
    raise RuntimeError("Plug a USB microphone into the USB host port")

# Pick the microphone's format and rate, and start its stream.
formats = adafruit_usb_host_descriptors.find_microphone_formats(device)
mic_format = adafruit_usb_host_descriptors.choose_microphone_format(
    formats, sample_rate=SAMPLE_RATE
)
sample_rate = mic_format.nearest_rate(SAMPLE_RATE)
device.set_configuration()
# SET_INTERFACE to the format's alternate setting starts the stream, then
# SET_CUR of the endpoint's sampling frequency picks the rate.
device.ctrl_transfer(0x01, 11, mic_format.alternate, mic_format.interface, None)
if mic_format.rate_control:
    device.ctrl_transfer(
        0x22, 0x01, 0x0100, mic_format.endpoint, sample_rate.to_bytes(3, "little")
    )

mic = usb_host_audio.USBIn(
    device,
    mic_format.endpoint,
    sample_rate=sample_rate,
    channel_count=mic_format.channel_count,
    bit_depth=8 * mic_format.bytes_per_sample,
    samples_signed=mic_format.samples_signed,
    max_packet_size=mic_format.max_packet_size,
)
print("Microphone:", mic.channel_count, "channel(s) at", mic.sample_rate, "Hz")

# Room in RAM for the whole recording, the 44 byte WAV header and a second to
# spare. (The recording is 16-bit, so 2 bytes per sample.) Giving BytesIO the
# size up front sets the memory aside now, so it never has to grow while recording.
bytes_per_second = mic.sample_rate * mic.channel_count * 2
recording = io.BytesIO((RECORD_SECONDS + 1) * bytes_per_second + 44)

# Some microphones send silence for a second or two after they are powered.
time.sleep(2)

print("Recording", RECORD_SECONDS, "seconds")
dropouts = 0
mic.overflow  # reading it clears it: forget anything from start-up
writer = AudioFileWriter(recording)
writer.play(mic)
start = time.monotonic()
while time.monotonic() - start < RECORD_SECONDS:
    # Your project's code goes here. Keep each pass short.
    if mic.overflow:  # audio from the microphone was lost
        dropouts += 1
    time.sleep(0.01)
# stop() writes what is left and fills in the WAV header's lengths.
writer.stop()
print("Recorded with", dropouts, "dropouts")

# Use the next free file name: rec_0001.wav, rec_0002.wav, ...
existing = os.listdir(SD_MOUNT)
number = 1
while "rec_%04d.wav" % number in existing:
    number += 1
path = "%s/rec_%04d.wav" % (SD_MOUNT, number)

# Copy the recording to the card, 64 KB at a time.
print("Saving", path)
chunk = bytearray(64 * 1024)
recording.seek(0)
with open(path, "wb") as file:
    while True:
        count = recording.readinto(chunk)
        if not count:
            break
        file.write(memoryview(chunk)[:count])
recording.close()
print("Saved", path)

# The computer doesn't see the new file on the SD card's USB drive until the
# board resets.
