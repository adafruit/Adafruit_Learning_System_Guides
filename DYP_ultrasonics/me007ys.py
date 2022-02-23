# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import serial

SERIAL_PORT = "/dev/ttyS15"   # or "COM4" or whatever

serialport = serial.Serial(SERIAL_PORT, 9600)


def read_me007ys(ser, timeout = 1.0):
    ts = time.monotonic()
    buf = bytearray(3)
    idx = 0

    while True:
        # Option 1, we time out while waiting to get valid data
        if time.monotonic() - ts > timeout:
            raise RuntimeError("Timed out waiting for data")

        c = ser.read(1)[0]
        #print(c)
        if idx == 0 and c == 0xFF:
            buf[0] = c
            idx = idx + 1
        elif 0 < idx < 3:
            buf[idx] = c
            idx = idx + 1
        else:
            chksum = sum(buf) & 0xFF
            if chksum == c:
                return (buf[1] << 8) + buf[2]
            idx = 0
    return None

while True:
    dist = read_me007ys(serialport)
    print("Distance = %d mm" % dist)
