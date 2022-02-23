# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

try:
    import struct
except ImportError:
    import ustruct as struct

# Connect the sensor TX pin to the board/computer RX pin
# For use with a microcontroller board:
import board
import busio
uart = busio.UART(board.TX, board.RX, baudrate=9600)

# For use with Raspberry Pi/Linux:
# import serial
# uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

# For use with USB-to-serial cable:
# import serial
# uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=0.25)

buffer = []

while True:
    data = uart.read(32)  # read up to 32 bytes
    data = list(data)
    # print("read: ", data)          # this is a bytearray type

    buffer += data

    while buffer and buffer[0] != 0x42:
        buffer.pop(0)

    if len(buffer) > 200:
        buffer = []  # avoid an overrun if all bad data
    if len(buffer) < 32:
        continue

    if buffer[1] != 0x4d:
        buffer.pop(0)
        continue

    frame_len = struct.unpack(">H", bytes(buffer[2:4]))[0]
    if frame_len != 28:
        buffer = []
        continue

    frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(buffer[4:]))

    pm10_standard, pm25_standard, pm100_standard, pm10_env, \
        pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, \
        particles_25um, particles_50um, particles_100um, skip, checksum = frame

    check = sum(buffer[0:30])

    if check != checksum:
        buffer = []
        continue

    print("Concentration Units (standard)")
    print("---------------------------------------")
    print("PM 1.0: %d\tPM2.5: %d\tPM10: %d" %
          (pm10_standard, pm25_standard, pm100_standard))
    print("Concentration Units (environmental)")
    print("---------------------------------------")
    print("PM 1.0: %d\tPM2.5: %d\tPM10: %d" % (pm10_env, pm25_env, pm100_env))
    print("---------------------------------------")
    print("Particles > 0.3um / 0.1L air:", particles_03um)
    print("Particles > 0.5um / 0.1L air:", particles_05um)
    print("Particles > 1.0um / 0.1L air:", particles_10um)
    print("Particles > 2.5um / 0.1L air:", particles_25um)
    print("Particles > 5.0um / 0.1L air:", particles_50um)
    print("Particles > 10 um / 0.1L air:", particles_100um)
    print("---------------------------------------")

    buffer = buffer[32:]
    # print("Buffer ", buffer)
