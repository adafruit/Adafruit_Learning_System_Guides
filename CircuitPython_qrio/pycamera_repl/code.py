# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3 with the
ILI9341 display.
"""

import time
import qrio
from adafruit_pycamera import PyCamera

pycam = PyCamera()
pycam._mode_label.text = "QR SCAN"  # pylint: disable=protected-access
pycam._res_label.text = ""  # pylint: disable=protected-access
pycam.display.refresh()
qrdecoder = qrio.QRDecoder(pycam.camera.width, pycam.camera.height)

old_payload = None
while True:
    new_frame = pycam.continuous_capture()
    pycam.blit(new_frame)
    for row in qrdecoder.decode(new_frame, qrio.PixelPolicy.RGB565_SWAPPED):
        payload = row.payload
        try:
            payload = payload.decode("utf-8")
        except UnicodeError:
            payload = str(payload)
        if payload != old_payload:
            pycam.tone(200, 0.1)
            print(payload)
            pycam.display_message(payload, color=0xFFFFFF)
            time.sleep(1)
            old_payload = payload
